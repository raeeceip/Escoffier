#!/bin/bash

# Cost-optimized Azure deployment script for Escoffier

set -e

# Variables
RESOURCE_GROUP="rg-escoffier-prod"
LOCATION="eastus"
DEPLOYMENT_NAME="escoffier-cost-optimized-$(date +%Y%m%d%H%M%S)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}Escoffier Cost-Optimized Azure Deployment${NC}"
echo -e "${BLUE}======================================${NC}"

# Function to check command existence
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"
if ! command_exists az; then
    echo -e "${RED}Azure CLI not found. Please install: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli${NC}"
    exit 1
fi

if ! command_exists jq; then
    echo -e "${RED}jq not found. Please install jq for JSON parsing.${NC}"
    exit 1
fi

# Check Azure login
if ! az account show &> /dev/null; then
    echo -e "${RED}Not logged in to Azure. Please run 'az login' first.${NC}"
    exit 1
fi

SUBSCRIPTION=$(az account show --query name -o tsv)
echo -e "${GREEN}Using subscription: $SUBSCRIPTION${NC}"

# Create resource group
echo -e "${YELLOW}Creating resource group: $RESOURCE_GROUP${NC}"
az group create --name $RESOURCE_GROUP --location $LOCATION --output none || true

# Deploy cost-optimized infrastructure
echo -e "${YELLOW}Deploying cost-optimized infrastructure...${NC}"
DEPLOYMENT_OUTPUT=$(az deployment group create \
    --name $DEPLOYMENT_NAME \
    --resource-group $RESOURCE_GROUP \
    --template-file cost-optimized.bicep \
    --parameters location=$LOCATION \
    --query "properties.outputs" \
    -o json)

# Extract outputs
CONTAINER_REGISTRY=$(echo $DEPLOYMENT_OUTPUT | jq -r '.containerRegistryLoginServer.value')
WEB_APP_NAME=$(echo $DEPLOYMENT_OUTPUT | jq -r '.webAppName.value')
WEB_APP_URL=$(echo $DEPLOYMENT_OUTPUT | jq -r '.webAppUrl.value')
CDN_ENDPOINT=$(echo $DEPLOYMENT_OUTPUT | jq -r '.cdnEndpoint.value')
POSTGRES_SERVER=$(echo $DEPLOYMENT_OUTPUT | jq -r '.postgresServerName.value')
REDIS_HOST=$(echo $DEPLOYMENT_OUTPUT | jq -r '.redisHostName.value')
AI_ENDPOINT=$(echo $DEPLOYMENT_OUTPUT | jq -r '.aiServicesEndpoint.value')
APP_INSIGHTS_KEY=$(echo $DEPLOYMENT_OUTPUT | jq -r '.appInsightsInstrumentationKey.value')
APP_INSIGHTS_CONNECTION=$(echo $DEPLOYMENT_OUTPUT | jq -r '.appInsightsConnectionString.value')

echo -e "${GREEN}Infrastructure deployment completed!${NC}"

# Deploy monitoring setup
echo -e "${YELLOW}Setting up monitoring...${NC}"
MONITORING_OUTPUT=$(az deployment group create \
    --name "$DEPLOYMENT_NAME-monitoring" \
    --resource-group $RESOURCE_GROUP \
    --template-file monitoring-setup.bicep \
    --parameters location=$LOCATION \
                 environment=production \
                 logAnalyticsWorkspaceId="/subscriptions/$(az account show --query id -o tsv)/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.OperationalInsights/workspaces/log-escoffier-production" \
                 appInsightsName="appi-escoffier-production" \
                 webAppResourceId="/subscriptions/$(az account show --query id -o tsv)/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Web/sites/$WEB_APP_NAME" \
                 postgresResourceId="/subscriptions/$(az account show --query id -o tsv)/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.DBforPostgreSQL/flexibleServers/$POSTGRES_SERVER" \
                 redisResourceId="/subscriptions/$(az account show --query id -o tsv)/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Cache/redis/${REDIS_HOST%%.*}" \
    --query "properties.outputs" \
    -o json)

GRAFANA_URL=$(echo $MONITORING_OUTPUT | jq -r '.grafanaUrl.value')

