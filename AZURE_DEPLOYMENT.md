# Azure Deployment Guide for Escoffier (formerly MasterChef)

This guide covers the complete process of deploying the Escoffier restaurant simulation framework to Azure.

## Prerequisites

- Azure subscription with appropriate permissions
- Azure CLI installed and authenticated (`az login`)
- GitHub repository with Actions enabled
- Docker installed locally for testing

## Architecture Overview

The Escoffier framework will be deployed on Azure using:

- **Azure Container Registry (ACR)** for Docker images
- **Azure App Service** for the main application
- **Azure Database for PostgreSQL** for data persistence
- **Azure Cache for Redis** for caching and real-time features
- **Azure AI Services** for LLM capabilities
- **Azure Key Vault** for secrets management
- **Application Insights** for monitoring

## Step 1: Run the Refactoring Script

First, rename the project from escoffierto Escoffier:

```bash
chmod +x refactor-to-escoffier.sh
./refactor-to-escoffier.sh
```

This script will:

- Update all Go module references
- Rename Docker services
- Update configuration files
- Refactor all code references
- Update documentation

## Step 2: Deploy Azure Infrastructure

1. Navigate to the infrastructure directory:

   ```bash
   cd azure-infrastructure
   ```

2. Run the deployment script:

   ```bash
   chmod +x deploy.sh
   ./deploy.sh
   ```

3. Save the output values for later configuration.

## Step 3: Configure Azure AI Services

1. Go to the Azure Portal
2. Navigate to your Azure AI Services instance
3. Deploy the following models:

   - `gpt-4` or `gpt-4-turbo`
   - `gpt-3.5-turbo` (for cost-effective operations)

4. Note the deployment names for configuration.

## Step 4: Set Up GitHub Secrets

Add the following secrets to your GitHub repository:

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
```

To create Azure credentials:

```bash
az ad sp create-for-rbac --name "escoffier-github-actions" \
  --role contributor \
  --scopes /subscriptions/<subscription-id>/resourceGroups/rg-escoffier-prod \
  --sdk-auth
```

## Step 5: Update Application Configuration

1. Update the `configs/config.yaml` with Azure-specific settings:

   ```yaml
   azure:
     openai:
       endpoint: ${AZURE_OPENAI_ENDPOINT}
       deployment: gpt-4
       apiVersion: 2024-02-01
   ```

2. Ensure all environment variables are properly set in the App Service configuration.

## Step 6: Deploy the Application

1. Push your changes to trigger the GitHub Actions workflow:

   ```bash
   git add .
   git commit -m "Refactor to Escoffier and configure Azure deployment"
   git push origin main
   ```

2. Monitor the deployment in the GitHub Actions tab.

## Step 7: Post-Deployment Configuration

1. **Database Initialization**:

   ```bash
   # Connect to Azure PostgreSQL and run init.sql
   psql -h <postgres-server>.postgres.database.azure.com \
        -U escoffieradmin@<postgres-server> \
        -d escoffier \
        -f init.sql
   ```

2. **Configure Firewall Rules**:

   - Allow App Service outbound IPs in PostgreSQL firewall
   - Configure Redis firewall rules

3. **Set Up Monitoring**:
   - Configure Application Insights alerts
   - Set up log streaming
   - Configure auto-scaling rules

## Environment Variables

Key environment variables for Azure deployment:

```bash
# Database
DATABASE_URL=postgresql://escoffieradmin:${DB_PASSWORD}@${AZURE_POSTGRES_HOST}:5432/escoffier?sslmode=require

# Redis
REDIS_URL=rediss://:${REDIS_PASSWORD}@${AZURE_REDIS_HOST}:6380/0

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://<your-instance>.openai.azure.com/
AZURE_OPENAI_API_KEY=${AZURE_OPENAI_API_KEY}
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4

# Application Insights
APPLICATIONINSIGHTS_CONNECTION_STRING=${APPLICATIONINSIGHTS_CONNECTION_STRING}
```

## Scaling Considerations

1. **App Service Plan**: Start with P1v3 for production workloads
2. **Database**: Use General Purpose tier with at least 2 vCores
3. **Redis**: Standard C1 for basic caching, Premium for persistence
4. **Auto-scaling**: Configure based on CPU and memory metrics

## Cost Management

1. Use Azure Cost Management to set budgets
2. Consider using spot instances for non-critical workloads
3. Implement proper caching to reduce database calls
4. Use Application Insights sampling for high-volume scenarios

## Security Best Practices

1. Enable Azure AD authentication where possible
2. Use managed identities for service-to-service auth
3. Regularly rotate secrets in Key Vault
4. Enable Azure Defender for all services
5. Implement network security groups and private endpoints

## Troubleshooting

Common issues and solutions:

1. **Container fails to start**: Check App Service logs and container diagnostics
2. **Database connection errors**: Verify firewall rules and SSL settings
3. **Redis timeouts**: Check network configuration and connection limits
4. **AI Service errors**: Verify API keys and deployment names

## Monitoring and Alerts

Set up the following alerts:

- High CPU usage (>80%)
- Memory pressure
- Database connection pool exhaustion
- Redis cache hit ratio < 80%
- HTTP 5xx errors
- Response time > 2s

## Backup and Disaster Recovery

1. Enable automated PostgreSQL backups
2. Configure geo-replication for critical data
3. Test restore procedures regularly
4. Document recovery time objectives (RTO) and recovery point objectives (RPO)

## Next Steps

1. Set up staging environment
2. Implement CI/CD for database migrations
3. Configure custom domain and SSL
4. Set up Azure Front Door for global distribution
5. Implement Azure Policy for governance

For support and questions, refer to the Azure documentation or create an issue in the repository.
