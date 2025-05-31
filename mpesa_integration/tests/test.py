import os
import sys
import logging
import json
import time
from dotenv import load_dotenv
import importlib
from supabase import create_client

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Force reload of the mpesa module to ensure latest changes are used
if 'mpesa_integration.mpesa' in sys.modules:
    importlib.reload(sys.modules['mpesa_integration.mpesa'])
from mpesa_integration.mpesa import MpesaClient, MpesaConfig

# Configure logging
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
logger.debug(f"MPESA_CONSUMER_SECRET exists: {'Yes' if os.getenv('MPESA_CONSUMER_SECRET') else 'No'}")
logger.debug(f"MPESA_PASSKEY exists: {'Yes' if os.getenv('MPESA_PASSKEY') else 'No'}")
logger.debug(f"MPESA_INITIATOR_NAME exists: {'Yes' if os.getenv('MPESA_INITIATOR_NAME') else 'No'}")
logger.debug(f"MPESA_INITIATOR_PASSWORD exists: {'Yes' if os.getenv('MPESA_INITIATOR_PASSWORD') else 'No'}")
logger.debug(f"MPESA_CERTIFICATE_PATH exists: {'Yes' if os.getenv('MPESA_CERTIFICATE_PATH') else 'No'}")
logger.debug(f"SHORT_CODE exists: {'Yes' if os.getenv('SHORT_CODE') else 'No'}")
logger.debug(f"MPESA_ACCOUNT_NUMBER exists: {'Yes' if os.getenv('MPESA_ACCOUNT_NUMBER') else 'No'}")
logger.debug(f"PHONE_NUMBER exists: {'Yes' if os.getenv('PHONE_NUMBER') else 'No'}")
logger.debug(f"MPESA_ENVIRONMENT exists: {'Yes' if os.getenv('MPESA_ENVIRONMENT') else 'No'}")
logger.debug(f"MPESA_CALLBACK_URL exists: {'Yes' if os.getenv('MPESA_CALLBACK_URL') else 'No'}")
logger.debug(f"MPESA_RESULT_URL exists: {'Yes' if os.getenv('MPESA_RESULT_URL') else 'No'}")
logger.debug(f"MPESA_QUEUE_TIMEOUT_URL exists: {'Yes' if os.getenv('MPESA_QUEUE_TIMEOUT_URL') else 'No'}")
logger.debug(f"SUPABASE_URL exists: {'Yes' if os.getenv('SUPABASE_URL') else 'No'}")
logger.debug(f"SUPABASE_KEY exists: {'Yes' if os.getenv('SUPABASE_KEY') else 'No'}")

# Get the callback URL for testing
callback_url = os.getenv("MPESA_CALLBACK_URL", "https://your-ngrok-url.ngrok-free.app/api/mpesa/callback")
logger.info(f"Using callback URL: {callback_url}")

# Configure MpesaConfig for Till Payment
config_till = MpesaConfig(
    consumer_key=os.getenv("MPESA_CONSUMER_KEY"),
    consumer_secret=os.getenv("MPESA_CONSUMER_SECRET"),
    shortcode=os.getenv("SHORT_CODE"),
    passkey=os.getenv("MPESA_PASSKEY"),
    callback_url=callback_url,
    initiator_name=os.getenv("MPESA_INITIATOR_NAME"),
    initiator_password=os.getenv("MPESA_INITIATOR_PASSWORD"),
    certificate_path=os.getenv("MPESA_CERTIFICATE_PATH"),
    result_url=os.getenv("MPESA_RESULT_URL", callback_url),
    queue_timeout_url=os.getenv("MPESA_QUEUE_TIMEOUT_URL", callback_url),
    environment=os.getenv("MPESA_ENVIRONMENT", "sandbox"),
    request_timeout=float(os.getenv("MPESA_REQUEST_TIMEOUT", 30.0)),
    max_retries=int(os.getenv("MPESA_MAX_RETRIES", 3)),
    retry_delay=float(os.getenv("MPESA_RETRY_DELAY", 5.0))
)

