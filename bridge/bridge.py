#!/usr/bin/env python3

import asyncio
import threading
import time
import logging
import sys
import os
from meshcore import MeshCore, EventType
from serial import SerialException
from w3w_lookup import convert_coords_to_words

# Add parent directory to path if needed
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import SERIAL_PORT, DB_PATH, STATS_INTERVAL, LOG_LEVEL, MAX_RETRIES, RETRY_DELAYS
from database import (init_db, store_node, store_breadcrumb, store_emergency,
                      update_emergency_status, increment_emergency_retries, store_telemetry)
from emergency_classifier import is_emergency, parse_sos
from forwarder import forward_emergency
from utils import setup_logging
from ack_generator import send_ack_async

setup_logging(LOG_LEVEL)
logger = logging.getLogger(__name__)

mc = None
forward_queue = []

def on_text(msg):
    """Handle incoming text messages."""
    # Access dictionary keys CORRECTLY as per official docs
    sender = msg.get('pubkey_prefix', 'unknown')
    message_text = msg.get('text', '')
    logger.info(f"TXT from {sender}: {message_text}")

    if is_emergency(message_text):                     
        data = parse_sos(message_text)
        # --- Add this new code block for what3words conversion ---
        w3w_location = None
        if data['lat'] and data['lon'] and data['lat'] != 0 and data['lon'] != 0:
            w3w_location = convert_coords_to_words(data['lat'], data['lon'])
        # ---------------------------------------------------------
        msg_id = store_emergency(DB_PATH, msg.src, msg.text,
                                 data['lat'], data['lon'], data['alt'], data['bat'],
                                 w3w_location)
        forward_queue.append((msg_id, msg.src, data['lat'], data['lon'], data['bat'], 0))
        logger.info(f"Emergency stored ID={msg_id}, queued")

    elif message_text.startswith('LOC|'):
        data = parse_sos(message_text)
        rssi = msg.get('rssi', None)
        snr = msg.get('snr', None)
        store_breadcrumb(DB_PATH, sender, data['lat'], data['lon'],
                         data['alt'], data['bat'], rssi, snr)
        store_node(DB_PATH, sender, lat=data['lat'], lon=data['lon'],
                   alt=data['alt'], bat=data['bat'], rssi=rssi, snr=snr)
        logger.info(f"Location stored for {sender}")

def on_advert(ad):
    """Handle node adverts."""
    # Access ADVERT payload dictionary correctly
    # The payload for ADVERT is a dictionary with keys like 'public_key', 'name', etc.
    # Adjust if needed based on your specific library version
    logger.info(f"Advert from {ad.get('public_key', 'unknown')}: name={ad.get('name', 'unknown')}")
    # Your existing on_advert logic
    # ...

def on_stats(stats):
    """Handle incoming stats."""
    logger.info(f"Stats received: battery={stats.get('battery_mv')}mV")
    # Your existing on_stats logic
    # ...

async def handle_text(event):
    on_text(event.payload)

async def handle_advert(event):
    on_advert(event.payload)

async def handle_stats(event):
    on_stats(event.payload)

async def send_ack_async(meshcore, dest_pubkey, msg_id):
    """Send an ACK message back through the mesh to the source node."""
    ack_text = f"ACK|MSGID:{msg_id}|TS:{int(time.time())}|GW:bridge"
    try:
        await meshcore.commands.send_chan_msg(0, ack_text, destination=dest_pubkey)
        logger.info(f"ACK sent to {dest_pubkey} for msg {msg_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to send ACK: {e}")
        return False

def forward_worker(loop, meshcore_ref):
    while True:
        if forward_queue:
            item = forward_queue.pop(0)
            msg_id, pubkey, lat, lon, bat, retries = item
            success = forward_emergency(pubkey, lat, lon, bat)
            if success:
                update_emergency_status(DB_PATH, msg_id, 'success')
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

async def stats_poller_async(meshcore):
    while True:
        await asyncio.sleep(STATS_INTERVAL)
        logger.info("Stats polling is temporarily disabled")

async def run_bridge():
    global mc
    init_db(DB_PATH)

    while True:
        try:
            mc = await MeshCore.create_serial(SERIAL_PORT, 115200, debug=True)
            logger.info(f"Connected to MeshCore on {SERIAL_PORT}")

            # CRITICAL: Start automatic message fetching
            await mc.start_auto_message_fetching()
            logger.info("Auto message fetching enabled")

        except (SerialException, Exception) as e:
            logger.error(f"Cannot connect to serial port {SERIAL_PORT}: {e}. Retrying in 5s...")
            await asyncio.sleep(5)
            continue

        mc.subscribe(EventType.CONTACT_MSG_RECV, handle_text)
        mc.subscribe(EventType.ADVERTISEMENT, handle_advert)
        mc.subscribe(EventType.TELEMETRY_RESPONSE, handle_stats)

        loop = asyncio.get_running_loop()
        threading.Thread(target=forward_worker, args=(loop, mc), daemon=True).start()
        asyncio.create_task(stats_poller_async(mc))

        logger.info("Bridge started. Waiting for events...")

        try:
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