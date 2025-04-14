import os
import sys
import logging
from dotenv import load_dotenv
# This assumes 'mpesa_integration' package is installed and contains 'mpesa.py'
# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
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

# For Till Payment
config_till = MpesaConfig(
    consumer_key=os.getenv("MPESA_CONSUMER_KEY"),
    consumer_secret=os.getenv("MPESA_SECRET_KEY"),
    shortcode="174379",
    passkey=os.getenv("MPESA_PASSKEY"),
    callback_url="https://your-domain.com/callback",
    environment="sandbox"  # or "production"
)

# For Paybill Payment
config_paybill = MpesaConfig(
    consumer_key=os.getenv("MPESA_CONSUMER_KEY"),
    consumer_secret=os.getenv("MPESA_SECRET_KEY"),
    shortcode="5536682",  # Account number
    passkey=os.getenv("MPESA_PASSKEY"),
    callback_url="https://your-domain.com/callback",
    business_shortcode="522533",  # Business number
    environment="sandbox"
)

# Choose which config to use for the client
# For example, using Paybill config:
# client = MpesaClient(config_paybill)
# Or using Till config:
client = MpesaClient(config_till)

try:
    # Try to just get an access token first to isolate the issue
    logger.info("Attempting to get access token...")
    access_token = client.get_access_token()
    logger.info("Successfully obtained access token")
    
    # Now try the full payment flow
    logger.info("Initiating payment...")
    response = client.initiate_payment(
        phone_number="254719321423",  # Remove the + for consistency
        amount=1,
        account_reference="test",
        transaction_desc="test"
    )
    logger.info(f"Payment response: {response}")
    print(response)
except Exception as e:
    logger.error(f"Error: {str(e)}")
    print(f"Error: {str(e)}")