from mpesa_integration import MpesaClient, MpesaConfig

# For Till Payment
config = MpesaConfig(
    consumer_key="your_consumer_key",
    consumer_secret="your_consumer_secret",
    shortcode="174379",
    passkey="your_passkey",
    callback_url="https://your-domain.com/callback",
    environment="sandbox"  # or "production"
)

# For Paybill Payment
config = MpesaConfig(
    consumer_key="your_consumer_key",
    consumer_secret="your_consumer_secret",
    shortcode="5536682",  # Account number
    passkey="your_passkey",
    callback_url="https://your-domain.com/callback",
    business_shortcode="522533",  # Business number
    environment="sandbox"
)

client = MpesaClient(config)


response = client.initiate_payment(
    phone_number="+254719321423",
    amount=47,
    account_reference="test",
    transaction_desc="test"
)
print(response)