#!/bin/bash
set -e

echo "============================================"
echo "  CIT-CQT Server Deployment"
echo "============================================"
echo ""

# 1. Create user
echo "[1/4] Creating user CIQ-CQT..."
sudo useradd -m -s /bin/bash CIQ-CQT || echo "  User already exists, skipping."

# 2. Switch to the user and clone repo
echo "[2/4] Cloning repository..."
sudo -u CIQ-CQT bash -c "
    cd ~
    if [ -d CIT-CQT ]; then
        echo '  Repo already exists, pulling latest...'
        cd CIT-CQT && git pull
    else
        git clone https://github.com/LucaSun-456/CIT-CQT.git
    fi
"

# 3. Install dependencies
echo "[3/4] Installing Python dependencies..."
sudo -u CIQ-CQT bash -c "
    cd ~/CIT-CQT
    pip install -r requirements.txt
"

# 4. Create .env and start on port 3002
echo "[4/4] Setting up environment..."
cd /home/CIQ-CQT/CIT-CQT

if [ ! -f .env ]; then
    echo "  Creating .env file..."
    sudo -u CIQ-CQT tee .env > /dev/null << 'EOF'
ELEVENLABS_API_KEY=sk_8271e0693fe305d592cc113fb578edb8589b224f1897651a
DEEPSEEK_API_KEY=sk-4707d6b74b564bcea23dbe86199c04cb
EOF
fi

echo ""
echo "============================================"
echo "  Starting server on port 3002..."
echo "============================================"
echo ""
echo "  URL: http://<your-server-ip>:3002"
echo "  Press Ctrl+C to stop"
echo ""

PORT=3002 sudo -u CIQ-CQT python app.py
