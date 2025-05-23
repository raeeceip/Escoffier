#!/bin/bash

# MasterChef-Bench Verification Script
# Verifies that all components are properly built and configured

set -e

echo "🧑‍🍳 MasterChef-Bench System Verification"
echo "========================================"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass() {
    echo -e "${GREEN}✓${NC} $1"
}

fail() {
    echo -e "${RED}✗${NC} $1"
}

warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Check dependencies
echo ""
echo "Checking dependencies..."

if command -v go &> /dev/null; then
    pass "Go $(go version | cut -d' ' -f3) installed"
else
    fail "Go not found"
    exit 1
fi

if command -v node &> /dev/null; then
    pass "Node.js $(node --version) installed"
else
    fail "Node.js not found"
    exit 1
fi

if command -v npm &> /dev/null; then
    pass "npm $(npm --version) installed"
else
    fail "npm not found"
    exit 1
fi

# Check build artifacts
echo ""
echo "Checking build artifacts..."

if [ -f "cmd/masterchef" ]; then
    pass "Backend binary built"
else
    fail "Backend binary not found (run 'make build')"
fi

if [ -f "cli/cli" ]; then
    pass "CLI binary built"
else
    fail "CLI binary not found (run 'make build')"
fi

if [ -d "frontend/build" ] && [ "$(ls -A frontend/build)" ]; then
    pass "Frontend built"
else
    warn "Frontend not built (run 'cd frontend && npm run build')"
fi

# Check configuration
echo ""
echo "Checking configuration..."

if [ -f "configs/config.yaml" ]; then
    pass "Configuration file exists"
else
    warn "Configuration file not found (using defaults)"
fi

if [ -d "data" ]; then
    pass "Data directory exists"
else
    fail "Data directory not found"
fi

# Check scripts
echo ""
echo "Checking run scripts..."

if [ -x "start-all.sh" ]; then
    pass "Start script executable"
else
    fail "Start script not executable (run 'chmod +x start-all.sh')"
fi

if [ -x "dev.sh" ]; then
    pass "Development script executable"
else
    fail "Development script not executable (run 'chmod +x dev.sh')"
fi

if [ -f "Makefile" ]; then
    pass "Makefile exists"
else
    fail "Makefile not found"
fi

# Run basic tests
echo ""
echo "Running basic tests..."

echo "Testing Go modules..."
go mod verify > /dev/null 2>&1 && pass "Go modules verified" || fail "Go module issues"

echo "Testing backend help..."
if ./cmd/escoffier--help > /dev/null 2>&1; then
    pass "Backend binary functional"
else
    fail "Backend binary has issues"
fi

echo "Testing frontend dependencies..."
cd frontend
if npm list > /dev/null 2>&1; then
    pass "Frontend dependencies OK"
else
    warn "Frontend dependency issues (run 'npm install')"
fi
cd ..

echo ""
echo "========================================"
echo "🎯 Verification Summary"
echo ""
echo "To start the full system:"
echo "  ./start-all.sh"
echo ""
echo "For development:"
echo "  make dev"
echo "  # or"
echo "  ./dev.sh"
echo ""
echo "Individual components:"
echo "  Backend:  ./cmd/masterchef"
echo "  CLI:      ./cli/cli"
echo "  Frontend: cd frontend && npm start"
echo ""
echo "Available endpoints (when running):"
echo "  Main API:     http://localhost:8080"
echo "  Playground:   http://localhost:8090"
echo "  Metrics:      http://localhost:9090/metrics"
echo "  Health:       http://localhost:8080/health"
echo ""
echo "🧑‍🍳 Happy cooking!"