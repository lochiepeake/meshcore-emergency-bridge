from pathlib import Path
from dotenv import load_dotenv
import os

# Build the path to the .env file located in the parent directory of this script
env_path = Path(__file__).parent.parent / '.env'

# Load the .env file, using an absolute path and forcing it to overwrite
load_dotenv(dotenv_path=env_path, override=True)

# Now, after loading, fetch your variables
account_sid = os.getenv('TWILIO_ACCOUNT_SID')
auth_token = os.getenv('TWILIO_AUTH_TOKEN')


print(f"Account SID: '{account_sid}'")
print(f"Auth Token: '{auth_token}'")