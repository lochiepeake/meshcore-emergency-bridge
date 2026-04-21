import logging
import time

logger = logging.getLogger(__name__)

def send_ack(mc, dest_pubkey, msg_id):
    """Send an ACK message back through the mesh to the source node."""
    ack_text = f"ACK|MSGID:{msg_id}|TS:{int(time.time())}|GW:bridge"
    try:
        # Use send_text with destination = source node's public key
        mc.send_text(ack_text, dest=dest_pubkey)
        logger.info("ACK sent to %s for msg %d", dest_pubkey, msg_id)
        return True
    except Exception as e:
        logger.error("Failed to send ACK: %s", e)
        return False