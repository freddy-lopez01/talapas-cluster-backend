#!/packages/miniconda3/20240410/envs/python312/bin/python3

'''
This script was created to create/update the file node_data.json with the latest status of total cores in use per node running 
on the cluster. This information is obtained via the login node through one simple squeue command that is ran every 5 minutes. 
This script is currently lives locally on flopez2 machine but will be placed on toolbox where a the live json will be created 
and updated which will be copied to a external S3 bucket so that the web app can then retrieve the data without firewall issues.
'''

from collections import defaultdict
import subprocess
import sqlite3
import time
import os
import re

DB_PATH = os.environ.get("DB_PATH", "/var/log/cpu_ingest/cpu_data.db")

def get_node_alloc() -> dict[str, int]:
    """Get CPUAlloc per node using scontrol."""
    result = subprocess.run(
        ["scontrol", "show", "node", "-o"],
        capture_output=True, text=True, check=True
    )
    node_data = {}
    for line in result.stdout.strip().split("\n"):
        name_match = re.search(r'NodeName=(\S+)', line)
        alloc_match = re.search(r'CPUAlloc=(\d+)', line)
        if name_match and alloc_match:
            name = name_match.group(1)
            if name == "NODELIST":
                continue
            node_data[name] = int(alloc_match.group(1))
    return node_data

def update_cpu_db(node_data: dict[str, int]):
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL;")
    cursor = conn.cursor()
    for node, used_cores in node_data.items():
        if node[0] == "n":
            nodename = node + ".talapas.uoregon.edu"
            cursor.execute("""
                INSERT INTO cpu_data (hostname, cpu_count, cpu_usage)
                VALUES (?, ?, ?)
                ON CONFLICT(hostname) DO UPDATE SET
                    cpu_usage = excluded.cpu_usage
            """, (nodename, 0, used_cores))
        else: 
            continue
    conn.commit()
    conn.close()
    print(f"[{time.strftime('%H:%M:%S')}] Updated {len(node_data)} nodes", flush=True)

def main():
    print(f"[{time.strftime('%H:%M:%S')}] Refreshing node data...", flush=True)
    node_data = get_node_alloc()
    update_cpu_db(node_data)

if __name__ == "__main__":
    while True:
        main()
        time.sleep(30)
