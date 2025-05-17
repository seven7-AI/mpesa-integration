import os
import sys
import logging
import time
import json
from dotenv import load_dotenv
# This assumes 'mpesa_integration' package is installed and contains 'mpesa.py'
# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Force reload of the mpesa module to ensure latest changes are used
if 'mpesa_integration.mpesa' in sys.modules:
    importlib.reload(sys.modules['mpesa_integration.mpesa'])
from mpesa_integration.mpesa import MpesaClient, MpesaConfig

# Configure logging first
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# Print environment variables for debugging (without revealing sensitive data)
logger.info("Environment variables loaded")
logger.debug(f"MPESA_CONSUMER_KEY exists: {'Yes' if os.getenv('MPESA_CONSUMER_KEY') else 'No'}")
logger.debug(f"MPESA_SECRET_KEY exists: {'Yes' if os.getenv('MPESA_SECRET_KEY') else 'No'}")
logger.debug(f"MPESA_PASSKEY exists: {'Yes' if os.getenv('MPESA_PASSKEY') else 'No'}")

# Get the ngrok URL for testing - you can replace this with your actual ngrok URL
callback_url = os.getenv("MPESA_CALLBACK_URL", "https://your-ngrok-url.ngrok-free.app/api/mpesa/callback")
logger.info(f"Using callback URL: {callback_url}")

# For Till Payment
config_till = MpesaConfig(
    consumer_key=os.getenv("MPESA_CONSUMER_KEY"),
    consumer_secret=os.getenv("MPESA_SECRET_KEY"),
    shortcode="174379",
    passkey=os.getenv("MPESA_PASSKEY"),
    callback_url=callback_url,
    environment="sandbox"  # or "production"
)

# For Paybill Payment
# config_paybill = MpesaConfig(
#     consumer_key=os.getenv("MPESA_CONSUMER_KEY"),
#     consumer_secret=os.getenv("MPESA_SECRET_KEY"),
#     shortcode="174379",  # Account number
#     passkey=os.getenv("MPESA_PASSKEY"),
#     callback_url="https://your-domain.com/callback",
#     business_shortcode="174379",  # Business number
#     environment="sandbox"
# )

# Choose which config to use for the client
# For example, using Paybill config:
# client = MpesaClient(config_paybill)
# Or using Till config:
client = MpesaClient(config_till)

# Test function to run all tests
def run_tests():
    try:
        # Test 1: Get access token
        logger.info("TEST 1: Attempting to get access token...")
        access_token = client.get_access_token()
        logger.info("✅ Successfully obtained access token")
        
        # Test 2: Initiate payment
        logger.info("TEST 2: Initiating payment...")
        payment_response = client.initiate_payment(
            phone_number="254719321423",
            amount=1,
            account_reference="test",
            transaction_desc="test"
        )
        logger.info(f"Payment response: {payment_response}")
        print(f"Payment initiated: {json.dumps(payment_response, indent=2)}")
        
        # Validate response format based on documentation
        expected_keys = ["MerchantRequestID", "CheckoutRequestID", "ResponseCode", "ResponseDescription", "CustomerMessage"]
        missing_keys = [key for key in expected_keys if key not in payment_response]
        if missing_keys:
            logger.warning(f"⚠️ Payment response missing expected keys: {missing_keys}")
        else:
            logger.info("✅ Payment response has all expected keys")
        
        # Test 3: Transaction status check
        checkout_request_id = payment_response.get("CheckoutRequestID")
        if checkout_request_id:
            logger.info(f"TEST 3: Checking transaction status using CheckoutRequestID: {checkout_request_id}")
            logger.info("Waiting 5 seconds before checking status...")
            time.sleep(5)  # Wait for transaction to be processed
            
            try:
                status_response = client.check_transaction_status(
                    transaction_id=checkout_request_id
                )
                logger.info(f"Transaction status response: {status_response}")
                print(f"Transaction status: {json.dumps(status_response, indent=2)}")
            except Exception as e:
                logger.error(f"❌ Error checking transaction status: {str(e)}")
        else:
            logger.warning("⚠️ No CheckoutRequestID found in payment response, skipping status check")
        
        # Test 4: Callback parsing (with mock data)
        logger.info("TEST 4: Testing callback parsing with sample successful and failed callback data")
        
        # Successful callback example
        successful_callback = {
            "Body": {
                "stkCallback": {
                    "MerchantRequestID": "29115-34620561-1",
                    "CheckoutRequestID": "ws_CO_191220191020363925",
                    "ResultCode": 0,
                    "ResultDesc": "The service request is processed successfully.",
                    "CallbackMetadata": {
                        "Item": [
                            {"Name": "Amount", "Value": 1.00},
                            {"Name": "MpesaReceiptNumber", "Value": "NLJ7RT61SV"},
                            {"Name": "TransactionDate", "Value": 20191219102115},
                            {"Name": "PhoneNumber", "Value": 254708374149}
                        ]
                    }
                }
            }
        }
        
        # Failed callback example
        failed_callback = {
            "Body": {
                "stkCallback": {
                    "MerchantRequestID": "29115-34620561-1",
                    "CheckoutRequestID": "ws_CO_191220191020363925",
                    "ResultCode": 1032,
                    "ResultDesc": "Request canceled by user."
                }
            }
        }
        
        # Test with successful callback
        try:
            parsed_success = client.parse_callback_data(successful_callback)
            logger.info(f"Parsed successful callback: {parsed_success}")
            print(f"Parsed successful callback: {json.dumps(parsed_success, indent=2)}")
            logger.info("✅ Successfully parsed successful callback")
        except Exception as e:
            logger.error(f"❌ Error parsing successful callback: {str(e)}")
        
        # Test with failed callback
        try:
            parsed_failure = client.parse_callback_data(failed_callback)
            logger.info(f"Parsed failed callback: {parsed_failure}")
            print(f"Parsed failed callback: {json.dumps(parsed_failure, indent=2)}")
            logger.info("✅ Successfully parsed failed callback")
        except Exception as e:
            logger.error(f"❌ Error parsing failed callback: {str(e)}")
        
    except Exception as e:
        logger.error(f"❌ Test error: {str(e)}")
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    run_tests()