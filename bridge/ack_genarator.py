import logging
logger = logging.getLogger(__name__)

async def send_ack_async(meshcore, dest_pubkey, msg_id):
    """Send an ACK message back through the mesh to the source node."""
    ack_text = f"ACK|MSGID:{msg_id}|TS:{int(time.time())}|GW:bridge"
    try:
        # ✅ Use send_msg (direct message) instead of send_chan_msg
        await meshcore.commands.send_msg(dest_pubkey, ack_text)
        logger.info(f"ACK sent to {dest_pubkey} for msg {msg_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to send ACK: {e}")
        return False