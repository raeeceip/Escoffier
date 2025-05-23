param location string = resourceGroup().location
param appName string = 'escoffier'
param environment string

// Existing resources references
param logAnalyticsWorkspaceId string
param appInsightsName string
param webAppResourceId string
param postgresResourceId string
param redisResourceId string

// Azure Monitor Workspace
resource monitorWorkspace 'Microsoft.Monitor/accounts@2023-04-03' = {
  name: 'amw-${appName}-${environment}'
  location: location
}

// Grafana Instance
resource grafana 'Microsoft.Dashboard/grafana@2022-08-01' = {
  name: 'grafana-${appName}-${environment}'
  location: location
  sku: {
    name: 'Standard'
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    publicNetworkAccess: 'Enabled'
    grafanaIntegrations: {
      azureMonitorWorkspaceIntegrations: [
        {
          azureMonitorWorkspaceResourceId: monitorWorkspace.id
        }
      ]
    }
  }
}

// Data Collection Endpoint
resource dataCollectionEndpoint 'Microsoft.Insights/dataCollectionEndpoints@2022-06-01' = {
  name: 'dce-${appName}-${environment}'
  location: location
  properties: {
    networkAcls: {
      publicNetworkAccess: 'Enabled'
    }
  }
}

// Data Collection Rule for Prometheus metrics
resource prometheusDataCollectionRule 'Microsoft.Insights/dataCollectionRules@2022-06-01' = {
  name: 'dcr-prometheus-${appName}'
  location: location
  properties: {
    dataCollectionEndpointId: dataCollectionEndpoint.id
    destinations: {
      monitoringAccounts: [
        {
          accountResourceId: monitorWorkspace.id
          name: 'MonitoringAccount'
        }
      ]
    }
    dataFlows: [
      {
        destinations: ['MonitoringAccount']
        streams: ['Microsoft-PrometheusMetrics']
      }
    ]
  }
}

// Log Analytics queries for monitoring
resource customQueries 'Microsoft.OperationalInsights/savedSearches@2020-08-01' = [for query in monitoringQueries: {
  name: '${logAnalyticsWorkspaceId}/savedSearches/${query.name}'
  properties: {
    category: 'Escoffier Monitoring'
    displayName: query.displayName
    query: query.query
    version: 2
  }
}]

var monitoringQueries = [
  {
    name: 'escoffier-order-processing-time'
    displayName: 'Order Processing Time'
    query: '''
      AppMetrics
      | where Name == "order_processing_duration"
      | summarize avg(Sum), percentile(Sum, 95), percentile(Sum, 99) by bin(TimeGenerated, 5m)
      | render timechart
    '''
  }
  {
    name: 'escoffier-agent-performance'
    displayName: 'Agent Performance Metrics'
    query: '''
      AppMetrics
      | where Name contains "agent_"
      | summarize avg(Sum) by Name, bin(TimeGenerated, 5m)
      | render timechart
    '''
  }
  {
    name: 'escoffier-error-rate'
    displayName: 'Error Rate Analysis'
    query: '''
      AppExceptions
      | summarize ErrorCount = count() by ExceptionType, bin(TimeGenerated, 5m)
      | order by ErrorCount desc
    '''
  }
  {
    name: 'escoffier-api-latency'
    displayName: 'API Endpoint Latency'
    query: '''
      AppRequests
      | summarize percentile(DurationMs, 50), percentile(DurationMs, 95), percentile(DurationMs, 99) 
        by Name, bin(TimeGenerated, 5m)
      | where Name startswith "POST" or Name startswith "GET"
    '''
  }
]

// Workbook for comprehensive monitoring
resource monitoringWorkbook 'Microsoft.Insights/workbooks@2022-04-01' = {
  name: guid('workbook-${appName}-monitoring')
  location: location
  kind: 'shared'
  properties: {
    displayName: 'Escoffier Monitoring Dashboard'
    serializedData: string(loadJsonContent('monitoring-workbook.json'))
    sourceId: logAnalyticsWorkspaceId
    category: 'Escoffier'
  }
}

