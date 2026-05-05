import os

# Serial port -- (check with `ls /dev/tty*`)
SERIAL_PORT = '/dev/ttyUSB0'   

# Database file – absolute path recommended
DB_PATH = '/home/pibridge/meshcore-emergency-bridge/data.db'

# External forwarding (set to None if not used/ not currently testing)
FORWARD_HTTP_URL ="https://webhook.site/5a582fd1-81c9-4489-8543-e31819d55dec"

FORWARD_SMS_TO = "whatsapp:+447436840986"         
TWILIO_ACCOUNT_SID = "AC525f8411a5a1219325127c185d9a3bc6"
TWILIO_FROM = "whatsapp:+14155238886"

FORWARD_MQTT_BROKER = None     # add to test
FORWARD_MQTT_PORT = 1883
FORWARD_MQTT_TOPIC = 'mesh/emergency'

# Logging level (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL = 'INFO'

# Stats polling interval (seconds)
STATS_INTERVAL = 60

# Retry settings for forwarding
MAX_RETRIES = 4
RETRY_DELAYS = [5, 15, 45, 120]   # seconds between attempts