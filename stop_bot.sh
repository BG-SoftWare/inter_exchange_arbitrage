#!/bin/bash
source buildname
touch .stopped_by_user
process_id=$(< bot.lock)
kill -USR1 $process_id
