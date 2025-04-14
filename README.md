# M-Pesa Integration💸

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

You'll also need additional dependencies for a typical web server setup:

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

Create a `.env` file in your project root to store your M-Pesa credentials.

**For Till Payments:**

```plaintext:.env
MPESA_CONSUMER_KEY=your_consumer_key
MPESA_CONSUMER_SECRET=your_consumer_secret
MPESA_PASSKEY=your_passkey
MPESA_SHORTCODE=your_till_number # Use Till Number here
MPESA_CALLBACK_URL=https://your-domain.com/api/mpesa/callback
MPESA_ENVIRONMENT=sandbox  # or "production"
# MPESA_BUSINESS_SHORTCODE is not needed for Till
```

**For Paybill Payments:**

```plaintext:.env
MPESA_CONSUMER_KEY=your_consumer_key
MPESA_CONSUMER_SECRET=your_consumer_secret
MPESA_PASSKEY=your_passkey
MPESA_SHORTCODE=your_paybill_number # Use Paybill Number here
MPESA_BUSINESS_SHORTCODE=your_paybill_number # Use the same Paybill Number here
MPESA_CALLBACK_URL=https://your-domain.com/api/mpesa/callback
MPESA_ENVIRONMENT=sandbox  # or "production"
```

**Note:**
*   For Paybill, both `MPESA_SHORTCODE` and `MPESA_BUSINESS_SHORTCODE` should typically be set to your Paybill number. The `MpesaConfig` uses `shortcode` as the primary identifier passed in the API request's `PartyB` field and `business_shortcode` for the `BusinessShortCode` field.
*   For production, set `MPESA_ENVIRONMENT=production` and ensure your callback URL is secure (HTTPS) and publicly accessible.

## How It Works 🤔

The `mpesa-integration` package provides two main components:

1.  **`MpesaConfig`**:
    *   A configuration class to hold your M-Pesa credentials and settings.
    *   Supports customization for Till or Paybill payments.
    *   Validates required fields to prevent misconfiguration. ✅
2.  **`MpesaClient`**:
    *   A client class to interact with the M-Pesa API.
    *   Handles authentication (access token retrieval). 🔑
    *   Initiates STK Push payments with a single method call (`initiate_payment`).
    *   Formats phone numbers automatically.

The package uses the Safaricom Daraja API under the hood, automating tasks like:

*   Generating OAuth access tokens.
*   Constructing and sending STK Push requests.
*   Parsing API responses.

## Usage Examples 🚀

This package can be easily integrated into web frameworks like FastAPI or Flask.

**For detailed examples using FastAPI for both Till and Paybill payments, including request handling, client initialization, payment initiation, and callback processing, please see:**

➡️ **[Usage Examples (usecases.md)](./usecases.md)**

## Debugging Tips 🐞

*   **Enable logging:** Use Python's `logging` module to see detailed information from the client.
*   **Check environment variables:** Ensure all required variables are correctly set in your `.env` file and loaded (using `python-dotenv`).
*   **Test in sandbox:** Use Safaricom's sandbox environment (`MPESA_ENVIRONMENT=sandbox`) to avoid real transactions during development.
*   **Use ngrok for callbacks:** Essential for testing callbacks locally. Ensure the ngrok URL is registered on the Daraja portal and matches your `MPESA_CALLBACK_URL`.
*   **Inspect API responses:** Log the full response from `initiate_payment` and the data received at the callback endpoint.
*   **Verify Credentials:** Double-check Consumer Key, Secret, Passkey, and Shortcode(s).

## Security Considerations 🛡️

*   **Secure your `.env` file:** Never commit it to version control. Add `.env` to your `.gitignore`.
*   **Validate callbacks:** Verify the `CheckoutRequestID` and potentially other details against your records to ensure callbacks are legitimate. Consider IP whitelisting if possible.
*   **Use HTTPS:** In production, **always** ensure your callback URL uses HTTPS.
*   **Limit retries:** Implement sensible retry logic for failed API calls, but cap the number of attempts.
*   **Sanitize Inputs:** Validate and sanitize phone numbers and amounts before sending them to the API.

## Contributing 🤝

Found a bug or have a feature request? Open an issue or submit a pull request on the GitHub repository.

## License 📜

This package is licensed under the MIT License. See the `LICENSE` file for details.

## Support ❓

For questions or assistance, please open an issue on the GitHub repository.