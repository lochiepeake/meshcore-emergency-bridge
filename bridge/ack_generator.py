import logging
import time

logger = logging.getLogger(__name__)

async def send_ack_async(meshcore, dest_pubkey, msg_id):
    """Send an ACK message back through the mesh to the source node."""
    ack_text = f"ACK|MSGID:{msg_id}|TS:{int(time.time())}|GW:bridge"
    
    # Method 1: Try send_msg (direct message - preferred)
    if hasattr(meshcore.commands, 'send_msg'):
        try:
            await meshcore.commands.send_msg(dest_pubkey, ack_text)
            logger.info(f"ACK sent via send_msg to {dest_pubkey} for msg {msg_id}")
            return True
        except Exception as e:
            logger.warning(f"send_msg failed: {e}")
    
    # Method 2: Try send_chan_msg WITHOUT destination parameter
    if hasattr(meshcore.commands, 'send_chan_msg'):
        try:
            # Note: NO destination parameter here
            await meshcore.commands.send_chan_msg(0, ack_text)
            logger.info(f"ACK sent via send_chan_msg to channel 0 for msg {msg_id}")
            return True
        except Exception as e:
            logger.warning(f"send_chan_msg failed: {e}")
    
    # Method 3: Try send_text (if available)
    if hasattr(meshcore.commands, 'send_text'):
        try:
            await meshcore.commands.send_text(dest_pubkey, ack_text)
            logger.info(f"ACK sent via send_text to {dest_pubkey} for msg {msg_id}")
            return True
        except Exception as e:
            logger.warning(f"send_text failed: {e}")
    
    # Method 4: Try send_message (alternative naming)
    if hasattr(meshcore.commands, 'send_message'):
        try:
            await meshcore.commands.send_message(dest_pubkey, ack_text)
            logger.info(f"ACK sent via send_message to {dest_pubkey} for msg {msg_id}")
            return True
        except Exception as e:
            logger.warning(f"send_message failed: {e}")
    
    logger.error(f"All ACK sending methods failed for msg {msg_id}")
    return False