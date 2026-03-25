#!/bin/bash
# BotBuddy - Run Script

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting BotBuddy...${NC}"

# Check for .env
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}No .env file found. Copying from .env.example...${NC}"
    cp .env.example .env
    echo -e "${YELLOW}Please edit .env with your API keys before running.${NC}"
    exit 1
fi

# Check for venv
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate venv
source venv/bin/activate

# Install dependencies
echo -e "${GREEN}Installing dependencies...${NC}"
pip install -r requirements.txt --quiet

# Run the app
echo -e "${GREEN}Starting server on http://localhost:8000${NC}"
echo -e "${GREEN}API docs at http://localhost:8000/docs${NC}"
echo ""

python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
