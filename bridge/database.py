import sqlite3
import time
import json
import logging

logger = logging.getLogger(__name__)

def init_db(db_path):
    """Create all tables if they don't exist."""
    with sqlite3.connect(db_path) as conn:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS nodes (
            pubkey TEXT PRIMARY KEY,
            last_seen INTEGER,
            last_lat REAL,
            last_lon REAL,
            last_alt REAL,
            last_battery_mv INTEGER,
            last_rssi INTEGER,
            last_snr INTEGER,
            node_name TEXT,
            device_type TEXT
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS breadcrumbs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pubkey TEXT,
            timestamp INTEGER,
            latitude REAL,
            longitude REAL,
            altitude REAL,
            battery_mv INTEGER,
            rssi INTEGER,
            snr INTEGER,
            path_json TEXT
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS emergencies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pubkey TEXT,
            timestamp INTEGER,
            raw_message TEXT,
            parsed_lat REAL,
            parsed_lon REAL,
            parsed_alt REAL,
            battery_mv INTEGER,
            forwarded_status TEXT,
            ack_sent INTEGER DEFAULT 0,
            retries INTEGER DEFAULT 0,
            w3w_location TEXT
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS telemetry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pubkey TEXT,
            timestamp INTEGER,
            battery_mv INTEGER,
            uptime_secs INTEGER,
            queue_len INTEGER,
            noise_floor REAL,
            last_rssi INTEGER,
            last_snr INTEGER,
            tx_air_secs REAL,
            rx_air_secs REAL,
            flood_tx INTEGER,
            direct_tx INTEGER,
            flood_rx INTEGER,
            direct_rx INTEGER
        )''')
        conn.commit()
    logger.info("Database initialised at %s", db_path)

def store_node(db_path, pubkey, name=None, lat=None, lon=None, alt=None,
               bat=None, rssi=None, snr=None):
    with sqlite3.connect(db_path) as conn:
        cur = conn.cursor()
        cur.execute("SELECT pubkey FROM nodes WHERE pubkey=?", (pubkey,))
        if cur.fetchone():
            cur.execute('''UPDATE nodes SET last_seen=?, last_lat=?, last_lon=?, last_alt=?,
                        last_battery_mv=?, last_rssi=?, last_snr=?, node_name=?
                        WHERE pubkey=?''',
                        (int(time.time()), lat, lon, alt, bat, rssi, snr, name, pubkey))
        else:
            cur.execute('''INSERT INTO nodes (pubkey, last_seen, last_lat, last_lon, last_alt,
                                            last_battery_mv, last_rssi, last_snr, node_name)
                        VALUES (?,?,?,?,?,?,?,?,?)''',
                        (pubkey, int(time.time()), lat, lon, alt, bat, rssi, snr, name))
        conn.commit()
    

def store_breadcrumb(db_path, pubkey, lat, lon, alt=None, bat=None,
                     rssi=None, snr=None, path=None):
    with sqlite3.connect(db_path) as conn:
    
        cur = conn.cursor()
        cur.execute('''INSERT INTO breadcrumbs
                    (pubkey, timestamp, latitude, longitude, altitude,
                        battery_mv, rssi, snr, path_json)
                    VALUES (?,?,?,?,?,?,?,?,?)''',
                    (pubkey, int(time.time()), lat, lon, alt, bat, rssi, snr,
                    json.dumps(path) if path else None))
        conn.commit()
    

def store_emergency(db_path, pubkey, raw_msg, lat, lon, alt=None, bat=None, w3w_location=None):
    with sqlite3.connect(db_path) as conn:
        cur = conn.cursor()
        cur.execute('''INSERT INTO emergencies
                       (pubkey, timestamp, raw_message, parsed_lat, parsed_lon,
                        parsed_alt, battery_mv, forwarded_status, w3w_location)
                       VALUES (?,?,?,?,?,?,?,?,?)''',
                    (pubkey, int(time.time()), raw_msg, lat, lon, alt, bat, 'pending', w3w_location))
        conn.commit()
        return cur.lastrowid

def update_emergency_status(db_path, msg_id, status):
    with sqlite3.connect(db_path) as conn:
        cur = conn.cursor()
        cur.execute("UPDATE emergencies SET forwarded_status=? WHERE id=?", (status, msg_id))
        conn.commit()
        conn.close()

def increment_emergency_retries(db_path, msg_id):
    with sqlite3.connect(db_path) as conn:
        cur = conn.cursor()
        cur.execute("UPDATE emergencies SET retries=retries+1 WHERE id=?", (msg_id,))
        conn.commit()
        conn.close()
        cur.execute("SELECT retries FROM emergencies WHERE id=?", (msg_id,))
        retries = cur.fetchone()[0]
        conn.close()
        return retries

def store_telemetry(db_path, pubkey, bat, uptime, queue_len, noise,
                    rssi, snr, tx_air, rx_air, flood_tx, direct_tx,
                    flood_rx, direct_rx):
    with sqlite3.connect(db_path) as conn:
        cur = conn.cursor()
        cur.execute('''INSERT INTO telemetry
                    (pubkey, timestamp, battery_mv, uptime_secs, queue_len,
                        noise_floor, last_rssi, last_snr, tx_air_secs, rx_air_secs,
                        flood_tx, direct_tx, flood_rx, direct_rx)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                    (pubkey, int(time.time()), bat, uptime, queue_len, noise,
                    rssi, snr, tx_air, rx_air, flood_tx, direct_tx, flood_rx, direct_rx))
        conn.commit()
        conn.close()