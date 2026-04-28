# debug_routes.py
from dashboard import app
from flask import Flask, request, jsonify
import sqlite3
import sys
import os

# Ensure we're using the correct DB path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bridge.config import DB_PATH

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# Re-define the update route within the test script to mirror the one in dashboard.py
@app.route('/api/emergencies/<int:emergency_id>/status', methods=['POST'])
def update_emergency_status(emergency_id):
    print(f"--- TEST: /api/emergencies/{emergency_id}/status route was called ---")
    data = request.get_json()
    if not data or 'status' not in data:
        return jsonify({'error': 'Missing status field'}), 400
    new_status = data['status']
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("UPDATE emergencies SET forwarded_status=? WHERE id=?", (new_status, emergency_id))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'id': emergency_id, 'status': new_status})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("\n--- Registered Routes (debug view) ---")
    for rule in app.url_map.iter_rules():
        print(f"Endpoint: '{rule.endpoint}', Methods: {rule.methods}, URL: '{rule}'")
    print("--- End of Route List ---\n")

    # Test the route directly
    print("Proceeding to test the route manually...")
    with app.test_client() as client:
        test_emergency_id = 1

        # First, check if this ID exists to avoid a potential "doesn't exist" error later
        conn_for_check = get_db()
        cur_check = conn_for_check.cursor()
        cur_check.execute("SELECT id FROM emergencies WHERE id = ?", (test_emergency_id,))
        exists = cur_check.fetchone() is not None
        conn_for_check.close()

        if not exists:
            print(f"WARNING: Emergency with ID {test_emergency_id} does not exist. Status update will fail, but the route itself should still be found (returns 404 only if ID is missing).")

        response = client.post(f'/api/emergencies/{test_emergency_id}/status',
                               json={'status': 'acknowledged'})
        print(f"Test request to '/api/emergencies/{test_emergency_id}/status'")
        print(f"Response status code: {response.status_code}")
        print(f"Response data: {response.get_data(as_text=True)}")
    print("\n--- Diagnostic complete. ---")