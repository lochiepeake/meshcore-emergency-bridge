#!/usr/bin/env python3
import threading
import time
import logging
import sys
import os

# Add parent directory to path if needed (for running directly)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from meshcore import MeshCore
from config import SERIAL_PORT, DB_PATH, STATS_INTERVAL, LOG_LEVEL, MAX_RETRIES, RETRY_DELAYS
from database import (init_db, store_node, store_breadcrumb, store_emergency,
                      update_emergency_status, increment_emergency_retries)
from emergency_classifier import is_emergency, parse_sos
from forwarder import forward_emergency
from ack_generator import send_ack
from utils import setup_logging

setup_logging(LOG_LEVEL)
logger = logging.getLogger(__name__)

# Global variables
mc = None
forward_queue = []   # each item: (msg_id, pubkey, lat, lon, bat, retries)

def on_text(msg):
    logger.info("TXT from %s: %s", msg.src, msg.text)
    if is_emergency(msg.text):
        data = parse_sos(msg.text)
        msg_id = store_emergency(DB_PATH, msg.src, msg.text,
                                 data['lat'], data['lon'], data['alt'], data['bat'])
        forward_queue.append((msg_id, msg.src, data['lat'], data['lon'], data['bat'], 0))
        logger.info("Emergency stored ID=%d, queued", msg_id)
    elif msg.text.startswith('LOC|'):
        data = parse_sos(msg.text)   # reuse parser
        store_breadcrumb(DB_PATH, msg.src, data['lat'], data['lon'],
                         data['alt'], data['bat'], msg.rssi, msg.snr)
        store_node(DB_PATH, msg.src, lat=data['lat'], lon=data['lon'],
                   alt=data['alt'], bat=data['bat'], rssi=msg.rssi, snr=msg.snr)
        logger.info("Location stored for %s", msg.src)

def on_advert(ad):
    logger.info("Advert from %s: name=%s, lat=%f, lon=%f",
                ad.src, ad.name, ad.latitude/1e6, ad.longitude/1e6)
    lat = ad.latitude / 1e6 if ad.latitude else None
    lon = ad.longitude / 1e6 if ad.longitude else None
    if lat is not None and lon is not None:
        store_breadcrumb(DB_PATH, ad.src, lat, lon, None, None, ad.rssi, ad.snr)
    store_node(DB_PATH, ad.src, name=ad.name, lat=lat, lon=lon,
               rssi=ad.rssi, snr=ad.snr)

def on_stats(stats):
    logger.info("Stats: battery=%s mV, uptime=%s s", stats.get('battery_mv'), stats.get('uptime_secs'))
    # Use safe .get() with defaults
    store_telemetry(DB_PATH, "gateway",
                    stats.get('battery_mv'), stats.get('uptime_secs'), stats.get('queue_len'),
                    stats.get('noise_floor'), stats.get('last_rssi'), stats.get('last_snr'),
                    stats.get('tx_air_secs'), stats.get('rx_air_secs'),
                    stats.get('flood_tx'), stats.get('direct_tx'),
                    stats.get('flood_rx'), stats.get('direct_rx'))

def forward_worker():
    """Background thread that processes the forwarding queue with retries."""
    while True:
        if forward_queue:
            item = forward_queue.pop(0)
            msg_id, pubkey, lat, lon, bat, retries = item
            success = forward_emergency(pubkey, lat, lon, bat)
            if success:
                update_emergency_status(DB_PATH, msg_id, 'success')
                send_ack(mc, pubkey, msg_id)
            else:
                # Increment retry count in DB
                new_retries = increment_emergency_retries(DB_PATH, msg_id)
                if new_retries <= MAX_RETRIES:
                    delay = RETRY_DELAYS[min(new_retries-1, len(RETRY_DELAYS)-1)]
                    logger.info("Retry %d for emergency %d in %d seconds", new_retries, msg_id, delay)
                    # Re-add with updated retries after delay
                    def delayed_retry():
                        time.sleep(delay)
                        forward_queue.append((msg_id, pubkey, lat, lon, bat, new_retries))
                    threading.Thread(target=delayed_retry, daemon=True).start()
                else:
                    logger.error("Emergency %d failed after %d retries", msg_id, MAX_RETRIES)
                    update_emergency_status(DB_PATH, msg_id, 'failed')
        time.sleep(1)

def stats_poller():
    """Periodically request stats from the MeshCore companion."""
    while True:
        time.sleep(STATS_INTERVAL)
        if mc:
            try:
                mc.get_stats()
            except Exception as e:
                logger.error("Stats request failed: %s", e)

def main():
    global mc
    init_db(DB_PATH)
    try:
        mc = MeshCore(SERIAL_PORT)
    except Exception as e:
        logger.error("Cannot open serial port %s: %s", SERIAL_PORT, e)
        sys.exit(1)
    mc.subscribe_text(on_text)
    mc.subscribe_advert(on_advert)
    mc.subscribe_stats(on_stats)

    threading.Thread(target=forward_worker, daemon=True).start()
    threading.Thread(target=stats_poller, daemon=True).start()

    logger.info("Bridge started. Listening on %s", SERIAL_PORT)
    try:
        mc.run()   # blocks
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error("MeshCore run error: %s", e)

if __name__ == '__main__':
    main()