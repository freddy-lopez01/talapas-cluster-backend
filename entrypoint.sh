#!/bin/bash
set -e

# Start cpu_usage.py in the background
python /app/cpu_usage.py &
python /app/scontrol_scaper.py &


# Start the Flask app in the foreground (keeps container alive)
python /app/cpu_receiver.py
