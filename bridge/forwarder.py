import logging
import time
import requests
from config import (FORWARD_HTTP_URL, FORWARD_SMS_TO, TWILIO_ACCOUNT_SID,
                     TWILIO_FROM, FORWARD_MQTT_BROKER,
                    FORWARD_MQTT_PORT, FORWARD_MQTT_TOPIC, MAX_RETRIES)
from dotenv import load_dotenv
import os


logger = logging.getLogger(__name__)
env_path = '/home/pibridge/meshcore-emergency-bridge/.env'
load_dotenv(dotenv_path=env_path)
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')


# Optional imports – fail gracefully if libraries missing
try:
    from twilio.rest import Client
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False
    logger.warning("Twilio not installed – SMS forwarding disabled")

try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False
    logger.warning("paho-mqtt not installed – MQTT forwarding disabled")

def forward_emergency(pubkey, lat, lon, bat):
    """Attempt to forward emergency to all configured external services.
       Returns True if at least one succeeded."""
    success = False
    payload = {'src': pubkey, 'lat': lat, 'lon': lon, 'battery_mv': bat, 'timestamp': int(time.time())}

    # HTTP forwarding
    if FORWARD_HTTP_URL:
        try:
            r = requests.post(FORWARD_HTTP_URL, json=payload, timeout=5)
            if r.status_code in (200, 201, 202):
                logger.info("HTTP forward successful to %s", FORWARD_HTTP_URL)
                success = True
            else:
                logger.warning("HTTP forward returned %d", r.status_code)
        except Exception as e:
            logger.error("HTTP forward error: %s", e)

    # SMS forwarding (Twilio)
    if FORWARD_SMS_TO and TWILIO_ACCOUNT_SID and TWILIO_AVAILABLE:
        logger.info(f"SMS forwarder is active! Trying to send to {FORWARD_SMS_TO}")
        try:
            client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
            logger.info("Twilio client object created successfully.")
            message_body = f"EMERGENCY from {pubkey}\nLocation: {lat},{lon}\nBattery: {bat}mV"
            msg = client.messages.create(
                body=message_body,
                from_=TWILIO_FROM,
                to=FORWARD_SMS_TO
            )
            logger.info("SMS sent, SID: %s", msg.sid)
            success = True
        except Exception as e:
            logger.error("SMS forward error: %s", e)

    # MQTT forwarding
    if FORWARD_MQTT_BROKER and MQTT_AVAILABLE:
        try:
            client = mqtt.Client()
            client.connect(FORWARD_MQTT_BROKER, FORWARD_MQTT_PORT, 60)
            client.publish(FORWARD_MQTT_TOPIC, json.dumps(payload))
            client.disconnect()
            logger.info("MQTT published to %s", FORWARD_MQTT_TOPIC)
            success = True
        except Exception as e:
            logger.error("MQTT forward error: %s", e)

    return success