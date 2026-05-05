import logging
import time

logger = logging.getLogger(__name__)

async def send_ack_async(meshcore, dest_pubkey, msg_id):
    """Send an ACK message back through the mesh to the source node."""
    ack_text = f"ACK|MSGID:{msg_id}|TS:{int(time.time())}|GW:bridge"
    
    # Try method 1: send_msg (direct message)
    if hasattr(meshcore.commands, 'send_msg'):
        try:
            await meshcore.commands.send_msg(dest_pubkey, ack_text)
            logger.info(f"ACK sent via send_msg to {dest_pubkey} for msg {msg_id}")
            return True
        except Exception as e:
            logger.warning(f"send_msg failed: {e}")
    
    # Try method 2: send_chan_msg without destination
    if hasattr(meshcore.commands, 'send_chan_msg'):
        try:
            await meshcore.commands.send_chan_msg(0, ack_text)
            logger.info(f"ACK sent via send_chan_msg to channel 0 for msg {msg_id}")
            return True
        except Exception as e:
            logger.warning(f"send_chan_msg failed: {e}")
    
    # Try method 3: send_text (if available)
    if hasattr(meshcore.commands, 'send_text'):
        try:
            await meshcore.commands.send_text(dest_pubkey, ack_text)
            logger.info(f"ACK sent via send_text to {dest_pubkey} for msg {msg_id}")
            return True
        except Exception as e:
            logger.warning(f"send_text failed: {e}")
    
    logger.error(f"All ACK sending methods failed for msg {msg_id}")
    return False