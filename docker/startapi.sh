#!/bin/bash
set +x
/usr/bin/redis-server /etc/redis/redis.conf &
source ./venv/bin/activate
uvicorn main:app --host 0.0.0.0 --reload > /var/log/nglue.log 2>&1 &
python3 client.py

