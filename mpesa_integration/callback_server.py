from flask import Flask, request, jsonify
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/api/mpesa/callback', methods=['POST'])
def mpesa_callback():
    logger.info(f"Received M-Pesa callback: {request.json}")
    return jsonify({"ResultCode": 0, "ResultDesc": "Success"})

if __name__ == '__main__':
    logger.info("Starting callback server on port 5000...")
    app.run(host='0.0.0.0', port=5000) 