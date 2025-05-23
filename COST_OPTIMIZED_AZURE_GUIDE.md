# Cost-Optimized Azure Deployment Guide for Escoffier

This guide provides a complete, cost-optimized deployment strategy for the Escoffier restaurant simulation system on Azure.

## Overview

The cost-optimized deployment uses:
- **Frontend**: Azure Storage Static Website + CDN (~$10/month)
- **Backend API**: Azure App Service B1 tier with auto-scaling (~$55/month)
- **Database**: PostgreSQL Flexible Server Burstable tier (~$25/month)
- **Cache**: Redis Basic C0 tier (~$17/month)
- **AI**: Azure OpenAI (pay-per-use)
- **Monitoring**: Application Insights + Azure Monitor (~$30/month)

**Total estimated cost: $150-250/month** (excluding AI usage)

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Azure CDN     │────▶│  Static Website │────▶│   Frontend      │
│                 │     │  (Storage Acct) │     │  (React SPA)    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                          │
                                                          ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ Azure App       │────▶│   Container     │────▶│   Backend API   │
│ Service (B1)    │     │   Registry      │     │   (Go)          │
└─────────────────┘     └─────────────────┘     └─────────────────┘
         │                                                │
         ▼                                                ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   PostgreSQL    │     │   Redis Cache   │     │  Azure OpenAI   │
│   (Burstable)   │     │   (Basic C0)    │     │   (Pay-per-use) │
└─────────────────┘     └─────────────────┘     └─────────────────┘
         │                       │                        │
         └───────────────────────┴────────────────────────┘
                                 │
                        ┌────────▼────────┐
                        │ App Insights &  │
                        │ Azure Monitor   │
                        └─────────────────┘
```

## Deployment Steps

### 1. Prerequisites

```bash
# Install required tools
brew install azure-cli jq

# Login to Azure
az login

# Set your subscription (if you have multiple)
az account set --subscription "Your Subscription Name"
```

### 2. Run the Refactoring Script

```bash
# Make the script executable
chmod +x refactor-to-escoffier.sh

# Run the refactoring
./refactor-to-escoffier.sh
```

### 3. Deploy Infrastructure

```bash
cd azure-infrastructure

# Make the deployment script executable
chmod +x deploy-cost-optimized.sh

# Run the deployment
./deploy-cost-optimized.sh
```

### 4. Configure GitHub Secrets

After deployment, run the generated script:

```bash
./set-github-secrets.sh
```

Add these secrets to your GitHub repository:
- `ACR_LOGIN_SERVER`
- `ACR_USERNAME`
- `ACR_PASSWORD`
- `AZURE_CREDENTIALS`
- `DB_PASSWORD`
- `REDIS_PASSWORD`
- `AZURE_OPENAI_API_KEY`

### 5. Deploy OpenAI Models

1. Go to Azure Portal → Your AI Services instance
2. Deploy these models:
   - `gpt-4` or `gpt-4-turbo` with deployment name: `escoffier-gpt4`
   - `gpt-3.5-turbo` with deployment name: `escoffier-gpt35`

### 6. Initialize Database

```bash
# Get the PostgreSQL connection string
POSTGRES_SERVER=$(cat deployment-config.json | jq -r '.postgresServer')

# Initialize the database
psql -h ${POSTGRES_SERVER}.postgres.database.azure.com \
     -U escoffieradmin@${POSTGRES_SERVER} \
     -d escoffier \
     -f ../init.sql
