# Azure Deployment Guide for Escoffier

This comprehensive guide covers deploying the Escoffier restaurant simulation framework to Azure, with both standard and cost-optimized options.

## Prerequisites

- Azure subscription with appropriate permissions
- Azure CLI installed and authenticated (`az login`)
- GitHub repository with Actions enabled
- Docker installed locally for testing

## Deployment Options

### Option 1: Cost-Optimized Deployment (~$150-250/month)
Best for development, testing, and small-scale production workloads.

### Option 2: Standard Deployment (~$500-800/month)
Best for production workloads requiring high availability and performance.

## Architecture Overview

### Cost-Optimized Architecture
- **Frontend**: Azure Storage Static Website + CDN (~$10/month)
- **Backend API**: Azure App Service B1 tier with auto-scaling (~$55/month)
- **Database**: PostgreSQL Flexible Server Burstable tier (~$25/month)
- **Cache**: Redis Basic C0 tier (~$17/month)
- **AI**: Azure OpenAI (pay-per-use)
- **Monitoring**: Application Insights + Azure Monitor (~$30/month)

### Standard Architecture
- **Frontend**: Azure App Service with CDN
- **Backend API**: Azure App Service P1v3 tier
- **Database**: PostgreSQL General Purpose with HA
- **Cache**: Redis Standard/Premium tier
- **AI**: Azure OpenAI with dedicated capacity
- **Monitoring**: Full Application Insights with retention

## Deployment Steps

### Step 1: Prepare the Codebase

The refactoring from MasterChef to Escoffier has already been completed. Verify by checking:

```bash
# Check Go module name
grep "module" go.mod
# Should show: module escoffier

# Check database references
grep -r "escoffier.db" --include="*.go" .
```

### Step 2: Choose Deployment Type

Navigate to the infrastructure directory:

```bash
cd azure-infrastructure
```

#### For Cost-Optimized Deployment:
```bash
chmod +x deploy-cost-optimized.sh
./deploy-cost-optimized.sh
```

#### For Standard Deployment:
```bash
chmod +x deploy.sh
./deploy.sh
```

### Step 3: Configure Azure AI Services

1. Go to Azure Portal → Your AI Services instance
2. Deploy the following models:
   - `gpt-4` or `gpt-4-turbo` with deployment name: `escoffier-gpt4`
   - `gpt-3.5-turbo` with deployment name: `escoffier-gpt35` (for cost-effective operations)

### Step 4: Set Up GitHub Secrets

Add these secrets to your GitHub repository:

```bash
# Azure Container Registry
ACR_LOGIN_SERVER=<your-acr>.azurecr.io
ACR_USERNAME=<acr-username>
ACR_PASSWORD=<acr-password>

# Azure Credentials (for deployment)
AZURE_CREDENTIALS=<service-principal-json>

# Database
DB_PASSWORD=<secure-password>

# Redis
REDIS_PASSWORD=<redis-access-key>

# Azure OpenAI
AZURE_OPENAI_API_KEY=<your-api-key>
AZURE_OPENAI_ENDPOINT=https://<your-instance>.openai.azure.com/
```

To create Azure credentials:
```bash
az ad sp create-for-rbac --name "escoffier-github-actions" \
  --role contributor \
  --scopes /subscriptions/<subscription-id>/resourceGroups/rg-escoffier-prod \
  --sdk-auth
```

### Step 5: Initialize Database

```bash
# Get the PostgreSQL connection string from deployment output
POSTGRES_SERVER=$(cat deployment-config.json | jq -r '.postgresServer')

# Initialize the database
psql -h ${POSTGRES_SERVER}.postgres.database.azure.com \
     -U escoffieradmin@${POSTGRES_SERVER} \
     -d escoffier \
     -f ../init.sql
```

### Step 6: Deploy the Application

Push your changes to trigger the GitHub Actions workflow:

```bash
git add .
git commit -m "Deploy Escoffier to Azure"
git push origin main
```

## Environment Variables

Configure these in your App Service:

