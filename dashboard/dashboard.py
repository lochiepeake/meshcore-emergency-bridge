from flask import Flask, render_template, jsonify, request   
import sqlite3
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bridge.config import DB_PATH

app = Flask(__name__)

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/nodes')
def api_nodes():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT pubkey, last_lat, last_lon, node_name FROM nodes WHERE last_lat IS NOT NULL")
    rows = cur.fetchall()
    nodes = [{'id': r['pubkey'], 'name': r['node_name'] or r['pubkey'][:8],
              'lat': r['last_lat'], 'lon': r['last_lon']} for r in rows]
    conn.close()
    return jsonify(nodes)

@app.route('/api/breadcrumbs/<pubkey>')
def api_breadcrumbs(pubkey):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT timestamp, latitude, longitude FROM breadcrumbs WHERE pubkey=? ORDER BY timestamp LIMIT 1000", (pubkey,))
    rows = cur.fetchall()
    crumbs = [{'ts': r['timestamp'], 'lat': r['latitude'], 'lon': r['longitude']} for r in rows]
    conn.close()
    return jsonify(crumbs)

@app.route('/api/emergencies')
def api_emergencies():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, pubkey, timestamp, parsed_lat, parsed_lon, forwarded_status, w3w_location FROM emergencies ORDER BY timestamp ASC")
    rows = cur.fetchall()
    emergencies = []
    for r in rows:
        emergencies.append({
            'id': r['id'],
            'src': r['pubkey'][:8],
            'full_src': r['pubkey'],
            'ts': r['timestamp'],
            'lat': r['parsed_lat'],
            'lon': r['parsed_lon'],
            'status': r['forwarded_status'],
            'w3w': r['w3w_location'] 
        })
    conn.close()
    return jsonify(emergencies)

@app.route('/api/emergencies/<int:emergency_id>/status', methods=['POST'])
def update_emergency_status(emergency_id):
    data = request.get_json()
    new_status = data.get('status')
    if not new_status:
        return jsonify({'error': 'Missing status'}), 400
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE emergencies SET forwarded_status=? WHERE id=?", (new_status, emergency_id))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'id': emergency_id, 'status': new_status})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=6541, debug=False)