#!/bin/bash

# MasterChef-Bench Startup Script
# Starts all components of the system for local development

set -e

echo "🧑‍🍳 Starting MasterChef-Bench Platform..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Log file locations
LOG_DIR="./logs"
BACKEND_LOG="$LOG_DIR/backend.log"
FRONTEND_LOG="$LOG_DIR/frontend.log"
PID_FILE="$LOG_DIR/services.pid"

# Create log directory
mkdir -p "$LOG_DIR"

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

# Function to check if a port is in use
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0  # Port is in use
    else
        return 1  # Port is free
    fi
}

# Check dependencies
check_dependencies() {
    print_status "Checking dependencies..."
    
    if ! command -v go &> /dev/null; then
        print_error "Go is required but not installed"
        exit 1
    fi
    
    if ! command -v node &> /dev/null; then
        print_error "Node.js is required but not installed"
        exit 1
    fi
    
    if ! command -v npm &> /dev/null; then
        print_error "npm is required but not installed"
        exit 1
    fi
    
    print_status "Dependencies OK"
}

# Build backend
build_backend() {
    print_status "Building backend..."
    go build -o escoffiercmd/main.go
    print_status "Backend built successfully"
}

# Build CLI
build_cli() {
    print_status "Building CLI..."
    cd cli
    go build -o cli main.go client.go
    cd ..
    print_status "CLI built successfully"
}

# Setup frontend
setup_frontend() {
    print_status "Setting up frontend..."
    cd frontend
    if [ ! -d "node_modules" ] || [ "package.json" -nt "node_modules" ]; then
        print_status "Installing frontend dependencies..."
        npm ci
    fi
    cd ..
    print_status "Frontend ready"
}

# Start services
start_services() {
    print_status "Starting services..."
    
    # Create data directory if it doesn't exist
    mkdir -p data
    
    # Clear PID file
    > "$PID_FILE"
    
    # Check if ports are already in use
    for port in 3000 8080 8090 9090; do
        if check_port "$port"; then
            print_warning "Port $port is already in use. Killing existing process..."
            lsof -ti:$port | xargs kill -9 2>/dev/null || true
            sleep 1
        fi
    done
    
    # Start backend API server
    print_status "Starting backend server..."
    ./escoffier> "$BACKEND_LOG" 2>&1 &
    BACKEND_PID=$!
    echo "$BACKEND_PID" >> "$PID_FILE"
    print_status "Backend server started (PID: $BACKEND_PID)"
    
    # Wait for backend to be ready
    local attempts=0
    while [ $attempts -lt 30 ]; do
        if curl -s "http://localhost:8080/health" >/dev/null 2>&1; then
            print_status "Backend API is ready!"
            break
        fi
        sleep 1
        attempts=$((attempts + 1))
    done
    
    if [ $attempts -eq 30 ]; then
        print_error "Backend failed to start. Check $BACKEND_LOG for details"
        tail -20 "$BACKEND_LOG"
        exit 1
    fi
    
    # Start frontend server
    print_status "Starting frontend development server..."
    cd frontend && npm start > "../$FRONTEND_LOG" 2>&1 &
    FRONTEND_PID=$!
    cd ..
    echo "$FRONTEND_PID" >> "$PID_FILE"
    print_status "Frontend server started (PID: $FRONTEND_PID)"
    
    # Wait a bit for frontend to compile
    sleep 5
    
    print_status "All services started successfully!"
    echo ""
    echo "Access the services at:"
    echo "  📊 Frontend:    http://localhost:3000"
    echo "  🔧 Backend API: http://localhost:8080"
    echo "  🎮 Playground:  http://localhost:8090"
    echo "  📈 Metrics:     http://localhost:9090"
    echo ""
    echo "Logs are available at:"
    echo "  Backend:  $BACKEND_LOG"
    echo "  Frontend: $FRONTEND_LOG"
    echo ""
    echo "To stop all services, press Ctrl+C or run ./stop-all.sh"
    echo ""
    
    # Wait for interrupt
    trap cleanup SIGINT SIGTERM
    
    # Keep script running
    print_status "Services are running. Press Ctrl+C to stop..."
    while true; do
        sleep 1
    done
}

# Cleanup function
cleanup() {
    print_warning "Shutting down services..."
    
    # Kill all processes started by this script
    if [ -f "$PID_FILE" ]; then
        while read -r pid; do
            if kill -0 "$pid" 2>/dev/null; then
                print_status "Stopping process $pid..."
                kill -TERM "$pid" 2>/dev/null || true
            fi
        done < "$PID_FILE"
        rm -f "$PID_FILE"
    fi
    
    print_status "All services stopped"
    exit 0
}

# Main execution
main() {
    check_dependencies
    build_backend
    # Skip CLI build for development
    setup_frontend
    start_services
}

main "$@"