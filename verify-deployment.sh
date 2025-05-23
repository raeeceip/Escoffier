#!/bin/bash

# Verification script for Escoffier deployment readiness

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}=== Escoffier Deployment Verification ===${NC}"
echo

ERRORS=0
WARNINGS=0

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if a file exists
file_exists() {
    [ -f "$1" ]
}

# Function to report status
report_status() {
    local status=$1
    local message=$2
    
    if [ "$status" = "OK" ]; then
        echo -e "${GREEN}✓${NC} $message"
    elif [ "$status" = "WARNING" ]; then
        echo -e "${YELLOW}⚠${NC} $message"
        ((WARNINGS++))
    else
        echo -e "${RED}✗${NC} $message"
        ((ERRORS++))
    fi
}

echo -e "${YELLOW}Checking prerequisites...${NC}"

# Check Docker
if command_exists docker; then
    report_status "OK" "Docker installed"
else
    report_status "ERROR" "Docker not installed"
fi

# Check Docker Compose
if command_exists docker-compose || docker compose version >/dev/null 2>&1; then
    report_status "OK" "Docker Compose installed"
else
    report_status "ERROR" "Docker Compose not installed"
fi

# Check Go
if command_exists go; then
    GO_VERSION=$(go version | awk '{print $3}')
    report_status "OK" "Go installed ($GO_VERSION)"
else
    report_status "ERROR" "Go not installed"
fi

# Check Node.js
if command_exists node; then
    NODE_VERSION=$(node --version)
    report_status "OK" "Node.js installed ($NODE_VERSION)"
else
    report_status "ERROR" "Node.js not installed"
fi

# Check Azure CLI (for Azure deployment)
if command_exists az; then
    report_status "OK" "Azure CLI installed"
else
    report_status "WARNING" "Azure CLI not installed (required for Azure deployment)"
fi

echo
echo -e "${YELLOW}Checking project structure...${NC}"

# Check critical files
CRITICAL_FILES=(
    "go.mod"
    "Dockerfile"
    "docker-compose.yml"
    "init.sql"
    "configs/config.yaml"
    "configs/github-models.yaml"
    "azure-infrastructure/deploy.sh"
    "azure-infrastructure/deploy-cost-optimized.sh"
)

for file in "${CRITICAL_FILES[@]}"; do
    if file_exists "$file"; then
        report_status "OK" "Found $file"
    else
        report_status "ERROR" "Missing $file"
    fi
done

echo
echo -e "${YELLOW}Checking refactoring status...${NC}"

# Check if MasterChef references are gone
MASTERCHEF_COUNT=$(grep -r "masterchef\|MasterChef" --include="*.go" --include="*.yaml" --include="*.yml" --include="*.json" --include="*.md" --exclude-dir="node_modules" --exclude-dir=".git" --exclude="refactor-to-escoffier.sh" . 2>/dev/null | wc -l)

if [ "$MASTERCHEF_COUNT" -eq 0 ]; then
    report_status "OK" "No MasterChef references found"
else
    report_status "WARNING" "Found $MASTERCHEF_COUNT MasterChef references (run ./refactor-to-escoffier.sh)"
fi

# Check Go module name
GO_MODULE=$(grep "^module" go.mod | awk '{print $2}')
if [ "$GO_MODULE" = "escoffier" ]; then
    report_status "OK" "Go module correctly named: escoffier"
else
    report_status "ERROR" "Go module name incorrect: $GO_MODULE (should be escoffier)"
fi

echo
echo -e "${YELLOW}Checking deployment options...${NC}"

# Check for environment files
if file_exists ".env"; then
    report_status "OK" "Environment file exists"
else
    report_status "WARNING" ".env file not found (create one from .env.example)"
fi

# Check GitHub Actions workflows
if [ -d ".github/workflows" ]; then
    WORKFLOW_COUNT=$(ls .github/workflows/*.yml 2>/dev/null | wc -l)
    report_status "OK" "Found $WORKFLOW_COUNT GitHub Actions workflows"
else
    report_status "WARNING" "No GitHub Actions workflows found"
fi

echo
echo -e "${YELLOW}Testing build...${NC}"

# Try to build Go binary
if command_exists go; then
    if go build -o /tmp/escoffier-test cmd/main.go 2>/dev/null; then
        report_status "OK" "Go build successful"
        rm -f /tmp/escoffier-test
    else
        report_status "ERROR" "Go build failed"
    fi
fi

# Check frontend build
if [ -d "frontend" ] && file_exists "frontend/package.json"; then
    if [ -d "frontend/node_modules" ]; then
        report_status "OK" "Frontend dependencies installed"
    else
        report_status "WARNING" "Frontend dependencies not installed (run: cd frontend && npm install)"
    fi
fi

echo
echo -e "${YELLOW}Deployment readiness summary:${NC}"
echo "================================"

if [ "$ERRORS" -eq 0 ]; then
    if [ "$WARNINGS" -eq 0 ]; then
        echo -e "${GREEN}✓ All checks passed! Ready for deployment.${NC}"
    else
        echo -e "${GREEN}✓ Ready for deployment with $WARNINGS warnings.${NC}"
    fi
    
    echo
    echo -e "${YELLOW}Deployment options:${NC}"
    echo "1. Local development: ./start-all.sh"
    echo "2. Docker Compose: docker-compose up"
    echo "3. GitHub Models (free): ./setup-github-models.sh"
    echo "4. Azure (cost-optimized): cd azure-infrastructure && ./deploy-cost-optimized.sh"
    echo "5. Azure (standard): cd azure-infrastructure && ./deploy.sh"
else
    echo -e "${RED}✗ Found $ERRORS errors and $WARNINGS warnings.${NC}"
    echo -e "${RED}Please fix the errors before deployment.${NC}"
    exit 1
fi

echo
echo -e "${GREEN}For detailed deployment instructions, see AZURE_DEPLOYMENT.md${NC}"