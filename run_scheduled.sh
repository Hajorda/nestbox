#!/bin/bash
# Called by launchd twice a day. Random 0-10 min delay so requests don't hit at the exact same second every day.
cd "$(dirname "$0")" || exit 1
sleep $((RANDOM % 600))
FF_SOURCE=launchd /usr/bin/env python3 scraper.py --notify >> scheduled.log 2>&1
tail -n 2000 scheduled.log > scheduled.log.tmp && mv scheduled.log.tmp scheduled.log
