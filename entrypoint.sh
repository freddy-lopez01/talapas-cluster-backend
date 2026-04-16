#!/bin/bash
set -e


# Start the Flask app in the foreground (keeps container alive)
python /app/cpu_receiver.py
