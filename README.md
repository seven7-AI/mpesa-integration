# M-Pesa Integration 🐍💸

A lightweight and robust Python package for integrating M-Pesa STK Push payments, supporting both Till and Paybill payment methods. This package simplifies the process of initiating payments, handling callbacks, and managing M-Pesa API interactions with minimal setup.

Whether you're building a payment system for a parking lot 🅿️, e-commerce platform 🛒, or any other service, `mpesa-integration` abstracts the complexity of M-Pesa's Daraja API, letting you focus on your application logic.

## ✨ Features

*   Supports both Till and Paybill STK Push payments.
*   Easy-to-use client for initiating payments.
*   Configurable for sandbox and production environments. ⚙️
*   Robust error handling and logging support. 📝
*   Environment variable integration for secure credential management. 🔒
*   Compatible with modern Python web frameworks like FastAPI and Flask. 🚀

## Installation

Install the package using pip:

```bash
pip install mpesa-integration
```

You'll also need additional dependencies for a typical setup (like the FastAPI example below):

```bash
pip install fastapi uvicorn python-dotenv
```

## Prerequisites

Before using the package, ensure you have:

*   **M-Pesa Daraja API Credentials:**
    *   Consumer Key and Consumer Secret from the [Safaricom Developer Portal](https://developer.safaricom.co.ke/).
    *   Passkey for STK Push.
    *   Shortcode (Till Number or Paybill Number).
    *   Callback URL (a publicly accessible URL for M-Pesa to send payment confirmations). 🌐
*   A `.env` file to store sensitive credentials (see configuration below).
*   A web server (e.g., FastAPI with Uvicorn) to handle HTTP requests and callbacks.

## Configuration 🛠️

Create a `.env` file in your project root to store your M-Pesa credentials. For Till payments, use the following format:

```plaintext:.env
MPESA_CONSUMER_KEY=your_consumer_key
MPESA_CONSUMER_SECRET=your_consumer_secret
MPESA_PASSKEY=your_passkey
MPESA_SHORTCODE=your_till_number
MPESA_CALLBACK_URL=https://your-domain.com/api/mpesa/callback
MPESA_ENVIRONMENT=sandbox  # or "production"
```

**Note:** For production, set `MPESA_ENVIRONMENT=production` and ensure your callback URL is secure (HTTPS) and publicly accessible.

## How It Works 🤔

The `mpesa-integration` package provides two main components:

1.  **`MpesaConfig`**:
    *   A configuration class to hold your M-Pesa credentials and settings.
    *   Supports customization for Till or Paybill payments.
    *   Validates required fields to prevent misconfiguration. ✅
2.  **`MpesaClient`**:
    *   A client class to interact with the M-Pesa API.
    *   Handles authentication (access token retrieval). 🔑
    *   Initiates STK Push payments with a single method call.
    *   Supports callback handling for payment confirmation.

The package uses the Safaricom Daraja API under the hood, automating tasks like:

*   Generating OAuth access tokens.
*   Formatting phone numbers for Kenyan M-Pesa transactions.
*   Constructing and sending STK Push requests.
*   Parsing API responses for easy integration.

## Usage with FastAPI (Till Payment Example) 🚀

Below is a complete example of using `mpesa-integration` with FastAPI to initiate Till payments.

### Example Code

Create a file named `main.py`:

```python:main.py
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
import os
import logging
from dotenv import load_dotenv
# Assuming mpesa-integration package is installed
from mpesa_integration import MpesaClient, MpesaConfig

app = FastAPI(title="M-Pesa Till Payment API")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Verify environment variables
required_env_vars = [
    "MPESA_CONSUMER_KEY",
    "MPESA_CONSUMER_SECRET", # Note: Use MPESA_CONSUMER_SECRET in .env
    "MPESA_PASSKEY",
    "MPESA_SHORTCODE",
    "MPESA_CALLBACK_URL"
]
for var in required_env_vars:
    # Adjust check for the actual env var name if different (e.g., MPESA_SECRET_KEY vs MPESA_CONSUMER_SECRET)
    env_var_name = "MPESA_CONSUMER_SECRET" if var == "MPESA_CONSUMER_SECRET" else var
    if not os.getenv(env_var_name):
        logger.error(f"Missing environment variable: {env_var_name}")
        raise EnvironmentError(f"Missing environment variable: {env_var_name}")

# M-Pesa configuration for Till payment
try:
    config = MpesaConfig(
        consumer_key=os.getenv("MPESA_CONSUMER_KEY"),
        consumer_secret=os.getenv("MPESA_CONSUMER_SECRET"), # Ensure this matches your .env
        shortcode=os.getenv("MPESA_SHORTCODE"),
        passkey=os.getenv("MPESA_PASSKEY"),
        callback_url=os.getenv("MPESA_CALLBACK_URL"),
        environment=os.getenv("MPESA_ENVIRONMENT", "sandbox") # Default to sandbox if not set
    )
    logger.info(f"MpesaConfig initialized for environment: {config.environment}")
except Exception as e:
    logger.error(f"Failed to initialize MpesaConfig: {e}")
    raise

# Initialize M-Pesa client
try:
    client = MpesaClient(config)
    logger.info("MpesaClient initialized successfully.")
except Exception as e:
    logger.error(f"Failed to initialize MpesaClient: {e}")
    raise

# Pydantic model for request validation
class PaymentRequest(BaseModel):
    phone_number: str
    amount: int
    account_reference: str = "TillPayment" # Default or allow override
    transaction_desc: str = "Payment via Till Number" # Default or allow override

@app.post("/initiate_payment")
async def initiate_payment_endpoint(payment: PaymentRequest):
    logger.info(f"Received payment request: phone={payment.phone_number}, amount={payment.amount}")
    try:
        # Initiate payment using the client
        response = client.initiate_payment(
            phone_number=payment.phone_number, # Client handles normalization
            amount=payment.amount,
            account_reference=payment.account_reference,
            transaction_desc=payment.transaction_desc
        )

        logger.info(f"M-Pesa API Response: {response}")

        # Check for specific Daraja error codes if needed
        if response.get("ResponseCode") != "0":
             logger.error(f"M-Pesa API Error: {response.get('ResponseDescription')}")
             raise HTTPException(status_code=400, detail=response.get('CustomerMessage', 'M-Pesa request failed'))

        return response

    except Exception as e:
        logger.exception(f"Payment initiation failed unexpectedly: {str(e)}") # Log full traceback
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/mpesa/callback")
async def mpesa_callback(request: Request):
    try:
        callback_data = await request.json()
        logger.info(f"Received M-Pesa callback: {callback_data}")

        # Basic validation: Check if it's the structure you expect
        if not isinstance(callback_data, dict) or "Body" not in callback_data:
            logger.error("Invalid callback format received.")
            raise HTTPException(status_code=400, detail="Invalid callback format")

        stk_callback = callback_data.get("Body", {}).get("stkCallback", {})

        if not stk_callback:
             logger.error("Callback data missing 'stkCallback' field.")
             raise HTTPException(status_code=400, detail="Callback data missing 'stkCallback' field")

        # Process callback data (e.g., update database, notify user)
        merchant_request_id = stk_callback.get("MerchantRequestID")
        checkout_request_id = stk_callback.get("CheckoutRequestID")
        result_code = stk_callback.get("ResultCode")
        result_desc = stk_callback.get("ResultDesc")

        logger.info(f"Callback details: MerchantReqID={merchant_request_id}, CheckoutReqID={checkout_request_id}, ResultCode={result_code}, Desc={result_desc}")

        if result_code == 0:
            # Payment successful! 🎉
            logger.info(f"Payment successful for CheckoutRequestID: {checkout_request_id}")
            # Add your success logic here (e.g., update order status in DB)
            # Example: db.update_payment_status(checkout_request_id, "SUCCESS")
        else:
            # Payment failed or cancelled 😞
            logger.error(f"Payment failed/cancelled for CheckoutRequestID: {checkout_request_id}. Reason: {result_desc} (Code: {result_code})")
            # Add your failure logic here
            # Example: db.update_payment_status(checkout_request_id, "FAILED", result_desc)

        # Respond to M-Pesa acknowledging receipt (important!)
        return {"ResultCode": 0, "ResultDesc": "Accepted"} # Or {"C2BPaymentConfirmationResult": "Success"} depending on API

    except Exception as e:
        logger.exception(f"Callback processing failed: {str(e)}") # Log full traceback
        # Don't send error details back to M-Pesa, just acknowledge failure to process
        # Responding with error might cause M-Pesa to retry the callback.
        # Log the error internally and return a generic success ack if possible,
        # or a specific error code if absolutely necessary and documented by Safaricom.
        # For now, let's return a 500 to indicate internal failure, but M-Pesa might retry.
        # A better approach might be to always return success to M-Pesa and handle errors internally.
        # Let's stick to acknowledging receipt for now.
        # return {"ResultCode": 1, "ResultDesc": "Failed"} # Example failure ack
        raise HTTPException(status_code=500, detail="Internal server error processing callback")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000)) # Allow port configuration via env
    logger.info(f"Starting server on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)

```

### Steps to Run 🏃‍♀️

1.  **Set up your environment:**
    *   Create a `.env` file with the credentials as shown in the Configuration section.
    *   Ensure your Till Number is correctly set in `MPESA_SHORTCODE`.
2.  **Install dependencies:**
    ```bash
    pip install mpesa-integration fastapi uvicorn python-dotenv
    ```
3.  **Run the FastAPI server:**
    ```bash
    uvicorn main:app --host 0.0.0.0 --port 8000
    ```
4.  **Test the payment endpoint:**
    *   Send a POST request to `http://localhost:8000/initiate_payment` with a JSON body:
        ```json
        {
            "phone_number": "2547xxxxxxxx", // Use a valid test phone number
            "amount": 1
        }
        ```
    *   Use a tool like `curl`, Postman, or the FastAPI Swagger UI (`http://localhost:8000/docs`).
5.  **Handle callbacks:**
    *   Ensure your `MPESA_CALLBACK_URL` is publicly accessible. For local testing, use [ngrok](https://ngrok.com/): `ngrok http 8000`. Update your `.env` file and the Safaricom Developer Portal with the ngrok URL (e.g., `https://<your-ngrok-id>.ngrok.io/mpesa/callback`).
    *   The `/mpesa/callback` endpoint will receive payment confirmations from M-Pesa.

### Example Response ✅

On successful payment initiation:

```json
{
    "CheckoutRequestID": "ws_CO_14102024123456789",
    "ResponseCode": "0",
    "ResponseDescription": "Success. Request accepted for processing",
    "MerchantRequestID": "1234-5678-9012",
    "CustomerMessage": "Success. Request accepted for processing"
}
```

### Callback Handling 📞

The `/mpesa/callback` endpoint receives payment status updates from M-Pesa. The callback data includes:

*   `ResultCode`: `0` for success, non-zero for failure.
*   `ResultDesc`: Description of the result.
*   `CheckoutRequestID`: Unique ID to match the payment initiation request.
*   `MerchantRequestID`: Your internal request ID.
*   (Optional) `CallbackMetadata`: Contains details like Amount, MpesaReceiptNumber, PhoneNumber, etc., on success.

You should extend the callback handler to:

*   Update your database with payment status. 💾
*   Notify users of payment success or failure. 📧
*   Log transactions for auditing. 📊

Example successful callback payload:

```json
{
    "Body": {
        "stkCallback": {
            "MerchantRequestID": "1234-5678-9012",
            "CheckoutRequestID": "ws_CO_14102024123456789",
            "ResultCode": 0,
            "ResultDesc": "The service request is processed successfully.",
            "CallbackMetadata": {
                "Item": [
                    {"Name": "Amount", "Value": 1.00},
                    {"Name": "MpesaReceiptNumber", "Value": "SJKABCDEF1"},
                    {"Name": "TransactionDate", "Value": 20241014123500},
                    {"Name": "PhoneNumber", "Value": 2547xxxxxxxx}
                ]
            }
        }
    }
}
```

## Debugging Tips 🐞

*   **Enable logging:** The example includes detailed logging. Check your console/log files.
*   **Check environment variables:** Ensure all required variables are correctly set in your `.env` file and loaded.
*   **Test in sandbox:** Use Safaricom's sandbox environment (`MPESA_ENVIRONMENT=sandbox`) to avoid real transactions during development.
*   **Use ngrok for callbacks:** Essential for testing callbacks locally. Ensure the ngrok URL is registered on the Daraja portal.
*   **Inspect API responses:** Log the full response from `initiate_payment` and the data received at the callback endpoint.
*   **Verify Credentials:** Double-check Consumer Key, Secret, Passkey, and Shortcode.

## Security Considerations 🛡️

*   **Secure your `.env` file:** Never commit it to version control. Add `.env` to your `.gitignore`.
*   **Validate callbacks:** Verify the `CheckoutRequestID` and potentially other details against your records to ensure callbacks are legitimate. Consider IP whitelisting if possible.
*   **Use HTTPS:** In production, **always** ensure your callback URL uses HTTPS.
*   **Limit retries:** Implement sensible retry logic for failed API calls, but cap the number of attempts.
*   **Sanitize Inputs:** Validate and sanitize phone numbers and amounts before sending them to the API.

## Contributing 🤝

Found a bug or have a feature request? Open an issue or submit a pull request on our GitHub repository.

## License 📜

This package is licensed under the MIT License. See the `LICENSE` file for details.

## Support ❓

For questions or assistance, please open an issue on the GitHub repository.