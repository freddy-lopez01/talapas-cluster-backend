#!/usr/bin/bash

docker run --rm -it \
  -p 5000:5000 \
  -e CPU_COUNT_API_KEY="FreddyHa\$aR3DH4T" \
  -v /var/log/cpu_ingest:/var/log/cpu_ingest \
  -v /gpfs/t2/slurm/apps/24.05.7/bin:/usr/local/bin/slurm \
  -v /gpfs/t2/slurm/apps/24.05.7/lib/slurm:/usr/local/lib/slurm \
  -v /gpfs/t2/slurm/apps/current/lib64:/usr/local/lib64/slurm \
  -v /gpfs/t2/slurm/etc:/etc/slurm:ro \
  -e PATH="/usr/local/bin/slurm:$PATH" \
  -e LD_LIBRARY_PATH="/usr/local/lib/slurm:$LD_LIBRARY_PATH" \
  --network host \
  cpu-backend
