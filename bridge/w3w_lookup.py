# w3w_lookup.py
import logging
import what3words
import os
from dotenv import load_dotenv




logger = logging.getLogger(__name__)

#get w3w API ket from .env file
env_path = Path('/home/pibridge/meshcore-emergency-bridge/.env')
load_dotenv(dotenv_path=env_path)
W3W_API_KEY = os.getenv('W3W_API_KEY')

if not W3W_API_KEY:
    logger.error("W3W_API_KEY not found in environment. Please check your .env file.")
else:
    # initialize  what3words API client 
    w3w = what3words.geocoder.Geocoder(W3W_API_KEY)

def convert_coords_to_words(lat, lon):
    """
    Convert latitude and longitude to a what3words 3-word address.
    Returns a string like 'filled.count.soap' or None if conversion fails.
    """
    if not lat or not lon:
        return None
    try:
        # The API expects a tuple of (latitude, longitude)
        result = w3w.convert_to_3wa((lat, lon))
        # The 3 word address is returned in the 'words' key
        words = result.get('words')
        if words:
            logger.info(f"what3words lookup successful: ({lat}, {lon}) -> {words}")
            return words
        else:
            logger.warning(f"what3words lookup returned no words: {result}")
            return None
    except Exception as e:
        logger.error(f"what3words API error: {e}")
        return None