#!/packages/miniconda3/20240410/envs/python312/bin/python3
from flask import Flask, request, jsonify
from flask_cors import CORS 
from datetime import datetime
import os
import requests
import json
import sqlite3
import hashlib
import subprocess
app = Flask(__name__)
CORS(app)

CORS(app, origins=["http://localhost:3002"])

LOG_DIR = "/var/log/cpu_ingest"
LOG_FILE = os.path.join(LOG_DIR, "cpu_data.jsonl")
os.makedirs(LOG_DIR, exist_ok=True)
DB_PATH = os.path.join(LOG_DIR, "cpu_data.db")
NODES_DB_PATH = os.path.join(LOG_DIR, "nodes.db")
#os.makedirs(LOG_DIR, exist_ok=TRUE)
# Now to make the DB hehe
def init_db():
    if os.path.exists(DB_PATH) and os.path.getsize(DB_PATH) > 0:
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.execute("SELECT name FROM sqlite_master LIMIT 1;")
            conn.close()
            return
        except sqlite3.DatabaseError:
            os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cpu_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hostname TEXT UNIQUE NOT NULL,
            cpu_count INTEGER NOT NULL,
            cpu_usage INTEGER
        )
    ''')
    conn.commit()
    conn.close()

def get_all_nodes():
    """Run sinfo to get a sorted, unique list of all nodes."""
    result = subprocess.run(
        ['sinfo', '-N', '-h', '-o', '%N'],
        capture_output=True,
        text=True,
        check=True
    )
    nodes = result.stdout.strip().split("\n")
    return sorted(set(nodes))  # remove duplicates just in case

def populate_nodes():
    """Add nodes to DB if they don't exist yet."""
    nodes = get_all_nodes()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    for node in nodes:
        name = node + ".talapas.uoregon.edu"
        print(name)
        cursor.execute('''
            INSERT INTO cpu_data (hostname, cpu_count)
            VALUES (?, 0)
            ON CONFLICT(hostname) DO NOTHING
        ''', (name,))
    
    conn.commit()
    conn.close()
    print(f"Added/verified {len(nodes)} nodes in the database.")


# Create the token authentication so no one does anything nasty and it be my fault.....

API_KEY_PLAIN = os.environ['CPU_COUNT_API_KEY']
API_KEY_HASH = hashlib.sha256(API_KEY_PLAIN.encode()).hexdigest()

def verify_api_key(request):
    """Verify SHA-256 API key from the header."""
    key = request.headers.get("X-API-Key")
    if not key:
        return False 
    hashed = hashlib.sha256(key.encode()).hexdigest()
    return hashed == API_KEY_HASH

@app.route('/api/total_jobs', methods=['GET'])
def total_jobs():
    if not verify_api_key(request):
        return jsonify({"status": "error", "message": "Unauthorized Access"}), 401

    try:
        # Call the remote host API
        remote_api_key = os.environ.get("CPU_COUNT_API_KEY")
        remote_url = "http://toolbox.talapas.uoregon.edu:5004/api/total_jobs"
        headers = {"X-API-KEY": remote_api_key}

        resp = requests.get(remote_url, headers=headers, timeout=5)
        resp.raise_for_status()  # Raise exception if HTTP error

        data = resp.json()
        return jsonify({"total_jobs": data.get("total_jobs", 0)}), 200

    except requests.RequestException as e:
        print(f"Error querying remote Slurm API: {e}")
        return jsonify({"status": "error", "message": "Failed to query remote Slurm API"}), 500

@app.route('/api/total_users', methods=['GET'])
def total_users():
    if not verify_api_key(request):
        return jsonify({"status": "error", "message": "Unauthorized Access"}), 401

    try:
        remote_api_key = os.environ.get("CPU_COUNT_API_KEY")
        remote_url = "http://toolbox.talapas.uoregon.edu:5004/api/total_live_users"
        headers = {"X-API-KEY": remote_api_key}

        resp = requests.get(remote_url, headers=headers, timeout=5)
        resp.raise_for_status()

        data = resp.json()
        return jsonify({"total_users": data.get("total_users", 0)}), 200

    except requests.RequestException as e:
        print(f"Error querying remote login node API: {e}")
        return jsonify({"status": "error", "message": "Failed to query remote login node API"}), 500

@app.route("/api/node_usage")
def get_node_usage():
    if not verify_api_key(request):
        return jsonify({"status": "error", "message": "Unauthorized Access To Toolbox"}), 401

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT hostname, cpu_usage FROM cpu_data")
        rows = cursor.fetchall()
        conn.close()

        # convert to dict
        usage_dict = {row[0]: row[1] for row in rows}
        return jsonify(usage_dict)

    except Exception as e:
        print(f"Error querying SQLite: {e}")
        return jsonify({"status": "error", "message": "Database error"}), 500

@app.route('/api/cpu_count/<nodename>', methods=['GET'])
def get_cpu_count(nodename):
    if not verify_api_key(request):
        return jsonify({"status": "error", "message": "Unauthorized Access To Toolbox"}), 401

    try:
        conn = sqlite3.connect(NODES_DB_PATH)
        c = conn.cursor()
        c.execute("SELECT CPUAlloc FROM nodes WHERE hostname = ?", (nodename.split(".")[0],))
        row = c.fetchone()
        conn.close()
        print(row)

        if row is None:
            return jsonify({"status": "error", "message": "Node not found"}), 404

        cpu_count = row[0]
        return jsonify({"hostname": nodename, "cpu_count": cpu_count}), 200

    except Exception as e:
        print(f"Error querying SQLite: {e}")
        return jsonify({"status": "error", "message": "Database error"}), 500


@app.route('/api/cpu_update', methods=['POST'])
def cpu_update():

    if not verify_api_key(request):
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    data = request.get_json(force=True)

    print(f"DATA FROM A NODE: {data}")

    hostname = data.get("hostname")
    cpu_count = data.get("cpu_count")

    if not hostname or not cpu_count:
        return jsonify({"status": "error", "message": "Missing hostname or cpu_count"}), 400

    entry = {
        "hostname": hostname,
        "cpu_count": cpu_count,
    }

    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")
    # This is where now hopefully the database will be populated 
     
    try: 
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''
                INSERT INTO cpu_data (hostname, cpu_count)
                VALUES (?, ?)
                ON CONFLICT(hostname) DO UPDATE SET
                    cpu_count=excluded.cpu_count
            ''', (hostname, cpu_count))
        conn.commit()
        conn.close()
    except Exception as e: 
        print(f"Error inserting into SQLite: {e}")

    print(f"[Received from {hostname}: {cpu_count} cores")

    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    init_db()
    #populate_nodes()
    app.run(host="0.0.0.0", port=5000)
