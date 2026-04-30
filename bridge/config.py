import os

# Serial port -- (check with `ls /dev/tty*`)
SERIAL_PORT = '/dev/ttyUSB0'   

# Database file – absolute path recommended
DB_PATH = '/home/pi/meshcore-emergency-bridge/data.db'

# External forwarding (set to None if not used/ not currently testing)
FORWARD_HTTP_URL = None      #  
FORWARD_SMS_TO = None          # change back toNone
TWILIO_ACCOUNT_SID = None #
TWILIO_AUTH_TOKEN = None  #
TWILIO_FROM = None  #

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