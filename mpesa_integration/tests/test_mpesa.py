import unittest
from mpesa_integration import MpesaClient, MpesaConfig

class TestMpesaClient(unittest.TestCase):
    def setUp(self):
        self.config = MpesaConfig(
            consumer_key="test_key",
            consumer_secret="test_secret",
            shortcode="174379",
            passkey="test_passkey",
            callback_url="https://example.com/callback",
            environment="sandbox"
        )
        self.client = MpesaClient(self.config)

    def test_timestamp_format(self):
        timestamp = self.client._get_timestamp()
        self.assertEqual(len(timestamp), 14)  # YYYYMMDDHHMMSS

if __name__ == "__main__":
    unittest.main()