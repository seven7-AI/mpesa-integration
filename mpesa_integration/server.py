from flask import Flask, request, jsonify
import logging
import json
from datetime import datetime
import os
from supabase import create_client, Client
from dotenv import load_dotenv
from mpesa_integration.mpesa import MpesaClient, MpesaConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mpesa_callbacks.log'),  # Save logs to file
        logging.StreamHandler()  # Print to console
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Load environment variables
load_dotenv()

# Initialize Supabase client
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
if not supabase_url or not supabase_key:
    logger.error("SUPABASE_URL and SUPABASE_KEY must be set in .env")
    raise ValueError("Missing Supabase credentials")
supabase: Client = create_client(supabase_url, supabase_key)
logger.info("Initialized Supabase client")

# Initialize MpesaClient for parsing callbacks
config = MpesaConfig(
    consumer_key=os.getenv("MPESA_CONSUMER_KEY"),
    consumer_secret=os.getenv("MPESA_CONSUMER_SECRET"),
    shortcode=os.getenv("SHORT_CODE"),
    passkey=os.getenv("MPESA_PASSKEY"),
    callback_url=os.getenv("MPESA_CALLBACK_URL"),
    initiator_name=os.getenv("MPESA_INITIATOR_NAME"),
    initiator_password=os.getenv("MPESA_INITIATOR_PASSWORD"),
    certificate_path=os.getenv("MPESA_CERTIFICATE_PATH"),
    result_url=os.getenv("MPESA_RESULT_URL"),
    queue_timeout_url=os.getenv("MPESA_QUEUE_TIMEOUT_URL"),
    environment=os.getenv("MPESA_ENVIRONMENT", "sandbox"),
    request_timeout=float(os.getenv("MPESA_REQUEST_TIMEOUT", 30.0)),
    max_retries=int(os.getenv("MPESA_MAX_RETRIES", 3)),
    retry_delay=float(os.getenv("MPESA_RETRY_DELAY", 5.0))
)
mpesa_client = MpesaClient(config)

def save_callback_data(parsed_data, callback_type):
    """Save parsed callback data to Supabase."""
    try:
        data = {
            "merchant_request_id": parsed_data.get('merchant_request_id'),
            "checkout_request_id": parsed_data.get('checkout_request_id'),
            "result_code": parsed_data.get('result_code'),
            "result_desc": parsed_data.get('result_desc'),
            "amount": parsed_data.get('amount'),
            "receipt_number": parsed_data.get('receipt_number'),
            "transaction_date": parsed_data.get('transaction_date'),
            "phone_number": parsed_data.get('phone_number'),
            "callback_type": callback_type
        }
        response = supabase.table("transactions").insert(data).execute()
        logger.info(f"Saved {callback_type} callback to Supabase: {response.data}")
    except Exception as e:
        logger.error(f"Error saving callback to Supabase: {str(e)}")
        raise

def is_valid_mpesa_ip(ip_address):
    """Validate if the request comes from a Safaricom IP (placeholder)."""
    # Safaricom IP ranges (contact Safaricom for exact ranges)
    allowed_ips = ['196.201.214.0/24', '197.248.0.0/16']
    from ipaddress import ip_address, ip_network
    try:
        client_ip = ip_address(ip_address)
        return any(client_ip in ip_network(cidr) for cidr in allowed_ips)
    except ValueError:
        return False

