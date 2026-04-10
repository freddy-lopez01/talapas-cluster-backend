#!/packages/miniconda3/20240410/envs/python312/bin/python3
from flask import Flask, jsonify, request
import subprocess
import hashlib
import os

app = Flask(__name__)

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
        # Run squeue, count unique job IDs
        result = subprocess.run(
            "squeue -h | awk '{print $1}' | sort | uniq | wc -l",
            shell=True,
            capture_output=True,
            text=True,
            check=True
        )
        total = int(result.stdout.strip())
        return jsonify({"total_jobs": total}), 200

    except subprocess.CalledProcessError as e:
        print(f"Error querying Slurm: {e}")
        return jsonify({"status": "error", "message": "Failed to query Slurm"}), 500

@app.route('/api/total_live_users', methods=['GET'])
def total_users():
    if not verify_api_key(request):
        return jsonify({"status": "error", "message": "Unauthorized Access"}), 401
    try:
        # Full command as a single string
        cmd = """pdsh -g login "users" | awk -F: '{print $2}' | tr ' ' '\\n' | sort | uniq | wc -l"""

        result = subprocess.run(
            cmd,
            shell=True,             # because we are using pipes
            capture_output=True,    # capture stdout
            text=True,              # get output as string
            check=True              # raise exception on failure
        )

        # The result is a string with a newline, strip and convert to int
        total_users = int(result.stdout.strip())
        return jsonify({"total_users": total_users}), 200

    except subprocess.CalledProcessError as e:
        print(f"Error querying Slurm: {e}")
        return jsonify({"status": "error", "message": "Failed to query login nodes"}), 500
if __name__ == "__main__":
    # Expose on all interfaces so container can reach it
    app.run(host="0.0.0.0", port=5004)

