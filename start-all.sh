#!/bin/bash

# MasterChef-Bench Startup Script
# Starts all components of the system

set -e

echo "🧑‍🍳 Starting MasterChef-Bench Platform..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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
    go build -o cmd/masterchef cmd/main.go
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
    if [ ! -d "node_modules" ]; then
        print_status "Installing frontend dependencies..."
        npm install
    fi
    print_status "Building frontend..."
    npm run build
    cd ..
    print_status "Frontend ready"
}

# Start services
start_services() {
    print_status "Starting services..."
    
    # Create data directory if it doesn't exist
    mkdir -p data
    
    # Start backend API server
    print_status "Starting backend API server on port 8080..."
    ./cmd/masterchef --port=8080 --playground-port=8090 --metrics-port=9090 &
    BACKEND_PID=$!
    
    # Wait a moment for backend to start
    sleep 3
    
    # Check if backend is running
    if ! kill -0 $BACKEND_PID 2>/dev/null; then
        print_error "Backend failed to start"
        exit 1
    fi
    
    print_status "All services started successfully!"
    print_status "Backend API: http://localhost:8080"
    print_status "LLM Playground: http://localhost:8090"
    print_status "Metrics: http://localhost:9090/metrics"
    
    # Store PIDs for cleanup
    echo $BACKEND_PID > .pids
    
    print_status "Press Ctrl+C to stop all services"
    
    # Wait for interrupt
    trap cleanup SIGINT
    wait $BACKEND_PID
}

# Cleanup function
cleanup() {
    print_warning "Shutting down services..."
    if [ -f .pids ]; then
        while read pid; do
            if kill -0 $pid 2>/dev/null; then
                kill $pid
                print_status "Stopped process $pid"
            fi
        done < .pids
        rm .pids
    fi
    print_status "All services stopped"
    exit 0
}

# Main execution
main() {
    check_dependencies
    build_backend
    build_cli
    setup_frontend
    start_services
}

main "$@"