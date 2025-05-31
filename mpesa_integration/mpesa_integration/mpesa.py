import base64
import logging
from datetime import datetime
import requests
import time
from typing import Dict, Any, Optional
from .config import MpesaConfig
from .exceptions import MpesaAuthError, MpesaPaymentError, MpesaTransactionError
import re
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend

class MpesaClient:
    """Client for M-Pesa STK Push and Transaction Status APIs supporting Till and Paybill payments.

    Args:
        config (MpesaConfig): Configuration object containing M-Pesa credentials and settings.

    Raises:
        ValueError: If required configuration fields are missing or invalid.
    """
    
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

    def _generate_security_credential(self) -> str:
        """Generate encrypted SecurityCredential for Transaction Status API.

        Returns:
            str: Base64-encoded encrypted initiator password.

        Raises:
            MpesaAuthError: If certificate or initiator password is invalid.
        """
        if not self.config.initiator_name or not self.config.initiator_password or not self.config.certificate_path:
            self.logger.error("Initiator name, password, or certificate path missing for SecurityCredential")
            raise MpesaAuthError("Initiator name, password, and certificate path required for Transaction Status")
        
        try:
            with open(self.config.certificate_path, "rb") as cert_file:
                cert_data = cert_file.read()
                public_key = serialization.load_pem_public_key(cert_data, backend=default_backend())
            
            encrypted = public_key.encrypt(
                self.config.initiator_password.encode(),
                padding.PKCS1v15()
            )
            security_credential = base64.b64encode(encrypted).decode('utf-8')
            self.logger.debug("Generated SecurityCredential successfully")
            return security_credential
        except Exception as e:
            self.logger.error(f"Failed to generate SecurityCredential: {str(e)}")
            raise MpesaAuthError(f"Failed to generate SecurityCredential: {str(e)}")

    def get_access_token(self) -> str:
        """Retrieve M-Pesa access token.

        Returns:
            str: Access token for API authentication.

        Raises:
            MpesaAuthError: If token retrieval fails.
        """
        try:
            basic_auth = self._get_basic_auth()
            headers = {"Authorization": basic_auth}
            
            self.logger.debug(f"Requesting access token from {self.auth_url}")
            self.logger.debug(f"Using auth header: {headers}")
            
            response = requests.get(self.auth_url, headers=headers, timeout=self.config.request_timeout)
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

    def _generate_password(self, timestamp: str, shortcode: Optional[str] = None) -> str:
        """Generate the password for the request."""
        code = shortcode or self.config.business_shortcode or self.config.shortcode
        password_str = f"{code}{self.config.passkey}{timestamp}"
        password = base64.b64encode(password_str.encode()).decode('utf-8')
        self.logger.debug(f"Generated password from: {code}...{timestamp}")
        self.logger.debug(f"Encoded password: {password}")
        return password

    def _validate_phone_number(self, phone_number: str) -> str:
        """Validate and normalize phone number format.

        Args:
            phone_number: Phone number to validate.

        Returns:
            str: Normalized phone number.

        Raises:
            ValueError: If phone number is invalid.
        """
        cleaned_number = phone_number.replace("+", "").replace(" ", "")
        if not re.match(r"^254[1-7][0-9]{8}$", cleaned_number):
            self.logger.error(f"Invalid phone number format: {cleaned_number}")
            raise ValueError(f"Phone number must be 12 digits starting with 254 (e.g., 2547XXXXXXXX)")
        return cleaned_number

    def initiate_payment(
        self,
        phone_number: str,
        amount: float,
        account_reference: str,
        transaction_desc: str,
        transaction_type: str = None,
        shortcode: Optional[str] = None
    ) -> Dict[str, Any]:
        """Initiate an STK Push payment.

        Args:
            phone_number: M-PESA registered phone number (e.g., 2547XXXXXXXX).
            amount: Transaction amount (whole numbers only).
            account_reference: Transaction identifier (max 12 characters).
            transaction_desc: Transaction description (max 13 characters).
            transaction_type: Transaction type ('CustomerPayBillOnline' or 'CustomerBuyGoodsOnline').
            shortcode: Optional override for the config shortcode.

        Returns:
            Dict[str, Any]: Payment response from M-Pesa.

        Raises:
            ValueError: If input parameters are invalid.
            MpesaPaymentError: If payment initiation fails.
        """
        if not phone_number or not amount:
            raise ValueError("phone_number and amount are required")
        if not account_reference or not transaction_desc:
            raise ValueError("account_reference and transaction_desc are required")
        if len(account_reference) > 12:
            raise ValueError("account_reference must be 12 characters or less")
        if len(transaction_desc) > 13:
            raise ValueError("transaction_desc must be 13 characters or less")
        
        valid_transaction_types = ["CustomerPayBillOnline", "CustomerBuyGoodsOnline"]
        if transaction_type not in valid_transaction_types:
            self.logger.error(f"Invalid transaction_type: {transaction_type}. Must be one of {valid_transaction_types}")
            raise ValueError(f"Invalid transaction_type: {transaction_type}. Must be 'CustomerPayBillOnline' or 'CustomerBuyGoodsOnline'")

        if shortcode and not re.match(r"^\d{5,9}$", shortcode):
            raise ValueError("shortcode must be a 5-9 digit number")

        try:
            access_token = self.get_access_token()
            timestamp = self._get_timestamp()
            password = self._generate_password(timestamp, shortcode)

            phone_number = self._validate_phone_number(phone_number)
            effective_shortcode = shortcode or self.config.shortcode

            payload = {
                "BusinessShortCode": self.config.business_shortcode or effective_shortcode,
                "Password": password,
                "Timestamp": timestamp,
                "TransactionType": transaction_type,
                "Amount": int(amount),
                "PartyA": phone_number,
                "PartyB": effective_shortcode,
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
            
            response = requests.post(self.stk_push_url, json=payload, headers=headers, timeout=self.config.request_timeout)
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

    def check_transaction_status(
        self,
        transaction_id: str,
        originator_conversation_id: Optional[str] = None,
        identifier_type: str = "4",
        remarks: str = "Transaction Status Query",
        occasion: str = "",
        result_url: Optional[str] = None,
        queue_timeout_url: Optional[str] = None,
        shortcode: Optional[str] = None
    ) -> Dict[str, Any]:
        """Check the status of a transaction using its ID or OriginatorConversationID.

        Args:
            transaction_id: The TransactionID or CheckoutRequestID from the STK Push response.
            originator_conversation_id: Optional OriginatorConversationID for querying without TransactionID.
            identifier_type: Type of organization receiving the transaction (default: "4" for shortcode).
            remarks: Comments to be sent with the transaction (max 100 characters).
            occasion: Optional parameter for additional information (max 100 characters).
            result_url: Optional override for result URL.
            queue_timeout_url: Optional override for queue timeout URL.
            shortcode: Optional override for the config shortcode.

        Returns:
            Dict[str, Any]: Transaction status response from M-Pesa.

        Raises:
            ValueError: If input parameters are invalid.
            MpesaTransactionError: If status check fails.
        """
        if not transaction_id and not originator_conversation_id:
            raise ValueError("Either transaction_id or originator_conversation_id is required")
        if len(remarks) > 100:
            raise ValueError("remarks must be 100 characters or less")
        if len(occasion) > 100:
            raise ValueError("occasion must be 100 characters or less")
        if shortcode and not re.match(r"^\d{5,9}$", shortcode):
            raise ValueError("shortcode must be a 5-9 digit number")

        try:
            access_token = self.get_access_token()
            timestamp = self._get_timestamp()
            password = self._generate_password(timestamp, shortcode)
            security_credential = self._generate_security_credential()

            effective_shortcode = shortcode or self.config.shortcode
            effective_result_url = result_url or self.config.result_url or self.config.callback_url
            effective_queue_timeout_url = queue_timeout_url or self.config.queue_timeout_url or self.config.callback_url

            payload = {
                "Initiator": self.config.initiator_name,
                "SecurityCredential": security_credential,
                "CommandID": "TransactionStatusQuery",
                "TransactionID": transaction_id or "",
                "OriginatorConversationID": originator_conversation_id or "",
                "PartyA": effective_shortcode,
                "IdentifierType": identifier_type,
                "ResultURL": effective_result_url,
                "QueueTimeOutURL": effective_queue_timeout_url,
                "Remarks": remarks,
                "Occasion": occasion
            }

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }

            self.logger.info(f"Checking transaction status for ID: {transaction_id or originator_conversation_id}")
            self.logger.debug(f"Transaction status request payload: {payload}")
            self.logger.debug(f"Transaction status request headers: {headers}")

            for attempt in range(self.config.max_retries + 1):
                response = requests.post(
                    self.transaction_status_url,
                    json=payload,
                    headers=headers,
                    timeout=self.config.request_timeout
                )
                
                self.logger.debug(f"Transaction status response: {response.status_code} - {response.text}")
                
                if response.status_code != 200:
                    error_message = f"Transaction status check failed with status {response.status_code}: {response.text}"
                    self.logger.error(error_message)
                    raise MpesaTransactionError(error_message)
                
                status_data = response.json()
                if status_data.get("Result", {}).get("ResultType", 1) == 0:
                    self.logger.info(f"Transaction status check successful: {status_data}")
                    return status_data
                
                self.logger.info(f"Transaction still processing, retrying... (attempt {attempt + 1}/{self.config.max_retries})")
                time.sleep(self.config.retry_delay)
            
            raise MpesaTransactionError("Transaction status check timed out after maximum retries")

        except requests.RequestException as e:
            self.logger.error(f"Network error checking transaction status: {str(e)}")
            raise MpesaTransactionError(f"Network error: {str(e)}")
        except ValueError as e:
            self.logger.error(f"JSON parsing error: {str(e)}")
            raise MpesaTransactionError(f"Invalid response format: {str(e)}")
        except Exception as e:
            self.logger.error(f"Error checking transaction status: {str(e)}")
            raise MpesaTransactionError(f"Error checking transaction status: {str(e)}")

    def parse_callback_data(self, callback_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse the callback data received from M-Pesa.

        Args:
            callback_data: The callback data received from M-Pesa.

        Returns:
            Dict[str, Any]: Parsed callback data with useful fields extracted.

        Raises:
            ValueError: If callback data is invalid.
        """
        try:
            self.logger.info("Parsing M-Pesa callback data")
            self.logger.debug(f"Raw callback data: {callback_data}")
            
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
            
            if stk_callback.get("ResultCode") == 0 and "CallbackMetadata" in stk_callback:
                metadata = stk_callback["CallbackMetadata"].get("Item", [])
                
                for item in metadata:
                    name = item.get("Name")
                    value = item.get("Value")
                    
                    if name == "Amount":
                        result["amount"] = value
                    elif name == "MpesaReceiptNumber":
                        result["receipt_number"] = value
                    elif name == "TransactionDate":
                        result["transaction_date"] = value
                    elif name == "PhoneNumber":
                        result["phone_number"] = value
            
            self.logger.info(f"Parsed callback data: {result}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error parsing callback data: {str(e)}")
            raise ValueError(f"Error parsing callback data: {str(e)}")