#!/bin/bash
set -e

echo "Updating system packages..."
sudo apt update
sudo apt install -y python3 python3-pip git sqlite3

echo "Installing Python libraries..."
pip3 install pyserial flask requests twilio paho-mqtt

echo "Installing meshcore_py from GitHub..."
if [ -d "meshcore_py" ]; then
    rm -rf meshcore_py
fi
git clone https://github.com/meshcore/meshcore_py.git
cd meshcore_py
python3 setup.py install
cd ..

echo "All dependencies installed."