#!/bin/bash

# Escoffier Setup Script for Unix/Linux/macOS

echo "🍳 Escoffier Kitchen Simulation Platform Setup"
echo "============================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Check if Python is available
echo -e "\n${YELLOW}1. Checking Python installation...${NC}"
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo -e "${GREEN}✅ Python found: $PYTHON_VERSION${NC}"
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_VERSION=$(python --version)
    echo -e "${GREEN}✅ Python found: $PYTHON_VERSION${NC}"
    PYTHON_CMD="python"
else
    echo -e "${RED}❌ Python not found. Please install Python 3.11+ from https://python.org${NC}"
    exit 1
fi

# Check for UV package manager
echo -e "\n${YELLOW}2. Checking UV package manager...${NC}"
UV_INSTALLED=false
if command -v uv &> /dev/null; then
    UV_VERSION=$(uv --version)
    echo -e "${GREEN}✅ UV found: $UV_VERSION${NC}"
    UV_INSTALLED=true
else
    echo -e "${YELLOW}⚠️  UV not found, will use pip instead${NC}"
fi

# Create virtual environment and install dependencies
echo -e "\n${YELLOW}3. Setting up dependencies...${NC}"

if [ "$UV_INSTALLED" = true ]; then
    echo -e "${BLUE}Installing with UV...${NC}"
    if uv sync; then
        echo -e "${GREEN}✅ Dependencies installed with UV${NC}"
    else
        echo -e "${RED}❌ UV sync failed, falling back to pip${NC}"
        UV_INSTALLED=false
    fi
fi

if [ "$UV_INSTALLED" = false ]; then
    echo -e "${BLUE}Installing with pip...${NC}"
    
    # Create virtual environment
    $PYTHON_CMD -m venv .venv
    
    # Activate virtual environment
    source .venv/bin/activate
    
    # Upgrade pip
    $PYTHON_CMD -m pip install --upgrade pip
    
    # Install dependencies
    if $PYTHON_CMD -m pip install -r requirements.txt; then
        echo -e "${GREEN}✅ Dependencies installed with pip${NC}"
    else
        echo -e "${RED}❌ Failed to install dependencies${NC}"
        exit 1
    fi
fi

# Create data directories
echo -e "\n${YELLOW}4. Creating data directories...${NC}"
DATA_DIRS=("data" "data/analytics" "data/analytics/charts" "data/analytics/reports" "data/metrics")
for dir in "${DATA_DIRS[@]}"; do
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir"
        echo -e "${GREEN}✅ Created directory: $dir${NC}"
    else
        echo -e "${GREEN}✅ Directory exists: $dir${NC}"
    fi
done

# Copy configuration template
echo -e "\n${YELLOW}5. Setting up configuration...${NC}"
if [ ! -f "configs/config.yaml" ]; then
    if [ -f "configs/config.yaml.example" ]; then
        cp "configs/config.yaml.example" "configs/config.yaml"
        echo -e "${GREEN}✅ Configuration template copied${NC}"
        echo -e "${YELLOW}⚠️  Please edit configs/config.yaml to add your API keys${NC}"
    else
        echo -e "${YELLOW}⚠️  No configuration template found${NC}"
    fi
else
    echo -e "${GREEN}✅ Configuration file already exists${NC}"
fi

# Initialize database
echo -e "\n${YELLOW}6. Initializing database...${NC}"
if [ "$UV_INSTALLED" = true ]; then
    if uv run python -m cli.main init_db; then
        echo -e "${GREEN}✅ Database initialized${NC}"
    else
        echo -e "${RED}❌ Database initialization failed${NC}"
    fi
else
    if .venv/bin/python -m cli.main init_db; then
        echo -e "${GREEN}✅ Database initialized${NC}"
    else
        echo -e "${RED}❌ Database initialization failed${NC}"
    fi
fi

# Success message
echo -e "\n${GREEN}🎉 Setup Complete!${NC}"
echo -e "${GREEN}==================${NC}"
echo ""
echo -e "${CYAN}Next steps:${NC}"
echo -e "${NC}1. Edit configs/config.yaml to add your LLM API keys${NC}"
echo -e "${NC}2. Create your first agent:${NC}"
if [ "$UV_INSTALLED" = true ]; then
    echo -e "   ${NC}uv run python -m cli.main create_agent 'Chef Gordon' head_chef 'leadership,knife_skills'${NC}"
else
    echo -e "   ${NC}.venv/bin/python -m cli.main create_agent 'Chef Gordon' head_chef 'leadership,knife_skills'${NC}"
fi
echo -e "${NC}3. Run a scenario:${NC}"
if [ "$UV_INSTALLED" = true ]; then
    echo -e "   ${NC}uv run python -m cli.main run_scenario cooking_challenge${NC}"
else
    echo -e "   ${NC}.venv/bin/python -m cli.main run_scenario cooking_challenge${NC}"
fi
echo -e "${NC}4. View metrics:${NC}"
if [ "$UV_INSTALLED" = true ]; then
    echo -e "   ${NC}uv run python -m cli.main metrics --export_csv --generate_charts${NC}"
else
    echo -e "   ${NC}.venv/bin/python -m cli.main metrics --export_csv --generate_charts${NC}"
fi
echo ""
echo -e "${CYAN}For more commands, run:${NC}"
if [ "$UV_INSTALLED" = true ]; then
    echo -e "   ${NC}uv run python -m cli.main --help${NC}"
else
    echo -e "   ${NC}.venv/bin/python -m cli.main --help${NC}"
fi
echo ""
echo -e "${GREEN}Happy cooking! 👨‍🍳🤖${NC}"