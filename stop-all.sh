#!/bin/bash

# MasterChef-Bench Stop Script
# Stops all running services

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Log file locations
LOG_DIR="./logs"
PID_FILE="$LOG_DIR/services.pid"

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

echo "🛑 Stopping MasterChef-Bench services..."

# Stop processes from PID file
if [ -f "$PID_FILE" ]; then
    print_status "Found PID file, stopping tracked processes..."
    while read -r pid; do
        if kill -0 "$pid" 2>/dev/null; then
            print_status "Stopping process $pid..."
            kill -TERM "$pid" 2>/dev/null || true
            
            # Wait up to 5 seconds for graceful shutdown
            count=0
            while kill -0 "$pid" 2>/dev/null && [ $count -lt 5 ]; do
                sleep 1
                count=$((count + 1))
            done
            
            # Force kill if still running
            if kill -0 "$pid" 2>/dev/null; then
                print_warning "Force killing process $pid..."
                kill -9 "$pid" 2>/dev/null || true
            fi
        fi
    done < "$PID_FILE"
    rm -f "$PID_FILE"
else
    print_warning "No PID file found, searching for processes..."
fi

# Kill any remaining processes on our ports
print_status "Checking for processes on known ports..."
for port in 3000 8080 8090 9090; do
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        print_warning "Found process on port $port, killing..."
        lsof -ti:$port | xargs kill -9 2>/dev/null || true
    fi
done

# Kill any remaining escoffierprocesses
print_status "Checking for remaining escoffierprocesses..."
pkill -f "masterchef" 2>/dev/null || true
pkill -f "react-scripts start" 2>/dev/null || true

# Clean up temporary files
if [ -d "$LOG_DIR" ]; then
    print_status "Log files preserved in $LOG_DIR"
fi

print_status "All services stopped successfully! ✅"