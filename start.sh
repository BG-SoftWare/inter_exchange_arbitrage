#!/bin/bash
FILE=./bot.lock
if test -f "$FILE"; then
    echo "I cant run second instance of bot"
    exit 0
fi
export PYTHONPATH=$PYTHONPATH:$(pwd)
python3 main.py
#read -p "press any key to close..."
