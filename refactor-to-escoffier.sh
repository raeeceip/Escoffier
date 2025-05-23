#!/bin/bash

# Script to refactor escoffierto Escoffier

set -e

YELLOW='\033[1;33m'
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}Starting refactoring from escoffierto Escoffier...${NC}"

# Backup current state
echo -e "${YELLOW}Creating backup...${NC}"
cp -r . ../masterchef-backup-$(date +%Y%m%d%H%M%S) 2>/dev/null || true

# Function to replace in files
replace_in_files() {
    local pattern=$1
    local replacement=$2
    local file_pattern=$3
    
    echo -e "${YELLOW}Replacing '$pattern' with '$replacement' in $file_pattern files...${NC}"
    find . -type f -name "$file_pattern" ! -path "./node_modules/*" ! -path "./.git/*" ! -path "./vendor/*" -exec sed -i '' "s/$pattern/$replacement/g" {} \;
}

# Go module and import paths
echo -e "${GREEN}Updating Go modules and imports...${NC}"
sed -i '' 's/module masterchef/module escoffier/g' go.mod
sed -i '' 's/module masterchef-cli/module escoffier-cli/g' cli/go.mod
find . -name "*.go" -type f ! -path "./vendor/*" -exec sed -i '' 's|masterchef/internal|escoffier/internal|g' {} \;

# Package.json
echo -e "${GREEN}Updating frontend package.json...${NC}"
sed -i '' 's/"name": "masterchef-frontend"/"name": "escoffier-frontend"/g' frontend/package.json

# Docker compose
echo -e "${GREEN}Updating Docker configurations...${NC}"
replace_in_files "masterchef-api" "escoffier-api" "docker-compose.yml"
replace_in_files "masterchef-postgres" "escoffier-postgres" "docker-compose.yml"
replace_in_files "masterchef-redis" "escoffier-redis" "docker-compose.yml"
replace_in_files "masterchef-prometheus" "escoffier-prometheus" "docker-compose.yml"
replace_in_files "masterchef-grafana" "escoffier-grafana" "docker-compose.yml"
replace_in_files "masterchef-jaeger" "escoffier-jaeger" "docker-compose.yml"
replace_in_files "masterchef-pgadmin" "escoffier-pgadmin" "docker-compose.yml"
replace_in_files "masterchef-net" "escoffier-net" "docker-compose.yml"
replace_in_files "masterchef" "escoffier" "docker-compose.yml"

# Database and configurations
echo -e "${GREEN}Updating database configurations...${NC}"
replace_in_files "masterchef" "escoffier" "init.sql"
replace_in_files "masterchef" "escoffier" "configs/config.yaml"
replace_in_files "masterchef-bench" "escoffier-bench" "prometheus.yml"

# Grafana dashboards
echo -e "${GREEN}Updating Grafana dashboards...${NC}"
replace_in_files "MasterChef" "Escoffier" "*.json"
replace_in_files "masterchef" "escoffier" "*.json"
mv grafana/dashboards/masterchef-overview.json grafana/dashboards/escoffier-overview.json 2>/dev/null || true

# Documentation
echo -e "${GREEN}Updating documentation...${NC}"
replace_in_files "MasterChef-Bench" "Escoffier-Bench" "*.md"
replace_in_files "MasterChef" "Escoffier" "*.md"
replace_in_files "masterchef" "escoffier" "*.md"

# HTML and frontend files
echo -e "${GREEN}Updating frontend files...${NC}"
replace_in_files "MasterChef" "Escoffier" "*.html"
replace_in_files "MasterChef" "Escoffier" "*.tsx"
replace_in_files "MasterChef" "Escoffier" "*.ts"
replace_in_files "masterchef" "escoffier" "*.tsx"
replace_in_files "masterchef" "escoffier" "*.ts"

# Shell scripts
echo -e "${GREEN}Updating shell scripts...${NC}"
replace_in_files "masterchef" "escoffier" "*.sh"
replace_in_files "MasterChef" "Escoffier" "*.sh"

# Makefile
echo -e "${GREEN}Updating Makefile...${NC}"
replace_in_files "masterchef" "escoffier" "Makefile"
replace_in_files "MasterChef" "Escoffier" "Makefile"

# Update Go source files
echo -e "${GREEN}Updating Go source files...${NC}"
replace_in_files "MasterChef" "Escoffier" "*.go"
replace_in_files "masterchef" "escoffier" "*.go"

# Update test files
echo -e "${GREEN}Updating test files...${NC}"
replace_in_files "MasterChef" "Escoffier" "*_test.go"
replace_in_files "masterchef" "escoffier" "*_test.go"

# Clean up go.mod and go.sum
echo -e "${GREEN}Cleaning up Go modules...${NC}"
go mod tidy
cd cli && go mod tidy && cd ..

echo -e "${GREEN}Refactoring completed!${NC}"
echo -e "${YELLOW}Please review the changes and run tests before committing.${NC}"
echo -e "${YELLOW}Don't forget to update any external references or documentation.${NC}"