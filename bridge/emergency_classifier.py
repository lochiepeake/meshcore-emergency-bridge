import re
import time

def is_emergency(text):
    """Return True if message starts with 'SOS|' and timestamp is recent (within 5 min)."""
    if not text.startswith('SOS|'):
        return False
    # Extract timestamp if present
    match = re.search(r'TS:(\d+)', text)
    if match:
        ts = int(match.group(1))
        now = int(time.time())
        if now - ts > 300:   # older than 5 minutes
            return False
    return True

def parse_sos(text):
    """Extract fields from SOS or LOC message. Returns dict with keys: lat, lon, alt, bat, id."""
    data = {'lat': 0.0, 'lon': 0.0, 'alt': 0.0, 'bat': 0, 'id': 'unknown'}
    # Split by '|' and skip first part (e.g., "SOS" or "LOC")
    parts = text.split('|')[1:]
    for part in parts:
        if ':' in part:
            k, v = part.split(':', 1)
            k = k.upper()
            if k == 'LAT':
                try:
                    data['lat'] = float(v)
                except ValueError:
                    pass
            elif k == 'LON':
                try:
                    data['lon'] = float(v)
                except ValueError:
                    pass
            elif k == 'ALT':
                try:
                    data['alt'] = float(v)
                except ValueError:
                    pass
            elif k == 'BAT':
                try:
                    data['bat'] = int(v)
                except ValueError:
                    pass
            elif k == 'ID':
                data['id'] = v
    return data