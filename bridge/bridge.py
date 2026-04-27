#!/usr/bin/env python3

import asyncio
import threading
import time
import logging
import sys
import os
from meshcore import MeshCore, EventType
from serial import SerialException

# Add parent directory to path if needed
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import SERIAL_PORT, DB_PATH, STATS_INTERVAL, LOG_LEVEL, MAX_RETRIES, RETRY_DELAYS
from database import (init_db, store_node, store_breadcrumb, store_emergency,
                      update_emergency_status, increment_emergency_retries, store_telemetry)
from emergency_classifier import is_emergency, parse_sos
from forwarder import forward_emergency
from utils import setup_logging

setup_logging(LOG_LEVEL)
logger = logging.getLogger(__name__)

# Global variables
mc = None
forward_queue = []  # each item: (msg_id, pubkey, lat, lon, bat, retries)

# ----------------------------------------------------------------------
# Synchronous callbacks (these do the actual work, called from async handlers)
# ----------------------------------------------------------------------
def on_text(msg):
    """Handle incoming text messages (synchronous part)."""
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
    """Handle node adverts (synchronous part)."""
    logger.info(f"Advert from {ad.src}: name={ad.name}, lat={ad.latitude/1e6}, lon={ad.longitude/1e6}")
    lat = ad.latitude / 1e6 if ad.latitude else None
    lon = ad.longitude / 1e6 if ad.longitude else None
    rssi = getattr(ad, 'rssi', None)
    snr = getattr(ad, 'snr', None)
    if lat is not None and lon is not None:
        store_breadcrumb(DB_PATH, ad.src, lat, lon, None, None, rssi, snr)
    store_node(DB_PATH, ad.src, name=ad.name, lat=lat, lon=lon, rssi=rssi, snr=snr)

def on_stats(stats):
    """Handle incoming stats (synchronous part)."""
    logger.info(f"Stats received: battery={stats.get('battery_mv')}mV")
    store_telemetry(DB_PATH, "gateway",
                    stats.get('battery_mv'), stats.get('uptime_secs'), stats.get('queue_len'),
                    stats.get('noise_floor'), stats.get('last_rssi'), stats.get('last_snr'),
                    stats.get('tx_air_secs'), stats.get('rx_air_secs'),
                    stats.get('flood_tx'), stats.get('direct_tx'),
                    stats.get('flood_rx'), stats.get('direct_rx'))

# ----------------------------------------------------------------------
# Async event handlers (these are called by meshcore library)
# ----------------------------------------------------------------------
async def handle_text(event):
    on_text(event.payload)

async def handle_advert(event):
    on_advert(event.payload)

async def handle_stats(event):
    on_stats(event.payload)

# ----------------------------------------------------------------------
# ACK sender (async version)
# ----------------------------------------------------------------------
async def send_ack_async(meshcore, dest_pubkey, msg_id):
    """Send an ACK message back through the mesh to the source node."""
    ack_text = f"ACK|MSGID:{msg_id}|TS:{int(time.time())}|GW:bridge"
    try:
        # Send to public channel 0, directed to the specific node
        await meshcore.commands.send_chan_msg(0, ack_text, destination=dest_pubkey)
        logger.info(f"ACK sent to {dest_pubkey} for msg {msg_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to send ACK: {e}")
        return False

# ----------------------------------------------------------------------
# Forward worker thread (handles queue and retries, calls async ACK)
# ----------------------------------------------------------------------
def forward_worker(loop, meshcore_ref):
    """Background thread that processes the forwarding queue with retries."""
    global mc
    while True:
        if forward_queue:
            item = forward_queue.pop(0)
            msg_id, pubkey, lat, lon, bat, retries = item
            success = forward_emergency(pubkey, lat, lon, bat)
            if success:
                update_emergency_status(DB_PATH, msg_id, 'success')
                # Schedule the async ACK sending on the event loop
                if meshcore_ref:
                    asyncio.run_coroutine_threadsafe(
                        send_ack_async(meshcore_ref, pubkey, msg_id),
                        loop
                    )
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

# ----------------------------------------------------------------------
# Stats poller (async)
# ----------------------------------------------------------------------
async def stats_poller_async(meshcore):
    """Periodically request stats from the MeshCore companion."""
    while True:
        await asyncio.sleep(STATS_INTERVAL)
        if meshcore:
            try:
                #COMMENTED OUT DONT FORGETawait meshcore.commands.get_stats()
            except Exception as e:
                logger.error(f"Stats request failed: {e}")

# ----------------------------------------------------------------------
# Main async function with auto-reconnect
# ----------------------------------------------------------------------
async def run_bridge():
    """Establish connection and run the bridge (with auto-reconnect)."""
    global mc
    init_db(DB_PATH)

    while True:
        try:
            # Connect to serial companion
            mc = await MeshCore.create_serial(SERIAL_PORT, 115200, debug=True)
            logger.info(f"Connected to MeshCore on {SERIAL_PORT}")
        except (SerialException, Exception) as e:
            logger.error(f"Cannot connect to serial port {SERIAL_PORT}: {e}. Retrying in 5s...")
            await asyncio.sleep(5)
            continue

        # Subscribe to events
        mc.subscribe(EventType.CONTACT_MSG_RECV, handle_text)
        mc.subscribe(EventType.ADVERTISMENT, handle_advert)
        mc.subscribe(EventType.TELEMETRY, handle_stats)

        # Get the current event loop for the forwarder thread
        loop = asyncio.get_running_loop()

        # Start forwarder thread (pass the loop and meshcore reference)
        threading.Thread(target=forward_worker, args=(loop, mc), daemon=True).start()

        # Start stats poller as async task
        asyncio.create_task(stats_poller_async(mc))

        logger.info("Bridge started. Waiting for events...")

        # Wait until the connection is lost (or manual interrupt)
        try:
            # Keep running – we'll detect disconnection when an exception occurs
            # in one of the background tasks. For simplicity, sleep forever.
            while True:
                await asyncio.sleep(1)
        except (ConnectionError, SerialException, Exception) as e:
            logger.error(f"Connection lost: {e}. Reconnecting...")
            try:
                await mc.disconnect()
            except:
                pass
            mc = None
            await asyncio.sleep(5)
            continue
        except KeyboardInterrupt:
            break

    if mc:
        await mc.disconnect()
        logger.info("Bridge shut down.")

async def main_async():
    await run_bridge()

def main():
    asyncio.run(main_async())

if __name__ == '__main__':
    main()