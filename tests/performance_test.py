# tests/test_performance.py
import time
import sqlite3
import sys
import os
import threading
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bridge.database import store_emergency, DB_PATH

def test_concurrent_writes(n_threads=10, n_messages_per_thread=100):
    """Test database can handle concurrent writes"""
    def worker(thread_id):
        for i in range(n_messages_per_thread):
            msg = f'SOS|ID:{thread_id}_{i}|LAT:51.5|LON:-0.1'
            store_emergency(DB_PATH, f'pubkey_{thread_id}', msg, 51.5, -0.1, 0, 3900)
    
    threads = []
    start = time.time()
    for i in range(n_threads):
        t = threading.Thread(target=worker, args=(i,))
        threads.append(t)
        t.start()
    for t in threads:
        t.join()
    duration = time.time() - start
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM emergencies")
    count = cur.fetchone()[0]
    conn.close()
    
    expected = n_threads * n_messages_per_thread
    print(f"Stored {count}/{expected} messages in {duration:.2f}s")
    return count == expected

if __name__ == '__main__':
    test_concurrent_writes()