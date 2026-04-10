#!/packages/miniconda3/20240410/envs/python312/bin/python3
"""
Test script for the extract_compute_nodes function in cpu_usage.py
"""

from cpu_usage import extract_compute_nodes, obtain_squeue_out

def main():
    
    nodes = extract_compute_nodes()
    print("Compute nodes populated!!")
    jobs = obtain_squeue_out()
    print(jobs)

if __name__ == "__main__":
    main()

