## nglue-api

This is API server for nglue, this will receive the details from the command line rust client and pass on the information the server via `client.py`.

### License: MIT

## How to build the container?

First, create a proper `config.py` with token & correct URL for Argus.

```
podman build -t kdas/nglue-api .
```

The container is based on `python:3.11-bullseye`.

## How to run the container?

```
podman run --rm -it -p 8000:8000 kdas/nglue-api:latest
```

Here we are mapping the port `8000` of the container to the host. Inside of the container we have a redis server for queue.
The web application is writing logs in `/var/log/nglue.log` file.

