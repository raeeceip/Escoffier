#!/bin/bash

# MasterChef-Bench Development Script
# Starts all components in development mode with hot reloading

set -e

echo "🧑‍🍳 Starting MasterChef-Bench in Development Mode..."

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[DEV]${NC} $1"
}

# Function to run backend in development mode
start_backend_dev() {
    print_status "Starting backend in development mode..."
    cd $(dirname $0)
    
    # Set development environment variables
    export NODE_ENV=development
    export GIN_MODE=debug
    export LOG_LEVEL=debug
    
    # Run with air for hot reload if available, otherwise use go run
    if command -v air &> /dev/null; then
        air
    else
        print_status "Air not found, using 'go run' (install air for hot reload: go install github.com/cosmtrek/air@latest)"
        go run cmd/main.go --port=8080 --playground-port=8090 --metrics-port=9090
    fi
}

# Function to run frontend in development mode
start_frontend_dev() {
    print_status "Starting frontend in development mode..."
    cd frontend
    npm install
    npm start
}

# Function to run CLI in development mode
run_cli_dev() {
    print_status "Building and running CLI..."
    cd cli
    go run main.go client.go "$@"
}

# Main menu
show_menu() {
    echo ""
    echo -e "${BLUE}MasterChef-Bench Development Menu${NC}"
    echo "1. Start Backend (API + Playground + Metrics)"
    echo "2. Start Frontend (React Development Server)"
    echo "3. Run CLI Client"
    echo "4. Run Tests"
    echo "5. Build All"
    echo "6. Exit"
    echo ""
}

# Run tests
run_tests() {
    print_status "Running tests..."
    echo "Running Go tests..."
    go test ./internal/...
    echo ""
    echo "Running Frontend tests..."
    cd frontend
    npm test -- --watchAll=false
    cd ..
    print_status "Tests completed"
}

# Build all components
build_all() {
    print_status "Building all components..."
    
    # Build backend
    go build -o cmd/masterchef cmd/main.go
    
    # Build CLI
    cd cli
    go build -o cli main.go client.go
    cd ..
    
    # Build frontend
    cd frontend
    npm run build
    cd ..
    
    print_status "All components built successfully"
}

# Handle menu selection
while true; do
    show_menu
    read -p "Select an option [1-6]: " choice
    
    case $choice in
        1)
            start_backend_dev
            ;;
        2)
            start_frontend_dev
            ;;
        3)
            echo "CLI arguments (or press Enter for help):"
            read -r cli_args
            run_cli_dev $cli_args
            ;;
        4)
            run_tests
            ;;
        5)
            build_all
            ;;
        6)
            print_status "Goodbye!"
            exit 0
            ;;
        *)
            echo "Invalid option. Please select 1-6."
            ;;
    esac
    
    echo ""
    read -p "Press Enter to return to menu..."
done