```

### 7. Deploy the Application

```bash
# Commit and push to trigger deployment
git add .
git commit -m "Deploy Escoffier to Azure"
git push origin main
```

## Cost Optimization Strategies

### 1. Frontend Optimization
- Static files served from Azure Storage (~$1/month)
- CDN for global distribution (~$9/month)
- No compute costs for frontend

### 2. Backend Optimization
- B1 App Service Plan (1.75 GB RAM, 1 vCPU)
- Auto-scaling 1-3 instances based on CPU
- Health checks to prevent cold starts

### 3. Database Optimization
- Burstable B1ms tier (1 vCore, 2 GB RAM)
- 32 GB storage (expandable)
- 7-day backup retention
- No high availability (can be enabled later)

### 4. Cache Optimization
- Redis C0 Basic (250 MB)
- LRU eviction policy
- No persistence (can be upgraded)

### 5. Monitoring Optimization
- 30-day log retention
- Basic alerting rules
- Budget alerts at 80% threshold

## Monitoring Dashboard

Access your monitoring dashboards:

1. **Application Insights**: 
   ```
   https://portal.azure.com/#resource/subscriptions/{subscription}/resourceGroups/rg-escoffier-prod/providers/Microsoft.Insights/components/appi-escoffier-production
   ```

2. **Grafana Dashboard**:
   - URL provided in deployment output
   - Default credentials: admin/admin

3. **Custom Workbook**:
   - Navigate to Application Insights → Workbooks
   - Open "Escoffier Monitoring Dashboard"

## Key Metrics to Monitor

1. **Performance**:
   - API response time (target: <200ms p95)
   - Order processing time (target: <5s)
   - Database query time (target: <50ms)

2. **Availability**:
   - Uptime (target: 99.9%)
   - Failed requests (target: <0.1%)
   - Health check status

3. **Cost**:
   - Daily spend (budget: ~$8/day)
   - Resource utilization
   - AI token usage

## Scaling Guidelines

### When to Scale Up

1. **App Service** (B1 → S1):
   - Consistent CPU >70%
   - Memory pressure
   - Need for more instances

2. **PostgreSQL** (B1ms → B2s):
   - CPU credits exhausted
   - Storage >80%
   - Query performance degraded

3. **Redis** (C0 → C1):
   - Memory usage >200MB
   - Eviction rate high
   - Need for persistence

### Auto-scaling Configuration

The deployment includes auto-scaling rules:
- Scale out: CPU >70% for 5 minutes
- Scale in: CPU <30% for 5 minutes
- Min instances: 1
- Max instances: 3

## Troubleshooting

### Common Issues

1. **Container fails to start**:
   ```bash
   az webapp log tail --name escoffier-app --resource-group rg-escoffier-prod
   ```

2. **Database connection errors**:
   - Check firewall rules
   - Verify SSL settings
   - Check connection string

3. **Redis connection issues**:
   - Verify access keys
   - Check SSL/TLS settings

4. **AI Service errors**:
   - Verify API keys
   - Check deployment names
   - Monitor rate limits

### Debug Commands

```bash
# View application logs
az webapp log stream --name escoffier-app --resource-group rg-escoffier-prod

# Check deployment status
az webapp deployment list --name escoffier-app --resource-group rg-escoffier-prod

# View container logs
az webapp log download --name escoffier-app --resource-group rg-escoffier-prod

# Test health endpoint
curl https://escoffier-app-production.azurewebsites.net/health
```

## Security Checklist

- [ ] Enable Azure AD authentication
- [ ] Configure network security groups
- [ ] Enable private endpoints (when scaling)
- [ ] Rotate secrets regularly
- [ ] Enable Azure Defender
- [ ] Configure backup policies
- [ ] Enable audit logging

## Next Steps

1. **Performance Testing**:
   ```bash
   # Run load tests
   artillery quick --count 100 --num 10 https://escoffier-app-production.azurewebsites.net/api/orders
   ```

2. **Enable CI/CD**:
   - Configure staging slots
   - Set up blue-green deployments
   - Add integration tests

3. **Optimize Costs Further**:
   - Use reserved instances (save ~40%)
   - Implement aggressive caching
   - Schedule scale-down during off-hours

4. **Enhance Monitoring**:
   - Custom metrics for business KPIs
   - Distributed tracing
   - Real user monitoring

## Support

For issues or questions:
1. Check Azure service health
2. Review Application Insights logs
3. Contact Azure support (if applicable)
4. Create GitHub issue for application bugs