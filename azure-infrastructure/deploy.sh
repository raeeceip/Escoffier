#!/bin/bash

# Azure deployment script for Escoffier

set -e

# Variables
RESOURCE_GROUP="rg-escoffier-prod"
LOCATION="eastus"
DEPLOYMENT_NAME="escoffier-deployment-$(date +%Y%m%d%H%M%S)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting Escoffier Azure deployment...${NC}"

# Check if logged in to Azure
if ! az account show &> /dev/null; then
    echo -e "${RED}Not logged in to Azure. Please run 'az login' first.${NC}"
    exit 1
fi

# Create resource group if it doesn't exist
if ! az group exists --name $RESOURCE_GROUP &> /dev/null; then
    echo -e "${YELLOW}Creating resource group: $RESOURCE_GROUP${NC}"
    az group create --name $RESOURCE_GROUP --location $LOCATION
else
    echo -e "${GREEN}Resource group $RESOURCE_GROUP already exists${NC}"
fi

# Deploy Bicep template
echo -e "${YELLOW}Deploying infrastructure...${NC}"
DEPLOYMENT_OUTPUT=$(az deployment group create \
    --name $DEPLOYMENT_NAME \
    --resource-group $RESOURCE_GROUP \
    --template-file main.bicep \
    --parameters location=$LOCATION \
    --query "properties.outputs" \
    -o json)

# Extract outputs
CONTAINER_REGISTRY=$(echo $DEPLOYMENT_OUTPUT | jq -r '.containerRegistryLoginServer.value')
WEB_APP_NAME=$(echo $DEPLOYMENT_OUTPUT | jq -r '.webAppName.value')
WEB_APP_URL=$(echo $DEPLOYMENT_OUTPUT | jq -r '.webAppUrl.value')
POSTGRES_SERVER=$(echo $DEPLOYMENT_OUTPUT | jq -r '.postgresServerName.value')
REDIS_HOST=$(echo $DEPLOYMENT_OUTPUT | jq -r '.redisHostName.value')
AI_ENDPOINT=$(echo $DEPLOYMENT_OUTPUT | jq -r '.aiServicesEndpoint.value')

echo -e "${GREEN}Deployment completed successfully!${NC}"
echo -e "${GREEN}Infrastructure Details:${NC}"
echo "  Container Registry: $CONTAINER_REGISTRY"
echo "  Web App Name: $WEB_APP_NAME"
echo "  Web App URL: $WEB_APP_URL"
echo "  PostgreSQL Server: $POSTGRES_SERVER"
echo "  Redis Host: $REDIS_HOST"
echo "  AI Services Endpoint: $AI_ENDPOINT"

# Save outputs to file for GitHub Actions
echo -e "${YELLOW}Saving deployment outputs...${NC}"
cat > deployment-outputs.json <<EOF
{
  "containerRegistry": "$CONTAINER_REGISTRY",
  "webAppName": "$WEB_APP_NAME",
  "webAppUrl": "$WEB_APP_URL",
  "postgresServer": "$POSTGRES_SERVER",
  "redisHost": "$REDIS_HOST",
  "aiEndpoint": "$AI_ENDPOINT"
}
EOF

echo -e "${GREEN}Deployment outputs saved to deployment-outputs.json${NC}"
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Configure GitHub secrets for CI/CD"
echo "2. Deploy OpenAI models to your Azure AI Services instance"
echo "3. Run the name refactoring script"
echo "4. Push to main branch to trigger deployment"