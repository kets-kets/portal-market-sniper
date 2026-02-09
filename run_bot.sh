#!/bin/bash

# Script for automatic launch and restart of NFT Sniper Bot
# On 401 error, bot will automatically refresh token and restart

echo "🚀 Starting NFT Sniper Bot with auto-restart..."

while true; do
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Starting bot..."
    export PYTHONPATH=$(pwd)
    .venv/bin/python3 src/main.py

    EXIT_CODE=$?
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Bot exited with code: $EXIT_CODE"

    if [ $EXIT_CODE -eq 0 ]; then
        echo "✅ Bot exited normally"
        break
    else
        echo "⚠️  Bot exited with error. Restarting in 5 seconds..."
        sleep 5
    fi
done

echo "🏁 Work finished"
