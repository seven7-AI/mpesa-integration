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
        
        # Define API endpoints based on environment
        base_url = "https://sandbox.safaricom.co.ke" if config.environment == "sandbox" else "https://api.safaricom.co.ke"
        self.auth_url = f"{base_url}/oauth/v1/generate?grant_type=client_credentials"
        self.stk_push_url = f"{base_url}/mpesa/stkpush/v1/processrequest"
        
        # Log initialization
        self.logger.info(f"Initialized MpesaClient with environment: {config.environment}")
        self.logger.debug(f"Using auth URL: {self.auth_url}")
        self.logger.debug(f"Using STK push URL: {self.stk_push_url}")

    def _get_basic_auth(self) -> str:
        """Generate Base64 encoded Basic Auth string."""
        auth_str = f"{self.config.consumer_key}:{self.config.consumer_secret}"
        encoded_auth = base64.b64encode(auth_str.encode()).decode('utf-8')
        basic_auth = f"Basic {encoded_auth}"
        self.logger.debug(f"Generated Basic Auth: {basic_auth}")
        return basic_auth

    def get_access_token(self) -> str:
        """Retrieve M-Pesa access token."""
        try:
            basic_auth = self._get_basic_auth()
            headers = {"Authorization": basic_auth}
            
            self.logger.debug(f"Requesting access token from {self.auth_url}")
            self.logger.debug(f"Using auth header: {headers}")
            
            response = requests.get(self.auth_url, headers=headers, timeout=10)
            self.logger.debug(f"Access token response status: {response.status_code}")
            self.logger.debug(f"Access token response body: {response.text}")
            
            if response.status_code != 200:
                self.logger.error(f"Failed to get access token: {response.status_code} - {response.text}")
                raise MpesaAuthError(f"Failed to get access token: {response.status_code} - {response.text}")
            
            data = response.json()
            if "access_token" not in data:
                self.logger.error(f"No access token in response: {response.text}")
                raise MpesaAuthError(f"No access token in response: {response.text}")
            
            access_token = data["access_token"]
            self.logger.info(f"Access token retrieved successfully")
            return access_token
        
        except requests.RequestException as e:
            self.logger.error(f"Network error getting access token: {str(e)}")
            raise MpesaAuthError(f"Network error: {str(e)}")
        except ValueError as e:
            self.logger.error(f"JSON parsing error: {str(e)}")
            raise MpesaAuthError(f"Invalid response format: {str(e)}")
        except Exception as e:
            self.logger.error(f"Unexpected error getting access token: {str(e)}")
            raise MpesaAuthError(f"Unexpected error: {str(e)}")

    def _get_timestamp(self) -> str:
        """Get formatted timestamp for the request."""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        self.logger.debug(f"Generated timestamp: {timestamp}")
        return timestamp

    def _generate_password(self, timestamp: str) -> str:
        """Generate the password for the request."""
        # Use business_shortcode if available, otherwise use shortcode
        code = self.config.business_shortcode or self.config.shortcode
        password_str = f"{code}{self.config.passkey}{timestamp}"
        password = base64.b64encode(password_str.encode()).decode('utf-8')
        self.logger.debug(f"Generated password from: {code}{self.config.passkey}{timestamp}")
        self.logger.debug(f"Encoded password: {password}")
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
                "BusinessShortCode": self.config.business_shortcode or self.config.shortcode,
                "Password": password,
                "Timestamp": timestamp,
                "TransactionType": transaction_type,
                "Amount": int(amount),  # Ensure amount is an integer
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
            self.logger.debug(f"Payment request headers: {headers}")
            
            response = requests.post(self.stk_push_url, json=payload, headers=headers, timeout=10)
            self.logger.debug(f"Payment response: {response.status_code} - {response.text}")
            
            if response.status_code != 200:
                raise MpesaPaymentError(f"Payment failed with status {response.status_code}: {response.text}")
            
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