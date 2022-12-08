#!/usr/bin/env python3
import redis
import json
from pprint import pprint

r = redis.Redis(host='localhost', port=6379, db=0)
print("Starting the client worker:")
while True:
    # This is from redis
    data_bytes = r.blpop("nglue")
    # Now our json data
    data = json.loads(data_bytes[1].decode("utf-8"))
    print("--"*20)
    pprint(data)
    print("--"*20)
