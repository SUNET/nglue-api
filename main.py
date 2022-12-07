from pprint import pprint
from fastapi import FastAPI, Request
import redis

app = FastAPI()
r = redis.Redis(host='localhost', port=6379, db=0)

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.post("/")
async def listen(request: Request):
    body = await request.body()
    r.rpush("nglue", body)
    return True