@app.route('/api/mpesa/callback', methods=['POST'])
def mpesa_callback():
    """Handle M-Pesa STK Push callback."""
    try:
        # Validate source IP (optional, uncomment to enable)
        # client_ip = request.remote_addr
        # if not is_valid_mpesa_ip(client_ip):
        #     logger.error(f"Unauthorized callback from IP: {client_ip}")
        #     return jsonify({"ResultCode": 1, "ResultDesc": "Unauthorized source"}), 403

        # Validate callback token
        token = request.args.get('token')
        if token != os.getenv("CALLBACK_TOKEN"):
            logger.error("Invalid callback token")
            return jsonify({"ResultCode": 1, "ResultDesc": "Invalid token"}), 403

        if not request.is_json:
            logger.error("Invalid callback: No JSON data received")
            return jsonify({"ResultCode": 1, "ResultDesc": "Invalid data format"}), 400

        callback_data = request.json
        logger.info(f"Received STK Push callback: {json.dumps(callback_data, indent=2)}")

        # Parse callback using MpesaClient
        parsed_data = mpesa_client.parse_callback_data(callback_data)

        # Save to Supabase
        save_callback_data(parsed_data, 'stk_push')

        return jsonify({"ResultCode": 0, "ResultDesc": "Success"})

    except ValueError as e:
        logger.error(f"Error parsing callback: {str(e)}")
        return jsonify({"ResultCode": 1, "ResultDesc": str(e)}), 400
    except Exception as e:
        logger.error(f"Unexpected error in callback: {str(e)}")
        return jsonify({"ResultCode": 1, "ResultDesc": "Internal server error"}), 500

@app.route('/api/mpesa/result', methods=['POST'])
def mpesa_result():
    """Handle M-Pesa Transaction Status result callback."""
    try:
        if not request.is_json:
            logger.error("Invalid result callback: No JSON data received")
            return jsonify({"ResultCode": 1, "ResultDesc": "Invalid data format"}), 400

        callback_data = request.json
        logger.info(f"Received Transaction Status result callback: {json.dumps(callback_data, indent=2)}")

        # Simplified parsing for Transaction Status
        parsed_data = {
            'merchant_request_id': callback_data.get('Result', {}).get('MerchantRequestID'),
            'checkout_request_id': callback_data.get('Result', {}).get('CheckoutRequestID'),
            'result_code': callback_data.get('Result', {}).get('ResultCode'),
            'result_desc': callback_data.get('Result', {}).get('ResultDesc'),
            'amount': None,
            'receipt_number': next((param['Value'] for param in callback_data.get('Result', {}).get('ResultParameters', {}).get('ResultParameter', []) if param.get('Key') == 'ReceiptNo'), None),
            'transaction_date': None,
            'phone_number': None
        }
        save_callback_data(parsed_data, 'transaction_status_result')

        return jsonify({"ResultCode": 0, "ResultDesc": "Success"})

    except Exception as e:
        logger.error(f"Error in result callback: {str(e)}")
        return jsonify({"ResultCode": 1, "ResultDesc": "Internal server error"}), 500

@app.route('/api/mpesa/timeout', methods=['POST'])
def mpesa_timeout():
    """Handle M-Pesa Transaction Status timeout callback."""
    try:
        if not request.is_json:
            logger.error("Invalid timeout callback: No JSON data received")
            return jsonify({"ResultCode": 1, "ResultDesc": "Invalid data format"}), 400

        callback_data = request.json
        logger.info(f"Received Transaction Status timeout callback: {json.dumps(callback_data, indent=2)}")

        # Simplified parsing for timeout
        parsed_data = {
            'merchant_request_id': callback_data.get('Result', {}).get('MerchantRequestID'),
            'checkout_request_id': callback_data.get('Result', {}).get('CheckoutRequestID'),
            'result_code': callback_data.get('Result', {}).get('ResultCode'),
            'result_desc': callback_data.get('Result', {}).get('ResultDesc'),
            'amount': None,
            'receipt_number': None,
            'transaction_date': None,
            'phone_number': None
        }
        save_callback_data(parsed_data, 'transaction_status_timeout')

        return jsonify({"ResultCode": 0, "ResultDesc": "Success"})

    except Exception as e:
        logger.error(f"Error in timeout callback: {str(e)}")
        return jsonify({"ResultCode": 1, "ResultDesc": "Internal server error"}), 500

if __name__ == '__main__':
    logger.info("Starting callback server on port 5000...")
    app.run(host='0.0.0.0', port=5000, debug=False)