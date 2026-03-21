#!/bin/bash
# setup.sh - Run this ONCE in the PythonAnywhere bash console.
# It clones the repo, creates a virtualenv, and installs dependencies.
#
# In the PythonAnywhere bash console, run:
#   bash ~/mathquest/deploy/setup.sh
#
# Or if you haven't cloned yet, paste these lines directly:

set -e  # stop on any error

REPO="https://github.com/arrivingskills/mathquest.git"
APP_DIR="$HOME/mathquest"
VENV_DIR="$APP_DIR/venv"
PYTHON_VERSION="python3.12"

echo ""
echo "=== MathQuest — PythonAnywhere setup ==="
echo ""

# ── 1. Clone or update the repo ──────────────────────────────────────────────
if [ -d "$APP_DIR/.git" ]; then
    echo "[1/3] Repo already cloned — pulling latest changes..."
    git -C "$APP_DIR" pull
else
    echo "[1/3] Cloning repo..."
    git clone "$REPO" "$APP_DIR"
fi

# ── 2. Create virtual environment ────────────────────────────────────────────
if [ -d "$VENV_DIR" ]; then
    echo "[2/3] Virtualenv already exists — skipping creation."
else
    echo "[2/3] Creating virtualenv with $PYTHON_VERSION..."
    $PYTHON_VERSION -m venv "$VENV_DIR"
fi

# ── 3. Install / upgrade dependencies ────────────────────────────────────────
echo "[3/3] Installing dependencies..."
"$VENV_DIR/bin/pip" install --upgrade pip --quiet
"$VENV_DIR/bin/pip" install "$APP_DIR" --quiet

echo ""
echo "Setup complete!"
echo "Now run deploy.py on your local machine to configure the web app."
echo ""
