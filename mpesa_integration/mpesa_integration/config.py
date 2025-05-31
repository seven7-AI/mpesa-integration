from dataclasses import dataclass
from typing import Optional
import re

@dataclass
class MpesaConfig:
    """Configuration for M-Pesa API client.

    Args:
        consumer_key: M-Pesa consumer key.
        consumer_secret: M-Pesa consumer secret.
        shortcode: M-Pesa shortcode (5-9 digits).
        passkey: M-Pesa passkey for password generation.
        callback_url: URL for STK Push callback notifications.
        business_shortcode: Optional business shortcode for Paybill (defaults to shortcode).
        environment: API environment ('sandbox' or 'production').
        initiator_name: Initiator username for Transaction Status API (optional).
        initiator_password: Initiator password for SecurityCredential (optional).
        certificate_path: Path to M-Pesa public certificate (optional).
        result_url: URL for Transaction Status result notifications (optional).
        queue_timeout_url: URL for Transaction Status timeout notifications (optional).
        request_timeout: HTTP request timeout in seconds (default: 30).
        max_retries: Max retries for transaction status checks (default: 3).
        retry_delay: Delay between retries in seconds (default: 5).

    Raises:
        ValueError: If configuration fields are invalid.
    """
    consumer_key: str
    consumer_secret: str
    shortcode: str
    passkey: str
    callback_url: str
    business_shortcode: Optional[str] = None
    environment: str = "sandbox"
    initiator_name: Optional[str] = None
    initiator_password: Optional[str] = None
    certificate_path: Optional[str] = None
    result_url: Optional[str] = None
    queue_timeout_url: Optional[str] = None
    request_timeout: float = 30.0
    max_retries: int = 3
    retry_delay: float = 5.0

    def __post_init__(self):
        """Validate configuration fields."""
        if self.environment not in ["sandbox", "production"]:
            raise ValueError("Environment must be 'sandbox' or 'production'")
        if not self.consumer_key or not self.consumer_secret:
            raise ValueError("consumer_key and consumer_secret are required")
        if not self.shortcode or not re.match(r"^\d{5,9}$", self.shortcode):
            raise ValueError("shortcode must be a 5-9 digit number")
        if not self.passkey:
            raise ValueError("passkey is required")
        if not self.callback_url or not re.match(r"^https?://", self.callback_url):
            raise ValueError("callback_url must be a valid URL")
        if self.business_shortcode and not re.match(r"^\d{5,9}$", self.business_shortcode):
            raise ValueError("business_shortcode must be a 5-9 digit number")
        if self.result_url and not re.match(r"^https?://", self.result_url):
            raise ValueError("result_url must be a valid URL")
        if self.queue_timeout_url and not re.match(r"^https?://", self.queue_timeout_url):
            raise ValueError("queue_timeout_url must be a valid URL")
        if self.request_timeout <= 0:
            raise ValueError("request_timeout must be positive")
        if self.max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        if self.retry_delay < 0:
            raise ValueError("retry_delay must be non-negative")
        if not self.business_shortcode:
            self.business_shortcode = self.shortcode