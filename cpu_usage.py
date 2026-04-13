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
import pathlib
import time
import json
import yaml
import os
import re

node_data = {}
node_features = {}

DB_PATH = "/var/log/cpu_ingest/cpu_data.db"

def expand_nodes(node_str):
    """Expand Slurm node list like n[0037-0040,0042] into individual node names."""
    result = subprocess.run(
        ["scontrol", "show", "hostnames", node_str],
        capture_output=True, text=True
    )
    return result.stdout.strip().split("\n")

def update_cpu_db(node_data: dict[str, int]):
    """
    Update the cpu_data table with the latest cpu_usage per node.
    node_data: dict mapping node_name -> used_cores
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")  # optional if you want to store last_updated elsewhere

    for node, used_cores in node_data.items():
        nodename = node + ".talapas.uoregon.edu"
        #print(f"Updating node: {nodename} with cpu_usage: {used_cores}")

        # Insert new row or update existing
        cursor.execute("""
            INSERT INTO cpu_data (hostname, cpu_count, cpu_usage)
            VALUES (?, ?, ?)
            ON CONFLICT(hostname) DO UPDATE SET
                cpu_usage = excluded.cpu_usage
        """, (nodename, 0, used_cores))  # cpu_count=0 since we just update usage

    conn.commit()
    conn.close()


def obtain_squeue_out() -> dict[str, list[str]]:
    cmd = "squeue -o '%i %C %R' --noheader"
    jobs_dict = {}
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
        total_jobs = 0
        for line in result.stdout.strip().split("\n"):
            total_jobs += 1
            parts = line.split(" ")
            jobs_dict[parts[0]] = [parts[2], parts[1]]
    except subprocess.CalledProcessError as e:
        print("Error executing SSH command:", e.stderr)

    return jobs_dict

def filter_data(data, node_dict):
    pattern = r"^[a-zA-Z]\d{4}$"
    for k, v in data.items():
        if re.match(pattern, v[0]):
                node_dict[v[0]] += int(v[1])
        else:
            if "[" in v[0]:
                node_list = expand_nodes(v[0])
                for node in node_list:
                    if node in node_dict:
                        node_dict[node] += int(v[1])
    return node_dict


def extract_compute_nodes():
    cmd = f"sinfo -N | awk '{{print $1}}'"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)

    nodes_split = result.stdout.split("\n")
    node_dict = {}
    for node in nodes_split:
        if node != "":
            nodename = node.split(".")[0]
            node_dict[nodename] = 0

    #print(node_dict)
    return node_dict

def main():
    res = obtain_squeue_out()
    #print(res)
    nodes = extract_compute_nodes()
    #print(nodes)
    node_data = filter_data(res, nodes)
    update_cpu_db(node_data)



if __name__ == "__main__":
    while True:
        main()
        time.sleep(30)
