from dataclasses import dataclass
from typing import Optional

@dataclass
class MpesaConfig:
    consumer_key: str
    consumer_secret: str
    shortcode: str
    passkey: str
    callback_url: str
    business_shortcode: Optional[str] = None  # For Paybill, this is the business number
    environment: str = "sandbox"  # or "production"

    def __post_init__(self):
        if self.environment not in ["sandbox", "production"]:
            raise ValueError("Environment must be 'sandbox' or 'production'")
        if not self.business_shortcode:
            self.business_shortcode = self.shortcode  # Default for Till