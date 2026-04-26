import asyncio
from meshcore import MeshCore

async def test_connection():
    print(f"Attempting connection on {SERIAL_PORT}...")
    try:
        # The meshcore = await MeshCore.create_serial() call is the first major check
        meshcore = await MeshCore.create_serial("/dev/ttyUSB0", 115200, debug=False) 
        print("✅ Successfully connected to MeshCore device!")
        await meshcore.disconnect()
        print("Connection closed.")
    except Exception as e:
        print(f"❌ Connection failed: {e}")

asyncio.run(test_connection())