#!/packages/miniconda3/20240410/envs/python312/bin/python3
import subprocess
import json
import sqlite3
import time

def save_nodes_to_sqlite(nodes, db_path="nodes.db"):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    all_columns = set()
    for node in nodes.values():
        all_columns.update(node.keys())

    all_columns.add("NodeName")

    columns_sql = ", ".join(f'"{col}" TEXT' for col in all_columns)

    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS nodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            {columns_sql}
        );
    """)
    cursor.execute("DELETE FROM nodes;")

    for nodename, data in nodes.items():
        data["NodeName"] = nodename

        cols = ", ".join(f'"{col}"' for col in all_columns)
        placeholders = ", ".join("?" for _ in all_columns)
        values = [data.get(col) for col in all_columns]

        cursor.execute(
            f"INSERT INTO nodes ({cols}) VALUES ({placeholders});",
            values
        )

    conn.commit()
    conn.close()

    print(f"Saved {len(nodes)} nodes to {db_path}")

def get_node_facts() -> dict[str, str]:

    cluster_nodes = {}

    cmd = ["scontrol", "show", "nodes"]

    res = subprocess.run(cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True
    )
    
    output = res.stdout
    raw_blocks = output.split("\n\n")
    nodes = {}

    for block in raw_blocks:
        cleaned = " ".join(block.split())

        tokens = cleaned.split()

        node_data = {}
        node_name = None

        for token in tokens:
            if "=" in token:
                key, value = token.split("=", 1)
                if key == "NodeName":
                    node_name = value
                else:
                    node_data[key] = value

        if node_name:
            nodes[node_name] = node_data

    return nodes


def main():
    while True:
        nodes = get_node_facts()
        save_nodes_to_sqlite(nodes, "nodes.db")
        print("Updated database.")
        time.sleep(1800) # 30 minutes




if __name__ == "__main__":
    main()

