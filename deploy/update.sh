#!/bin/bash
# update.sh - Run this in the PythonAnywhere bash console to deploy new code.
# After the initial setup, use this every time you push changes to GitHub.
#
# In the PythonAnywhere bash console, run:
#   bash ~/mathquest/deploy/update.sh

set -e

APP_DIR="$HOME/mathquest"
VENV_DIR="$APP_DIR/venv"

echo ""
echo "=== MathQuest — pulling latest code ==="

echo "[1/2] Pulling from GitHub..."
git -C "$APP_DIR" pull

echo "[2/2] Re-installing package (picks up any dependency changes)..."
"$VENV_DIR/bin/pip" install "$APP_DIR" --quiet

echo ""
echo "Done!  Now reload the web app:"
echo "  python deploy/deploy.py --username YOUR_USERNAME --token YOUR_TOKEN"
echo "(or click 'Reload' in the PythonAnywhere Web tab)"
echo ""
