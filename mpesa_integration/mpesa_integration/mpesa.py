import base64
import logging
from datetime import datetime
import requests
from typing import Dict, Any
from .config import MpesaConfig
from .exceptions import MpesaAuthError, MpesaPaymentError

class MpesaClient:
    """Client for M-Pesa STK Push API supporting Till and Paybill payments."""
    
    def __init__(self, config: MpesaConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.base_url = (
            "https://sandbox.safaricom.co.ke" if config.environment == "sandbox"
            else "https://api.safaricom.co.ke"
        )
        self.auth_url = f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials"
        self.stk_push_url = f"{self.base_url}/mpesa/stkpush/v1/processrequest"

    def _get_basic_auth(self) -> str:
        """Generate Base64 encoded Basic Auth string."""
        auth_str = f"{self.config.consumer_key}:{self.config.consumer_secret}"
        return f"Basic {base64.b64encode(auth_str.encode()).decode('utf-8')}"

    def get_access_token(self) -> str:
        """Retrieve M-Pesa access token."""
        try:
            headers = {"Authorization": self._get_basic_auth()}
            self.logger.debug(f"Requesting access token from {self.auth_url}")
            response = requests.get(self.auth_url, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            if "access_token" not in data:
                raise MpesaAuthError(f"No access token in response: {response.text}")
            self.logger.info("Access token retrieved successfully")
            return data["access_token"]
        except requests.RequestException as e:
            self.logger.error(f"Network error getting access token: {str(e)}")
            raise MpesaAuthError(f"Network error: {str(e)}")
        except ValueError as e:
            self.logger.error(f"JSON parsing error: {str(e)}")
            raise MpesaAuthError(f"Invalid response format: {str(e)}")

    def _get_timestamp(self) -> str:
        """Generate timestamp in YYYYMMDDHHMMSS format."""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        self.logger.debug(f"Generated timestamp: {timestamp}")
        return timestamp

    def _generate_password(self, timestamp: str) -> str:
        """Generate STK Push password."""
        password_str = f"{self.config.shortcode}{self.config.passkey}{timestamp}"
        password = base64.b64encode(password_str.encode()).decode('utf-8')
        self.logger.debug("Generated password")
        return password

    def initiate_payment(
        self,
        phone_number: str,
        amount: float,
        account_reference: str,
        transaction_desc: str,
        transaction_type: str = "CustomerBuyGoodsOnline"
    ) -> Dict[str, Any]:
        """Initiate an STK Push payment."""
        if not phone_number or not amount:
            raise ValueError("phone_number and amount are required")
        if not account_reference or not transaction_desc:
            raise ValueError("account_reference and transaction_desc are required")

        try:
            access_token = self.get_access_token()
            timestamp = self._get_timestamp()
            password = self._generate_password(timestamp)

            # Normalize phone number (remove + or spaces)
            phone_number = phone_number.replace("+", "").replace(" ", "")

            payload = {
                "BusinessShortCode": self.config.business_shortcode,
                "Password": password,
                "Timestamp": timestamp,
                "TransactionType": transaction_type,
                "Amount": str(amount),
                "PartyA": phone_number,
                "PartyB": self.config.shortcode,
                "PhoneNumber": phone_number,
                "CallBackURL": self.config.callback_url,
                "AccountReference": account_reference,
                "TransactionDesc": transaction_desc
            }

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }

            self.logger.info(f"Initiating payment with payload: {payload}")
            response = requests.post(self.stk_push_url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            payment_data = response.json()
            self.logger.info(f"Payment initiated successfully: {payment_data}")
            return payment_data

        except requests.RequestException as e:
            self.logger.error(f"Network error during payment: {str(e)}")
            raise MpesaPaymentError(f"Network error: {str(e)}")
        except ValueError as e:
            self.logger.error(f"JSON parsing error: {str(e)}")
            raise MpesaPaymentError(f"Invalid response format: {str(e)}")
        except Exception as e:
            self.logger.error(f"Unexpected error: {str(e)}")
            raise MpesaPaymentError(f"Error: {str(e)}")