// Alert rules for comprehensive monitoring
resource alertRules 'Microsoft.Insights/scheduledQueryRules@2022-08-01-preview' = [for alert in alertConfigs: {
  name: 'alert-${alert.name}'
  location: location
  properties: {
    displayName: alert.displayName
    description: alert.description
    severity: alert.severity
    enabled: true
    evaluationFrequency: 'PT5M'
    windowSize: 'PT5M'
    criteria: {
      allOf: [
        {
          query: alert.query
          timeAggregation: 'Count'
          operator: alert.operator
          threshold: alert.threshold
          failingPeriods: {
            numberOfEvaluationPeriods: 1
            minFailingPeriodsToAlert: 1
          }
        }
      ]
    }
    scopes: [
      logAnalyticsWorkspaceId
    ]
    actions: {
      actionGroups: []
      customProperties: {
        service: 'escoffier'
        environment: environment
      }
    }
  }
}]

var alertConfigs = [
  {
    name: 'high-order-processing-time'
    displayName: 'High Order Processing Time'
    description: 'Order processing time exceeds threshold'
    severity: 2
    query: 'AppMetrics | where Name == "order_processing_duration" | where Sum > 300000'
    operator: 'GreaterThan'
    threshold: 10
  }
  {
    name: 'agent-failure-rate'
    displayName: 'High Agent Failure Rate'
    description: 'Agent failure rate is above acceptable threshold'
    severity: 1
    query: 'AppMetrics | where Name == "agent_failures" | summarize FailureRate = sum(Sum) by bin(TimeGenerated, 5m)'
    operator: 'GreaterThan'
    threshold: 5
  }
  {
    name: 'database-connection-pool'
    displayName: 'Database Connection Pool Exhaustion'
    description: 'Database connection pool is nearly exhausted'
    severity: 1
    query: 'AppMetrics | where Name == "db_connection_pool_usage" | where Sum > 0.9'
    operator: 'GreaterThan'
    threshold: 1
  }
]

// Diagnostic settings for all resources
resource webAppDiagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'diag-webapp-${appName}'
  scope: webApp
  properties: {
    workspaceId: logAnalyticsWorkspaceId
    logs: [
      {
        category: 'AppServiceHTTPLogs'
        enabled: true
      }
      {
        category: 'AppServiceConsoleLogs'
        enabled: true
      }
      {
        category: 'AppServiceAppLogs'
        enabled: true
      }
    ]
    metrics: [
      {
        category: 'AllMetrics'
        enabled: true
      }
    ]
  }
}

resource postgresDiagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'diag-postgres-${appName}'
  scope: postgres
  properties: {
    workspaceId: logAnalyticsWorkspaceId
    logs: [
      {
        category: 'PostgreSQLLogs'
        enabled: true
      }
    ]
    metrics: [
      {
        category: 'AllMetrics'
        enabled: true
      }
    ]
  }
}

resource redisDiagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'diag-redis-${appName}'
  scope: redis
  properties: {
    workspaceId: logAnalyticsWorkspaceId
    metrics: [
      {
        category: 'AllMetrics'
        enabled: true
      }
    ]
  }
}

// Existing resources for diagnostic settings
resource webApp 'Microsoft.Web/sites@2022-09-01' existing = {
  name: split(webAppResourceId, '/')[8]
}

resource postgres 'Microsoft.DBforPostgreSQL/flexibleServers@2022-12-01' existing = {
  name: split(postgresResourceId, '/')[8]
}

resource redis 'Microsoft.Cache/redis@2023-08-01' existing = {
  name: split(redisResourceId, '/')[8]
}

// Outputs
output grafanaUrl string = grafana.properties.endpoint
output monitorWorkspaceId string = monitorWorkspace.id
output dataCollectionRuleId string = prometheusDataCollectionRule.id