# Configure PostgreSQL firewall
echo -e "${YELLOW}Configuring PostgreSQL firewall rules...${NC}"
MY_IP=$(curl -s https://api.ipify.org)
az postgres flexible-server firewall-rule create \
    --resource-group $RESOURCE_GROUP \
    --name $POSTGRES_SERVER \
    --rule-name "AllowMyIP" \
    --start-ip-address $MY_IP \
    --end-ip-address $MY_IP \
    --output none

# Get Web App outbound IPs
WEBAPP_IPS=$(az webapp show --resource-group $RESOURCE_GROUP --name $WEB_APP_NAME --query "outboundIpAddresses" -o tsv | tr ',' '\n')
COUNTER=1
for IP in $WEBAPP_IPS; do
    az postgres flexible-server firewall-rule create \
        --resource-group $RESOURCE_GROUP \
        --name $POSTGRES_SERVER \
        --rule-name "AllowWebApp$COUNTER" \
        --start-ip-address $IP \
        --end-ip-address $IP \
        --output none || true
    ((COUNTER++))
done

# Deploy AI models
echo -e "${YELLOW}Configuring Azure OpenAI models...${NC}"
echo -e "${YELLOW}Please deploy the following models manually in Azure Portal:${NC}"
echo "  1. Navigate to: $AI_ENDPOINT"
echo "  2. Deploy model: gpt-4 (or gpt-4-turbo)"
echo "  3. Deploy model: gpt-3.5-turbo"
echo "  4. Note the deployment names for configuration"

# Generate deployment configuration
echo -e "${YELLOW}Generating deployment configuration...${NC}"
cat > deployment-config.json <<EOF
{
  "resourceGroup": "$RESOURCE_GROUP",
  "containerRegistry": "$CONTAINER_REGISTRY",
  "webAppName": "$WEB_APP_NAME",
  "webAppUrl": "$WEB_APP_URL",
  "cdnEndpoint": "$CDN_ENDPOINT",
  "postgresServer": "$POSTGRES_SERVER",
  "redisHost": "$REDIS_HOST",
  "aiEndpoint": "$AI_ENDPOINT",
  "appInsightsKey": "$APP_INSIGHTS_KEY",
  "appInsightsConnection": "$APP_INSIGHTS_CONNECTION",
  "grafanaUrl": "$GRAFANA_URL"
}
EOF

# Generate GitHub Actions secrets script
echo -e "${YELLOW}Generating GitHub secrets configuration...${NC}"
cat > set-github-secrets.sh <<'SCRIPT'
#!/bin/bash

# This script sets up GitHub secrets for the Escoffier deployment

echo "Setting up GitHub secrets..."

# Read deployment config
CONFIG=$(cat deployment-config.json)

# Extract values
ACR_LOGIN_SERVER=$(echo $CONFIG | jq -r '.containerRegistry')
WEB_APP_NAME=$(echo $CONFIG | jq -r '.webAppName')

# Get ACR credentials
ACR_USERNAME=$(az acr credential show --name ${ACR_LOGIN_SERVER%%.*} --query username -o tsv)
ACR_PASSWORD=$(az acr credential show --name ${ACR_LOGIN_SERVER%%.*} --query passwords[0].value -o tsv)

# Create service principal for GitHub Actions
SP_OUTPUT=$(az ad sp create-for-rbac --name "escoffier-github-actions" \
    --role contributor \
    --scopes /subscriptions/$(az account show --query id -o tsv)/resourceGroups/rg-escoffier-prod \
    --sdk-auth)

echo "Add these secrets to your GitHub repository:"
echo "----------------------------------------"
echo "ACR_LOGIN_SERVER=$ACR_LOGIN_SERVER"
echo "ACR_USERNAME=$ACR_USERNAME"
echo "ACR_PASSWORD=$ACR_PASSWORD"
echo ""
echo "AZURE_CREDENTIALS:"
echo "$SP_OUTPUT"
echo ""
echo "Also add these application secrets:"
echo "DB_PASSWORD=<your-secure-password>"
echo "REDIS_PASSWORD=<redis-access-key>"
echo "AZURE_OPENAI_API_KEY=<your-api-key>"
SCRIPT

chmod +x set-github-secrets.sh

# Display summary
echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}Deployment Summary${NC}"
echo -e "${GREEN}======================================${NC}"
echo -e "${BLUE}Infrastructure:${NC}"
echo "  Resource Group: $RESOURCE_GROUP"
echo "  Location: $LOCATION"
echo ""
echo -e "${BLUE}Application:${NC}"
echo "  Web App URL: $WEB_APP_URL"
echo "  CDN Endpoint: $CDN_ENDPOINT"
echo "  Container Registry: $CONTAINER_REGISTRY"
echo ""
echo -e "${BLUE}Data Services:${NC}"
echo "  PostgreSQL: $POSTGRES_SERVER"
echo "  Redis: $REDIS_HOST"
echo ""
echo -e "${BLUE}AI Services:${NC}"
echo "  Endpoint: $AI_ENDPOINT"
echo ""
echo -e "${BLUE}Monitoring:${NC}"
echo "  Grafana: $GRAFANA_URL"
echo "  App Insights Key: $APP_INSIGHTS_KEY"
echo ""
echo -e "${BLUE}Cost Optimization Features:${NC}"
echo "  ✓ Basic tier App Service Plan (B1) with auto-scaling"
echo "  ✓ Burstable PostgreSQL (B1ms)"
echo "  ✓ Basic Redis Cache (C0)"
echo "  ✓ CDN for static assets"
echo "  ✓ Storage account for frontend hosting"
echo "  ✓ Budget alerts configured"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Run ./set-github-secrets.sh to configure GitHub secrets"
echo "2. Deploy OpenAI models in Azure Portal"
echo "3. Run the refactoring script: ./refactor-to-escoffier.sh"
echo "4. Initialize the database with init.sql"
echo "5. Push to main branch to trigger deployment"
echo ""
echo -e "${BLUE}Estimated Monthly Cost: ~$150-250 USD${NC}"
echo "  - App Service (B1): ~$55"
echo "  - PostgreSQL (B1ms): ~$25"
echo "  - Redis (C0): ~$17"
echo "  - Storage + CDN: ~$10"
echo "  - AI Services: Usage-based"
echo "  - Monitoring: ~$30"