# Configure MpesaConfig for Paybill Payment
config_paybill = MpesaConfig(
    consumer_key=os.getenv("MPESA_CONSUMER_KEY"),
    consumer_secret=os.getenv("MPESA_CONSUMER_SECRET"),
    shortcode=os.getenv("SHORT_CODE"),
    passkey=os.getenv("MPESA_PASSKEY"),
    callback_url=callback_url,
    business_shortcode=os.getenv("MPESA_ACCOUNT_NUMBER"),
    initiator_name=os.getenv("MPESA_INITIATOR_NAME"),
    initiator_password=os.getenv("MPESA_INITIATOR_PASSWORD"),
    certificate_path=os.getenv("MPESA_CERTIFICATE_PATH"),
    result_url=os.getenv("MPESA_RESULT_URL", callback_url),
    queue_timeout_url=os.getenv("MPESA_QUEUE_TIMEOUT_URL", callback_url),
    environment=os.getenv("MPESA_ENVIRONMENT", "sandbox"),
    request_timeout=float(os.getenv("MPESA_REQUEST_TIMEOUT", 30.0)),
    max_retries=int(os.getenv("MPESA_MAX_RETRIES", 3)),
    retry_delay=float(os.getenv("MPESA_RETRY_DELAY", 5.0))
)

# Initialize MpesaClient with Till config (change to 'config_paybill' to test Paybill payments)
client = MpesaClient(config_till)

def wait_for_callback(checkout_request_id, timeout=60, poll_interval=5):
    """Poll Supabase for a callback with the given CheckoutRequestID."""
    logger.info(f"Waiting for callback for CheckoutRequestID: {checkout_request_id}")
    start_time = time.time()
    
    try:
        supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
        while time.time() - start_time < timeout:
            response = supabase.table("transactions").select("*").eq("checkout_request_id", checkout_request_id).execute()
            callbacks = response.data
            if callbacks:
                callback = callbacks[0]  # Take the first callback
                logger.info(f"Callback received: {callback}")
                result_code = callback.get('result_code')
                if result_code == 0:
                    logger.info(f"✅ Transaction successful: {callback}")
                else:
                    logger.warning(f"⚠️ Transaction failed with result_code {result_code}: {callback}")
                return callback
            logger.debug(f"No callback found yet for {checkout_request_id}, retrying in {poll_interval} seconds...")
            time.sleep(poll_interval)
        
        logger.warning(f"No callback received for {checkout_request_id} after {timeout} seconds")
        return None
    
    except Exception as e:
        logger.error(f"Error polling Supabase for callback: {str(e)}")
        return None

