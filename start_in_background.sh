#!/bin/bash
source buildname
FILE=./bot.lock
if test -f "$FILE"; then
    echo "I cant run second instance of bot"
    exit 0
fi
rm .stopped_by_user
screen -dmS $BUILDNAME ./start.sh
