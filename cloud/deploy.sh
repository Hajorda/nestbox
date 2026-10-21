#!/bin/bash
# Ships ONLY this folder to Railway: app.py, describe.py (copied fresh), the site logos if you have them, and the Dockerfile.
# Nothing else from the project (no .env, no Gemini key, no config, no saved listings) is in here, so nothing else can be uploaded.
# usage: ./deploy.sh <projectId> <serviceName>      (see docs/SHARED_COPY.md)
set -e
cd "$(dirname "$0")"
[ -n "$1" ] && [ -n "$2" ] || { echo "usage: ./deploy.sh <projectId> <serviceName>"; exit 1; }
cp ../describe.py ../search.py ./
rm -rf logos && mkdir logos
cp ../data/logos/* logos/ 2>/dev/null || echo "(no data/logos folder: the shared copy will show letter badges instead of site logos)"
railway up --ci --no-gitignore -p "$1" -s "$2" -e production