# Test function to run all tests
def run_tests():
    try:
        # Test 1: Get access token
        logger.info("TEST 1: Attempting to get access token...")
        access_token = client.get_access_token()
        logger.info(f"✅ Successfully obtained access token: {access_token}")
        
        # Test 2: Initiate Till payment and wait for callback
        logger.info("TEST 2: Initiating Till payment...")
        payment_response = client.initiate_payment(
            phone_number=os.getenv("PHONE_NUMBER"),
            amount=1,
            account_reference="test_till",
            transaction_desc="Test Till",
            transaction_type="CustomerBuyGoodsOnline"
        )
        logger.info(f"Payment response: {payment_response}")
        print(f"Till payment initiated: {json.dumps(payment_response, indent=2)}")
        
        # Validate response format
        expected_keys = ["MerchantRequestID", "CheckoutRequestID", "ResponseCode", "ResponseDescription", "CustomerMessage"]
        missing_keys = [key for key in expected_keys if key not in payment_response]
        if missing_keys:
            logger.warning(f"⚠️ Payment response missing expected keys: {missing_keys}")
        else:
            logger.info("✅ Payment response has all expected keys")

        # Wait for Till payment callback
        checkout_request_id = payment_response.get("CheckoutRequestID")
        if checkout_request_id:
            callback = wait_for_callback(checkout_request_id)
            if not callback:
                logger.warning("⚠️ No callback received for Till payment, proceeding to next test")
        else:
            logger.warning("⚠️ No CheckoutRequestID found in Till payment response, skipping callback wait")

        # Delay to avoid subscriber lock
        logger.info("Pausing for 10 seconds to avoid subscriber lock...")
        time.sleep(10)

        # # Test 3: Initiate Paybill payment and wait for callback
        # logger.info("TEST 3: Initiating Paybill payment...")
        # client.config = config_paybill  # Switch to Paybill config
        # payment_response_paybill = client.initiate_payment(
        #     phone_number=os.getenv("PHONE_NUMBER"),
        #     amount=1,
        #     account_reference="test_paybill",
        #     transaction_desc="Test Paybill payment",
        #     transaction_type="CustomerPayBillOnline",
        #     shortcode=os.getenv("MPESA_ACCOUNT_NUMBER")
        # )
        # logger.info(f"Paybill payment response: {payment_response_paybill}")
        # print(f"Paybill payment initiated: {json.dumps(payment_response_paybill, indent=2)}")

        # # Wait for Paybill payment callback
        # checkout_request_id_paybill = payment_response_paybill.get("CheckoutRequestID")
        # if checkout_request_id_paybill:
        #     callback = wait_for_callback(checkout_request_id_paybill)
        #     if not callback:
        #         logger.warning("⚠️ No callback received for Paybill payment")
        # else:
        #     logger.warning("⚠️ No CheckoutRequestID found in Paybill payment response, skipping callback wait")

        # # Test 4: Transaction status check (for Till payment)
        # if checkout_request_id:
        #     logger.info(f"TEST 4: Checking transaction status using CheckoutRequestID: {checkout_request_id}")
        #     try:
        #         client.config = config_till  # Switch back to Till config
        #         status_response = client.check_transaction_status(
        #             transaction_id=checkout_request_id,
        #             remarks="Test status query",
        #             occasion="Test",
        #             result_url=os.getenv("MPESA_RESULT_URL", callback_url),
        #             queue_timeout_url=os.getenv("MPESA_QUEUE_TIMEOUT_URL", callback_url)
        #         )
        #         logger.info(f"Transaction status response: {status_response}")
        #         print(f"Transaction status: {json.dumps(status_response, indent=2)}")
        #     except Exception as e:
        #         logger.error(f"❌ Error checking transaction status: {str(e)}")

        # Final Supabase check for all callbacks
        logger.info("Checking Supabase for all received callbacks...")
        try:
            supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
            response = supabase.table("transactions").select("*").execute()
            callbacks = response.data
            if callbacks:
                logger.info(f"Found {len(callbacks)} total callbacks")
                for callback in callbacks:
                    print(f"Callback: {callback}")
            else:
                logger.warning("No callbacks found in Supabase")
        except Exception as e:
            logger.error(f"Error querying Supabase: {str(e)}")

        """
        Example M-Pesa Callback Data Structure

        Below are examples of M-Pesa callback data for successful and failed STK Push transactions.
        These are provided for reference to understand the expected structure when implementing
        callback handling at the endpoint specified in MPESA_CALLBACK_URL.

        Successful Callback Example:
        {
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

        Failed Callback Example:
        {
            "Body": {
                "stkCallback": {
                    "MerchantRequestID": "29115-34620561-1",
                    "CheckoutRequestID": "ws_CO_191220191020363925",
                    "ResultCode": 1032,
                    "ResultDesc": "Request canceled by user."
                }
            }
        }

        Use the MpesaClient.parse_callback_data method to process these callbacks in your application.
        Ensure your callback endpoint (e.g., MPESA_CALLBACK_URL) is configured to receive and handle these responses.
        """

    except Exception as e:
        logger.error(f"❌ Test error: {str(e)}")
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    run_tests()