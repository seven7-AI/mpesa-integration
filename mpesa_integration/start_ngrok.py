from pyngrok import ngrok
import os
from dotenv import load_dotenv, set_key

load_dotenv()
ngrok_tunnel = ngrok.connect(5000, bind_tls=True)
public_url = ngrok_tunnel.public_url
print(f"Ngrok URL: {public_url}")

env_file = ".env"
set_key(env_file, "MPESA_CALLBACK_URL", f"{public_url}/api/mpesa/callback?token=your_secret")
set_key(env_file, "MPESA_RESULT_URL", f"{public_url}/api/mpesa/result")
set_key(env_file, "MPESA_QUEUE_TIMEOUT_URL", f"{public_url}/api/mpesa/timeout")

print("Updated .env with new ngrok URLs")
input("Press Enter to stop ngrok...")