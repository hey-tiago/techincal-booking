#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}Setting up backend...${NC}"
# Setup backend
cd backend

# Handle .env file setup
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}Setting up environment variables...${NC}"
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo -e "${YELLOW}Please enter your OpenAI API key:${NC}"
        read -r OPENAI_KEY
        # Replace the OPENAI_API_KEY placeholder in .env file
        sed -i '' "s/OPENAI_API_KEY=.*/OPENAI_API_KEY=$OPENAI_KEY/" .env
        echo -e "${GREEN}Environment variables configured!${NC}"
    else
        echo -e "${YELLOW}Warning: .env.example file not found${NC}"
    fi
fi

# Create and activate virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python -m venv venv
fi
source venv/bin/activate
# Install backend dependencies
pip install -r requirements.txt

echo -e "${BLUE}Starting backend server...${NC}"
python app/main.py &
BACKEND_PID=$!

echo -e "${BLUE}Setting up frontend...${NC}"
# Setup frontend
cd ../frontend
# Install frontend dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install
fi

echo -e "${BLUE}Starting frontend server...${NC}"
npm run dev &
FRONTEND_PID=$!

echo -e "${GREEN}Both servers are running!${NC}"
echo -e "${GREEN}Frontend: http://localhost:3000${NC}"
echo -e "${GREEN}Backend: http://localhost:8000${NC}"

# Handle script termination
trap "kill $BACKEND_PID $FRONTEND_PID; deactivate" SIGINT SIGTERM

# Keep script running
wait 