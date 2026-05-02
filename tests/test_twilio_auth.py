from twilio.rest import Client
from dotenv import load_dotenv
import os
from pathlib import Path


env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path, override=True)



auth_token = os.getenv('TWILIO_AUTH_TOKEN')
print(f"Auth Token: '{auth_token}'")
account_sid = "AC525f8411a5a1219325127c185d9a3bc6"

client = Client(account_sid, auth_token)
# Just try to list accounts – this will fail if auth is wrong
try:
    accounts = client.api.accounts.list(limit=1)
    print("Authentication successful!")
except Exception as e:
    print(f"Auth failed: {e}")