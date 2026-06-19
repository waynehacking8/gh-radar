#!/usr/bin/env bash
# Install a daily cron job for gh-radar (default 08:00 local time).
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
HOUR="${1:-8}"   # pass an hour 0-23 as first arg, e.g. ./install.sh 9

LINE="0 ${HOUR} * * * ${DIR}/run.sh >> ${DIR}/radar.log 2>&1"
# Replace any existing gh-radar line, then append the new one.
( crontab -l 2>/dev/null | grep -v "${DIR}/run.sh" ; echo "${LINE}" ) | crontab -

echo "Installed cron job:"
echo "  ${LINE}"
echo "Logs -> ${DIR}/radar.log   |   remove with: crontab -e"
