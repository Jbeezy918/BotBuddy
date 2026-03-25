#!/bin/bash
# RoboBuddy - One-Click Installer

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}"
echo "  ____       _           ____            _     _       "
echo " |  _ \ ___ | |__   ___ | __ ) _   _  __| | __| |_   _ "
echo " | |_) / _ \| '_ \ / _ \|  _ \| | | |/ _\` |/ _\` | | | |"
echo " |  _ < (_) | |_) | (_) | |_) | |_| | (_| | (_| | |_| |"
echo " |_| \_\___/|_.__/ \___/|____/ \__,_|\__,_|\__,_|\__, |"
echo "                                                 |___/ "
echo -e "${NC}"
echo "Your Smart Assistant That Actually Remembers You"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python 3 is required. Please install it first.${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} Python 3 found"

# Check Ollama
if ! command -v ollama &> /dev/null; then
    echo -e "${YELLOW}!${NC} Ollama not found. Installing..."
    curl -fsSL https://ollama.com/install.sh | sh
else
    echo -e "${GREEN}✓${NC} Ollama found"
fi

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi
echo -e "${GREEN}✓${NC} Virtual environment ready"

# Activate and install deps
source venv/bin/activate
pip install -r requirements.txt --quiet
echo -e "${GREEN}✓${NC} Dependencies installed"

# Copy config
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo -e "${GREEN}✓${NC} Config created (.env)"
fi

# Pull Ollama models
echo ""
echo "Downloading AI models (this may take a few minutes)..."
ollama pull llama3.2:latest 2>/dev/null || true
echo -e "${GREEN}✓${NC} Models ready"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  RoboBuddy installed successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "To start chatting:"
echo "  python chat.py"
echo ""
echo "To start the API server:"
echo "  ./run.sh"
echo ""
echo "Customize your buddy's name in .env"
echo ""
