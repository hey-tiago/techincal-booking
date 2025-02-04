#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Setting up backend...${NC}"
# Setup backend
cd backend
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