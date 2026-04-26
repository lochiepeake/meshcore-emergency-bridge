import asyncio
from meshcore import MeshCore, EventType

async def on_message(event):
    """Prints any message the bridge receives."""
    data = event.payload
    sender = data.get('pubkey_prefix', data.get('pubkey', 'Unknown'))
    message_text = data.get('text', data.get('msg', 'No text'))
    print(f"\n📨 MESSAGE RECEIVED from {sender}: {message_text}")

async def test_send_and_receive():
    # 1. Connect to the Heltec Companion
    print(f"Connecting to {SERIAL_PORT}...")
    meshcore = await MeshCore.create_serial(SERIAL_PORT, 115200, debug=False)
    print("✅ Connected.")

    # 2. Set up the subscriber to listen for messages
    meshcore.subscribe(EventType.CONTACT_MSG_RECV, on_message)
    print("Listening for incoming messages...")
    await meshcore.start_auto_message_fetching()

    # 3. Send a test message. You'll need a contact's key.
    #    A simple approach is to send a broadcast message.
    #    The exact command may vary; check MeshCore docs for 'send_broadcast'.
    print("Sending a test broadcast message...")
    try:
        # This sends a message to any node listening on the default channel
        await meshcore.commands.send_chan_msg(0, "Bridge Test: Hello Mesh!")
        print("Message sent.")
    except AttributeError:
        print("Note: 'send_broadcast' not found. You may need to send a direct message to a known contact.")
    except Exception as e:
        print(f"Could not send test broadcast: {e}")

    # 4. Keep the script running to listen for replies for 60 seconds
    print("Listening for 60 seconds. Send a message from another node to this device.")
    await asyncio.sleep(60) # Wait for any incoming messages

    await meshcore.stop_auto_message_fetching()
    await meshcore.disconnect()
    print("Test complete.")

asyncio.run(test_send_and_receive())