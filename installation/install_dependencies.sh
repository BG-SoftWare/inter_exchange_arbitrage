#!/usr/bin/env bash
apt update
apt install -y python3-pip python3-venv screen
python3 -m pip install -r requirements.txt
