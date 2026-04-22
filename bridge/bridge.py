#!/usr/bin/env python3
#!/usr/bin/env python3
import asyncio
import threading
import time
import logging
import sys
import os
import json
from meshcore import MeshCore, EventType

# Add parent directory to path if needed
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import SERIAL_PORT, DB_PATH, STATS_INTERVAL, LOG_LEVEL, MAX_RETRIES, RETRY_DELAYS
from database import (init_db, store_node, store_breadcrumb, store_emergency,
                      update_emergency_status, increment_emergency_retries, store_telemetry)
from emergency_classifier import is_emergency, parse_sos
from forwarder import forward_emergency
from ack_generator import send_ack_sync
from utils import setup_logging

setup_logging(LOG_LEVEL)
logger = logging.getLogger(__name__)

# Global variables
mc = None
forward_queue = []  # each item: (msg_id, pubkey, lat, lon, bat, retries)

def on_text(msg):
    """Handle incoming text messages."""
    logger.info(f"TXT from {msg.src}: {msg.text}")
    
    if is_emergency(msg.text):
        data = parse_sos(msg.text)
        msg_id = store_emergency(DB_PATH, msg.src, msg.text,
                                 data['lat'], data['lon'], data['alt'], data['bat'])
        forward_queue.append((msg_id, msg.src, data['lat'], data['lon'], data['bat'], 0))
        logger.info(f"Emergency stored ID={msg_id}, queued")
        
    elif msg.text.startswith('LOC|'):
        data = parse_sos(msg.text)
        rssi = getattr(msg, 'rssi', None)
        snr = getattr(msg, 'snr', None)
        store_breadcrumb(DB_PATH, msg.src, data['lat'], data['lon'],
                         data['alt'], data['bat'], rssi, snr)
        store_node(DB_PATH, msg.src, lat=data['lat'], lon=data['lon'],
                   alt=data['alt'], bat=data['bat'], rssi=rssi, snr=snr)
        logger.info(f"Location stored for {msg.src}")

def on_advert(ad):
    """Handle node adverts (contain location and name)."""
    logger.info(f"Advert from {ad.src}: name={ad.name}, lat={ad.latitude/1e6}, lon={ad.longitude/1e6}")
    lat = ad.latitude / 1e6 if ad.latitude else None
    lon = ad.longitude / 1e6 if ad.longitude else None
    rssi = getattr(ad, 'rssi', None)
    snr = getattr(ad, 'snr', None)
    if lat is not None and lon is not None:
        store_breadcrumb(DB_PATH, ad.src, lat, lon, None, None, rssi, snr)
    store_node(DB_PATH, ad.src, name=ad.name, lat=lat, lon=lon, rssi=rssi, snr=snr)

def on_stats(stats):
    """Handle incoming stats from companion."""
    logger.info(f"Stats received: battery={stats.get('battery_mv')}mV")
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
                # Send ACK synchronously
                send_ack_sync(pubkey, msg_id)
            else:
                new_retries = increment_emergency_retries(DB_PATH, msg_id)
                if new_retries <= MAX_RETRIES:
                    delay = RETRY_DELAYS[min(new_retries-1, len(RETRY_DELAYS)-1)]
                    logger.info(f"Retry {new_retries} for emergency {msg_id} in {delay} seconds")
                    def delayed_retry():
                        time.sleep(delay)
                        forward_queue.append((msg_id, pubkey, lat, lon, bat, new_retries))
                    threading.Thread(target=delayed_retry, daemon=True).start()
                else:
                    logger.error(f"Emergency {msg_id} failed after {MAX_RETRIES} retries")
                    update_emergency_status(DB_PATH, msg_id, 'failed')
        time.sleep(1)

async def stats_poller_async():
    """Periodically request stats from the MeshCore companion."""
    global mc
    while True:
        await asyncio.sleep(STATS_INTERVAL)
        if mc:
            try:
                await mc.commands.get_stats()
            except Exception as e:
                logger.error(f"Stats request failed: {e}")

async def main_async():
    global mc
    init_db(DB_PATH)
    
    try:
        # Use the correct async API
        mc = await MeshCore.create_serial(SERIAL_PORT, 115200, debug=True)
        logger.info(f"Connected to MeshCore on {SERIAL_PORT}")
    except Exception as e:
        logger.error(f"Cannot connect to serial port {SERIAL_PORT}: {e}")
        return
    
    # Set up event handlers
    @mc.on(EventType.TEXT_MESSAGE)
    async def handle_text(event):
        on_text(event.payload)
    
    @mc.on(EventType.ADVERT)
    async def handle_advert(event):
        on_advert(event.payload)
    
    @mc.on(EventType.STATS)
    async def handle_stats(event):
        on_stats(event.payload)
    
    # Start forwarder thread
    threading.Thread(target=forward_worker, daemon=True).start()
    
    # Start stats poller as async task
    asyncio.create_task(stats_poller_async())
    
    logger.info("Bridge started. Listening for events...")
    
    # Keep the connection alive
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        await mc.disconnect()

def main():
    asyncio.run(main_async())

if __name__ == '__main__':
    main()