```bash
# Database
DATABASE_URL=postgresql://escoffieradmin:${DB_PASSWORD}@${AZURE_POSTGRES_HOST}:5432/escoffier?sslmode=require

# Redis
REDIS_URL=rediss://:${REDIS_PASSWORD}@${AZURE_REDIS_HOST}:6380/0

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://<your-instance>.openai.azure.com/
AZURE_OPENAI_API_KEY=${AZURE_OPENAI_API_KEY}
AZURE_OPENAI_DEPLOYMENT_NAME=escoffier-gpt4

# Application Insights
APPLICATIONINSIGHTS_CONNECTION_STRING=${APPLICATIONINSIGHTS_CONNECTION_STRING}
```

## Cost Management Strategies

### 1. Use Reserved Instances
- Save up to 40% on App Service and Database
- 1-year or 3-year commitments

### 2. Implement Auto-scaling
- Scale down during off-hours
- Use CPU and memory metrics
- Configure minimum instances

### 3. Optimize AI Usage
- Use GPT-3.5 for non-critical tasks
- Implement response caching
- Monitor token usage

### 4. Database Optimization
- Use connection pooling
- Implement query caching
- Regular index maintenance

## Monitoring and Alerts

### Key Metrics
1. **Performance**:
   - API response time (target: <200ms p95)
   - Order processing time (target: <5s)
   - Database query time (target: <50ms)

2. **Availability**:
   - Uptime (target: 99.9%)
   - Failed requests (target: <0.1%)
   - Health check status

3. **Cost**:
   - Daily spend tracking
   - Resource utilization
   - AI token usage

### Setting Up Alerts
```bash
# High CPU usage
az monitor metrics alert create \
  --name high-cpu \
  --resource-group rg-escoffier-prod \
  --scopes /subscriptions/.../providers/Microsoft.Web/sites/escoffier-app \
  --condition "avg Percentage CPU > 80" \
  --window-size 5m

# Database connection failures
az monitor metrics alert create \
  --name db-connection-failures \
  --resource-group rg-escoffier-prod \
  --scopes /subscriptions/.../providers/Microsoft.DBforPostgreSQL/flexibleServers/... \
  --condition "count failed_connections > 10" \
  --window-size 5m
```

## Troubleshooting

### Application Logs
```bash
# Stream live logs
az webapp log tail --name escoffier-app --resource-group rg-escoffier-prod

# Download logs
az webapp log download --name escoffier-app --resource-group rg-escoffier-prod
```

### Database Issues
```bash
# Check connection
psql -h ${POSTGRES_SERVER}.postgres.database.azure.com \
     -U escoffieradmin@${POSTGRES_SERVER} \
     -d escoffier \
     -c "SELECT 1"

# View active connections
az postgres flexible-server show-connection-string \
  --server-name ${POSTGRES_SERVER} \
  --resource-group rg-escoffier-prod
```

### Common Issues
1. **Container fails to start**: Check image registry permissions and environment variables
2. **Database timeouts**: Verify firewall rules and connection pooling settings
3. **Redis connection errors**: Check SSL settings and access keys
4. **AI Service errors**: Verify API keys and rate limits

## Security Best Practices

1. **Enable Managed Identities** for service-to-service authentication
2. **Use Key Vault** for all secrets
3. **Configure Network Security Groups** to restrict access
4. **Enable Azure Defender** for threat protection
5. **Implement Private Endpoints** for database and Redis
6. **Regular Security Audits** using Azure Security Center

## Backup and Disaster Recovery

1. **Database Backups**:
   - Automated daily backups (7-day retention minimum)
   - Geo-redundant backups for production

2. **Application State**:
   - Use Azure Backup for configuration
   - Document infrastructure as code

3. **Recovery Testing**:
   - Monthly restore drills
   - Document RTO/RPO requirements

## Next Steps

1. **Production Readiness**:
   - Configure custom domain and SSL
   - Set up staging environments
   - Implement blue-green deployments

2. **Performance Optimization**:
   - Enable Azure Front Door for global distribution
   - Implement aggressive caching strategies
   - Optimize database queries

3. **Governance**:
   - Implement Azure Policy
   - Set up cost budgets and alerts
   - Configure resource tagging

For additional support, refer to the Azure documentation or create an issue in the repository.