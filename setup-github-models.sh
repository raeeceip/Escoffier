#!/bin/bash

# Setup script for testing Escoffier with GitHub Models (Free Tier)

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}=== Escoffier GitHub Models Setup ===${NC}"
echo -e "${YELLOW}This script will help you set up Escoffier to use GitHub Models for free testing.${NC}"
echo

# Check if GitHub CLI is installed
if ! command -v gh &> /dev/null; then
    echo -e "${YELLOW}GitHub CLI (gh) is not installed. Would you like to install it? (y/n)${NC}"
    read -r response
    if [[ "$response" == "y" ]]; then
        if [[ "$OSTYPE" == "darwin"* ]]; then
            brew install gh
        elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
            curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
            echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
            sudo apt update
            sudo apt install gh
        fi
    fi
fi

# Check GitHub authentication
echo -e "${YELLOW}Checking GitHub authentication...${NC}"
if gh auth status &> /dev/null; then
    echo -e "${GREEN}✓ Already authenticated with GitHub${NC}"
else
    echo -e "${YELLOW}Please authenticate with GitHub:${NC}"
    gh auth login
fi

# Get GitHub token
echo -e "${YELLOW}Getting GitHub token...${NC}"
GITHUB_TOKEN=$(gh auth token)

if [ -z "$GITHUB_TOKEN" ]; then
    echo -e "${RED}Failed to get GitHub token. Please ensure you're authenticated with gh CLI.${NC}"
    exit 1
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo -e "${YELLOW}Creating .env file...${NC}"
    cat > .env << EOF
# GitHub Models Configuration
GITHUB_TOKEN=${GITHUB_TOKEN}

# Use GitHub Models configuration
CONFIG_FILE=configs/github-models.yaml

# Database (SQLite for local testing)
DATABASE_URL=sqlite://data/escoffier.db

# Logging
LOG_LEVEL=debug

# API Port
API_PORT=8080

# Metrics Port
METRICS_PORT=9090

# Playground Port
PLAYGROUND_PORT=8090
EOF
    echo -e "${GREEN}✓ Created .env file${NC}"
else
    echo -e "${YELLOW}.env file already exists. Adding GitHub token...${NC}"
    if grep -q "GITHUB_TOKEN" .env; then
        sed -i.bak "s/GITHUB_TOKEN=.*/GITHUB_TOKEN=${GITHUB_TOKEN}/" .env
    else
        echo "GITHUB_TOKEN=${GITHUB_TOKEN}" >> .env
    fi
fi

# Create data directory
mkdir -p data

# Initialize SQLite database
echo -e "${YELLOW}Initializing SQLite database...${NC}"
if [ ! -f data/escoffier.db ]; then
    sqlite3 data/escoffier.db < init.sql
    echo -e "${GREEN}✓ Database initialized${NC}"
else
    echo -e "${GREEN}✓ Database already exists${NC}"
fi

# Install Go dependencies
echo -e "${YELLOW}Installing Go dependencies...${NC}"
go mod download
go mod tidy
echo -e "${GREEN}✓ Go dependencies installed${NC}"

# Install frontend dependencies
echo -e "${YELLOW}Installing frontend dependencies...${NC}"
cd frontend
npm install
cd ..
echo -e "${GREEN}✓ Frontend dependencies installed${NC}"

# Build the project
echo -e "${YELLOW}Building the project...${NC}"
make build
echo -e "${GREEN}✓ Project built successfully${NC}"

# Create a test script
cat > test-github-models.sh << 'EOF'
#!/bin/bash
# Quick test script for GitHub Models integration

set -e
source .env

echo "Testing GitHub Models integration..."

# Test the API health endpoint
curl -s http://localhost:8080/health | jq .

# Test a simple agent interaction
curl -s -X POST http://localhost:8080/api/agents/executive-chef/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What dishes can we prepare with chicken and vegetables?",
    "context": {
      "inventory": {
        "chicken": 10,
        "vegetables": 20
      }
    }
  }' | jq .

echo "Test completed!"
EOF

chmod +x test-github-models.sh

echo
echo -e "${GREEN}=== Setup Complete! ===${NC}"
echo
echo -e "${YELLOW}To start using Escoffier with GitHub Models:${NC}"
echo "1. Start the backend: ${GREEN}./start-all.sh${NC}"
echo "2. Access the UI: ${GREEN}http://localhost:3000${NC}"
echo "3. Access the playground: ${GREEN}http://localhost:8090${NC}"
echo "4. Run tests: ${GREEN}./test-github-models.sh${NC}"
echo
echo -e "${YELLOW}Available GitHub Models:${NC}"
echo "- gpt-4o (most capable)"
echo "- gpt-4o-mini (faster, efficient)"
echo "- meta-llama-3.1-8b-instruct"
echo "- meta-llama-3.1-70b-instruct"
echo "- mistral-nemo"
echo "- phi-3.5-mini-instruct"
echo
echo -e "${YELLOW}To change the model, edit configs/github-models.yaml${NC}"
echo
echo -e "${GREEN}Happy testing! 🚀${NC}"