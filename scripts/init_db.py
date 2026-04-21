#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bridge.database import init_db
from bridge.config import DB_PATH

if __name__ == '__main__':
    init_db(DB_PATH)
    print(f"Database created at {DB_PATH}")