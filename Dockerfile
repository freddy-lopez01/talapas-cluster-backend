# Use a full Debian-based Python image (not slim)
FROM python:3.12

LABEL maintainer="Freddy Lopez"
LABEL version="1.0"

WORKDIR /app

COPY . /app/
COPY entrypoint.sh /entrypoint.sh

RUN apt-get update && apt-get install -y \
    sqlite3 \
    curl \
    build-essential \
    libslurm-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install -r requirements.txt

ENV PATH="/usr/local/bin/slurm:$PATH"

ENV FLASK_APP=/app/cpu_receiver.py \
    FLASK_ENV=production \
    DB_PATH=/var/log/cpu_ingest/cpu_data.db \
    LOG_DIR=/var/log/cpu_ingest

RUN mkdir -p /var/log/cpu_ingest

EXPOSE 5000
CMD ["/entrypoint.sh"]

