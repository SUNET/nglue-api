#!/bin/bash
set +x
python3 -m venv venv
source ./venv/bin/activate
python3 -m pip install wheel
python3 -m pip install --require-hashes -r requirements.txt

