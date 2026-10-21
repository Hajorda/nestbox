#!/bin/bash
# Ships ONLY this folder to Railway: app.py, describe.py (copied fresh), the five site logos and the Dockerfile.
# Nothing else from the project (no .env, no Gemini key, no config, no saved listings) is in here, so nothing else can be uploaded.
# usage: ./deploy.sh <projectId> <serviceName>
set -e
cd "$(dirname "$0")"
cp ../describe.py ./describe.py
rm -rf logos && mkdir logos && cp ../data/logos/* logos/
railway up --ci --no-gitignore -p "$1" -s "$2" -e production
