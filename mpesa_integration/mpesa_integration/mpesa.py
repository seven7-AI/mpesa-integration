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
        self.transaction_status_url = f"{base_url}/mpesa/transactionstatus/v1/query"
        
        # Log initialization
        self.logger.info(f"Initialized MpesaClient with environment: {config.environment}")
        self.logger.debug(f"Using auth URL: {self.auth_url}")
        self.logger.debug(f"Using STK push URL: {self.stk_push_url}")
        self.logger.debug(f"Using transaction status URL: {self.transaction_status_url}")

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

    def check_transaction_status(self, transaction_id: str, identifier_type: str = "4", 
                                 remarks: str = "Transaction Status Query", occasion: str = "") -> dict:
        """
        Check the status of a transaction using its ID.
        
        Args:
            transaction_id: The CheckoutRequestID from the STK push response
            identifier_type: Type of organization receiving the transaction (default: "4" for shortcode)
            remarks: Comments to be sent with the transaction
            occasion: Optional parameter for additional information
            
        Returns:
            dict: The transaction status response from M-Pesa
        """
        try:
            # Get access token
            access_token = self.get_access_token()
            
            # Generate password for the request
            timestamp = self._get_timestamp()
            password = self._generate_password(timestamp)
            
            # Prepare the request payload - following M-Pesa's specific format
            payload = {
                "BusinessShortCode": self.config.business_shortcode or self.config.shortcode,
                "Password": password,
                "Timestamp": timestamp,
                "CheckoutRequestID": transaction_id
            }
            
            # Set request headers
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            # Use the query request URL specifically for STK push query
            query_url = f"{self.stk_push_url}/query"
            
            self.logger.info(f"Checking transaction status for ID: {transaction_id}")
            self.logger.debug(f"Transaction status request payload: {payload}")
            self.logger.debug(f"Transaction status request headers: {headers}")
            self.logger.debug(f"Using query URL: {query_url}")
            
            # Send the request
            response = requests.post(
                query_url,
                json=payload,
                headers=headers,
                timeout=30
            )
            
            self.logger.debug(f"Transaction status response: {response.status_code} - {response.text}")
            
            # Handle response
            if response.status_code != 200:
                error_message = f"Transaction status check failed with status {response.status_code}: {response.text}"
                self.logger.error(error_message)
                raise Exception(error_message)
            
            # Parse response
            status_data = response.json()
            self.logger.info(f"Transaction status check successful: {status_data}")
            return status_data
            
        except requests.RequestException as e:
            self.logger.error(f"Network error checking transaction status: {str(e)}")
            raise Exception(f"Network error: {str(e)}")
        except ValueError as e:
            self.logger.error(f"JSON parsing error: {str(e)}")
            raise Exception(f"Invalid response format: {str(e)}")
        except Exception as e:
            self.logger.error(f"Error checking transaction status: {str(e)}")
            raise Exception(f"Error checking transaction status: {str(e)}")
    
    def parse_callback_data(self, callback_data: dict) -> dict:
        """
        Parse the callback data received from M-Pesa.
        
        Args:
            callback_data: The callback data received from M-Pesa
            
        Returns:
            dict: Parsed callback data with useful fields extracted
        """
        try:
            self.logger.info("Parsing M-Pesa callback data")
            self.logger.debug(f"Raw callback data: {callback_data}")
            
            # Check if it's a proper callback structure
            if "Body" not in callback_data or "stkCallback" not in callback_data["Body"]:
                raise ValueError("Invalid callback data format: missing Body or stkCallback")
            
            stk_callback = callback_data["Body"]["stkCallback"]
            result = {
                "merchant_request_id": stk_callback.get("MerchantRequestID"),
                "checkout_request_id": stk_callback.get("CheckoutRequestID"),
                "result_code": stk_callback.get("ResultCode"),
                "result_desc": stk_callback.get("ResultDesc"),
                "succeeded": stk_callback.get("ResultCode") == 0
            }
            
            # Extract additional metadata if available (only in successful transactions)
            if stk_callback.get("ResultCode") == 0 and "CallbackMetadata" in stk_callback:
                metadata = stk_callback["CallbackMetadata"].get("Item", [])
                
                # Process each metadata item
                for item in metadata:
                    name = item.get("Name")
                    value = item.get("Value")
                    
                    if name == "Amount":
                        result["amount"] = value
                    elif name == "MpesaReceiptNumber":
                        result["receipt_number"] = value
                    elif name == "TransactionDate":
                        # Convert date format if needed
                        result["transaction_date"] = value
                    elif name == "PhoneNumber":
                        result["phone_number"] = value
            
            self.logger.info(f"Parsed callback data: {result}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error parsing callback data: {str(e)}")
            raise Exception(f"Error parsing callback data: {str(e)}")