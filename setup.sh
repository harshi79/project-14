#!/bin/bash

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Crunchyroll Login Bot Setup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Install Python packages
echo "[1/3] Installing Python packages..."
pip install -r requirements.txt

# Install Chromium browser
echo "[2/3] Installing Chromium browser..."
python -m playwright install chromium

# Install system dependencies (for cloud)
echo "[3/3] Installing system dependencies..."
python -m playwright install-deps

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅ Setup Complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Run the bot:"
echo "  export BOT_TOKEN='your_token_here'"
echo "  python main.py"
echo ""
