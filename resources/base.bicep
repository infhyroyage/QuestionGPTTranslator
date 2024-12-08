param azureAdEAContributorObjectId string
@secure()
param azureApimPublisherEmail string
@secure()
param deeplAuthKey string
param location string = resourceGroup().location
@secure()
param openAIApiKey string
param openAIApiVersion string
param openAIDeployment string
param openAIEndpoint string
param openAIModel string
@secure()
param translatorKey string

var apimApisName = 'apis-functions'
var apisHealthcheckName = 'apis-healthcheck-functions'
var apimLoggersName = 'loggers-insights'
var apimName = 'qgtranslator-je-apim'
var apimNamedValuesNames = {
  insightsInstrumentationKey: 'named-values-insights-instrumentation-key'
}
var apimOrgName = 'qgtranslator-je-apim-org'

var cosmosDBContainerNames = {
  answer: 'Answer'
  question: 'Question'
  test: 'Test'
}
var cosmosDBDatabaseNames = {
  users: 'Users'
}
var cosmosDBName = 'qgtranslator-je-cosmosdb'

var functionsPlanName = 'qgtranslator-je-funcplan'
var functionsName = 'qgtranslator-je-func'

var insightsName = 'qgtranslator-je-insights'

var lawName = 'qgtranslator-je-law'

var storageBlobContainerName = 'import-items'
var storageName = 'qgtranslatorjesa'
var storageQueueName = 'answers'

var vaultName = 'qgtranslator-je-vault'
var vaultSecretNames = {
  translatorKey: 'translator-key'
  cosmosDBPrimaryKey: 'cosmos-db-primary-key'
  cosmosDBPrimaryReadonlyKey: 'cosmos-db-primary-readonly-key'
  deeplAuthKey: 'deepl-auth-key'
  insightsConnectionString: 'insights-connection-string'
  insightsInstrumentationKey: 'insights-instrumentation-key'
  openAIApiKey: 'openai-api-key'
  openAIApiVersion: 'openai-api-version'
  openAIDeployment: 'openai-deployment'
  openAIEndpoint: 'openai-endpoint'
}

// API Management
resource apim 'Microsoft.ApiManagement/service@2022-08-01' = {
  name: apimName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  sku: {
    name: 'Consumption'
    capacity: 0
  }
  properties: {
    customProperties: {
      'Microsoft.WindowsAzure.ApiManagement.Gateway.Protocols.Server.Http2': 'false'
      'Microsoft.WindowsAzure.ApiManagement.Gateway.Security.Backend.Protocols.Ssl30': 'false'
      'Microsoft.WindowsAzure.ApiManagement.Gateway.Security.Backend.Protocols.Tls10': 'false'
      'Microsoft.WindowsAzure.ApiManagement.Gateway.Security.Backend.Protocols.Tls11': 'false'
      'Microsoft.WindowsAzure.ApiManagement.Gateway.Security.Protocols.Tls10': 'false'
      'Microsoft.WindowsAzure.ApiManagement.Gateway.Security.Protocols.Tls11': 'false'
    }
    publisherEmail: azureApimPublisherEmail
    publisherName: apimOrgName
  }
}
resource apimApis 'Microsoft.ApiManagement/service/apis@2022-08-01' = {
  parent: apim
  name: apimApisName
  properties: {
    apiRevision: '1'
    description: 'QuestionGPTPortalでのWebアプリケーションから実行するAPIリファレンスです'
    displayName: 'QuestionGPTPortalAPIs'
    isCurrent: true
    path: 'api'
    protocols: ['https']
    subscriptionRequired: false
  }
  dependsOn: [functions]
}
resource apimApisHealthcheck 'Microsoft.ApiManagement/service/apis@2022-08-01' = {
  parent: apim
  name: apisHealthcheckName
  properties: {
    apiRevision: '1'
    description: 'FunctionsのヘルスチェックAPIリファレンスです'
    displayName: 'HealthCheckAPIs'
    isCurrent: true
    path: ''
    protocols: ['https']
    subscriptionRequired: true
  }
  dependsOn: [functions]
}
resource apimNamedValuesInsightsInstrumentationKey 'Microsoft.ApiManagement/service/namedValues@2022-08-01' = {
  parent: apim
  name: apimNamedValuesNames.insightsInstrumentationKey
  properties: {
    displayName: apimNamedValuesNames.insightsInstrumentationKey
    keyVault: {
      secretIdentifier: vaultSecretsInsightsInstrumentationKey.properties.secretUri
    }
    secret: true
  }
}
resource apimLoggers 'Microsoft.ApiManagement/service/loggers@2022-08-01' = {
  parent: apim
  name: apimLoggersName
  properties: {
    credentials: {
      instrumentationKey: '{{${apimNamedValuesNames.insightsInstrumentationKey}}}'
    }
    loggerType: 'applicationInsights'
    resourceId: insights.id
  }
  dependsOn: [apimNamedValuesInsightsInstrumentationKey]
}
resource apimDiagnosticsInsights 'Microsoft.ApiManagement/service/diagnostics@2022-08-01' = {
  parent: apim
  name: 'applicationinsights'
  properties: {
    alwaysLog: 'allErrors'
    httpCorrelationProtocol: 'Legacy'
    logClientIp: true
    loggerId: apimLoggers.id
    sampling: {
      percentage: 100
      samplingType: 'fixed'
    }
  }
}

// Cosmos DB
resource cosmosDB 'Microsoft.DocumentDb/databaseAccounts@2023-04-15' = {
  kind: 'GlobalDocumentDB'
  name: cosmosDBName
  location: location
  properties: {
    backupPolicy: {
      periodicModeProperties: {
        backupIntervalInMinutes: 240
        backupRetentionIntervalInHours: 8
        backupStorageRedundancy: 'Local'
      }
      type: 'Periodic'
    }
    capabilities: [
      {
        name: 'EnableServerless'
      }
    ]
    capacity: {
      totalThroughputLimit: 4000
    }
    consistencyPolicy: {
      defaultConsistencyLevel: 'Eventual'
    }
    databaseAccountOfferType: 'Standard'
    enableFreeTier: false
    ipRules: []
    isVirtualNetworkFilterEnabled: false
    locations: [
      {
        failoverPriority: 0
        locationName: location
      }
    ]
    virtualNetworkRules: []
  }
  tags: {
    defaultExperience: 'false'
    'hidden-cosmos-mmspecial': ''
  }
}
resource cosmosDBDatabaseUsers 'Microsoft.DocumentDb/databaseAccounts/sqlDatabases@2023-04-15' = {
  parent: cosmosDB
  name: cosmosDBDatabaseNames.users
  properties: {
    resource: {
      id: cosmosDBDatabaseNames.users
    }
  }
}
resource cosmosDBDatabaseUsersContainerTest 'Microsoft.DocumentDb/databaseAccounts/sqlDatabases/containers@2023-04-15' = {
  parent: cosmosDBDatabaseUsers
  name: cosmosDBContainerNames.test
  properties: {
    resource: {
      id: cosmosDBContainerNames.test
      indexingPolicy: {
        compositeIndexes: [
          [
            {
              order: 'ascending'
              path: '/courseName'
            }
            {
              order: 'ascending'
              path: '/testName'
            }
          ]
        ]
      }
      partitionKey: {
        paths: ['/id']
      }
    }
  }
}
resource cosmosDBDatabaseUsersContainerQuestion 'Microsoft.DocumentDb/databaseAccounts/sqlDatabases/containers@2023-04-15' = {
  parent: cosmosDBDatabaseUsers
  name: cosmosDBContainerNames.question
  properties: {
    resource: {
      id: cosmosDBContainerNames.question
      partitionKey: {
        paths: ['/id']
      }
    }
  }
}
resource cosmosDBDatabaseUsersContainerAnswer 'Microsoft.DocumentDb/databaseAccounts/sqlDatabases/containers@2023-04-15' = {
  parent: cosmosDBDatabaseUsers
  name: cosmosDBContainerNames.answer
  properties: {
    resource: {
      id: cosmosDBContainerNames.answer
      partitionKey: {
        paths: ['/id']
      }
    }
  }
}

// Storage Account
resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageName
  location: location
  kind: 'StorageV2'
  sku: {
    name: 'Standard_LRS'
  }
  properties: {
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
  }
}
resource storageBlob 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  parent: storage
  name: 'default'
  properties: {
    cors: {
      corsRules: []
    }
    deleteRetentionPolicy: {
      allowPermanentDelete: false
      enabled: false
    }
  }
}
resource storageBlobContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: storageBlob
  name: storageBlobContainerName
  properties: {
    immutableStorageWithVersioning: {
      enabled: false
    }
    defaultEncryptionScope: '$account-encryption-key'
    denyEncryptionScopeOverride: false
    publicAccess: 'None'
  }
}
resource storageQueue 'Microsoft.Storage/storageAccounts/queueServices@2023-05-01' = {
  parent: storage
  name: 'default'
}
resource storageQueueQueue 'Microsoft.Storage/storageAccounts/queueServices/queues@2023-05-01' = {
  parent: storageQueue
  name: storageQueueName
}

// Log Analytics Workspaces
resource law 'Microsoft.OperationalInsights/workspaces@2021-06-01' = {
  name: lawName
  location: location
  properties: {
    sku: {
      name: 'pergb2018'
    }
  }
}

// Application Insights
resource insights 'microsoft.insights/components@2020-02-02' = {
  name: insightsName
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    Flow_Type: 'Bluefield'
    Request_Source: 'rest'
    WorkspaceResourceId: law.id
  }
}

// Functions
resource functionsPlan 'Microsoft.Web/serverfarms@2022-09-01' = {
  name: functionsPlanName
  location: location
  kind: 'linux'
  sku: {
    name: 'Y1'
    tier: 'Dynamic'
  }
  properties: {
    reserved: true
  }
}
resource functions 'Microsoft.Web/sites@2022-09-01' = {
  name: functionsName
  location: location
  tags: {
    'hidden-link: /app-insights-resource-id': insights.id
  }
  identity: {
    type: 'SystemAssigned'
  }
  kind: 'functionapp,linux'
  properties: {
    clientAffinityEnabled: false
    httpsOnly: true
    serverFarmId: functionsPlan.id
    siteConfig: {
      appSettings: [
        {
          name: 'AzureWebJobsStorage'
          value: 'DefaultEndpointsProtocol=https;AccountName=${storageName};AccountKey=${storage.listKeys().keys[0].value};EndpointSuffix=core.windows.net'
        }
        {
          name: 'COSMOSDB_URI'
          value: 'https://${cosmosDBName}.documents.azure.com:443'
        }
        {
          name: 'FUNCTIONS_EXTENSION_VERSION'
          value: '~4'
        }
        {
          name: 'FUNCTIONS_WORKER_RUNTIME'
          value: 'python'
        }
        {
          name: 'OPENAI_API_VERSION'
          value: openAIApiVersion
        }
        {
          name: 'OPENAI_DEPLOYMENT'
          value: openAIDeployment
        }
        {
          name: 'OPENAI_ENDPOINT'
          value: openAIEndpoint
        }
        {
          name: 'OPENAI_MODEL'
          value: openAIModel
        }
        {
          name: 'WEBSITE_ENABLE_SYNC_UPDATE_SITE'
          value: 'true'
        }
      ]
      cors: {
        allowedOrigins: ['https://portal.azure.com']
      }
      ftpsState: 'Disabled'
      linuxFxVersion: 'python|3.11'
      keyVaultReferenceIdentity: 'SystemAssigned'
      use32BitWorkerProcess: false
    }
  }
}

// Key Vault
resource vault 'Microsoft.KeyVault/vaults@2023-02-01' = {
  name: vaultName
  location: location
  properties: {
    accessPolicies: [
      {
        objectId: azureAdEAContributorObjectId
        tenantId: tenant().tenantId
        permissions: {
          keys: []
          secrets: ['Get', 'Set']
          certificates: []
        }
      }
      {
        objectId: apim.identity.principalId
        tenantId: tenant().tenantId
        permissions: {
          keys: []
          secrets: ['Get', 'list']
          certificates: []
        }
      }
      {
        objectId: functions.identity.principalId
        tenantId: tenant().tenantId
        permissions: {
          keys: []
          secrets: ['Get']
          certificates: []
        }
      }
    ]
    enabledForDeployment: false
    enabledForDiskEncryption: false
    enabledForTemplateDeployment: false
    enableRbacAuthorization: false
    enableSoftDelete: true
    networkAcls: {
      bypass: 'AzureServices'
      defaultAction: 'allow'
      ipRules: []
      virtualNetworkRules: []
    }
    publicNetworkAccess: 'Enabled'
    sku: {
      family: 'A'
      name: 'standard'
    }
    softDeleteRetentionInDays: 90
    tenantId: tenant().tenantId
  }
}
resource vaultSecretsCosmosDBPrimaryKey 'Microsoft.KeyVault/vaults/secrets@2023-02-01' = {
  parent: vault
  name: vaultSecretNames.cosmosDBPrimaryKey
  properties: {
    attributes: {
      enabled: true
    }
    value: cosmosDB.listKeys().primaryMasterKey
  }
}
resource vaultSecretsCosmosDBPrimaryReadonlyKey 'Microsoft.KeyVault/vaults/secrets@2023-02-01' = {
  parent: vault
  name: vaultSecretNames.cosmosDBPrimaryReadonlyKey
  properties: {
    attributes: {
      enabled: true
    }
    value: cosmosDB.listKeys().primaryReadonlyMasterKey
  }
}
resource vaultSecretsDeeplAuthKey 'Microsoft.KeyVault/vaults/secrets@2023-02-01' = {
  parent: vault
  name: vaultSecretNames.deeplAuthKey
  properties: {
    attributes: {
      enabled: true
    }
    value: deeplAuthKey
  }
}
resource vaultSecretsInsightsConnectionString 'Microsoft.KeyVault/vaults/secrets@2023-02-01' = {
  parent: vault
  name: vaultSecretNames.insightsConnectionString
  properties: {
    attributes: {
      enabled: true
    }
    value: insights.properties.ConnectionString
  }
}
resource vaultSecretsInsightsInstrumentationKey 'Microsoft.KeyVault/vaults/secrets@2023-02-01' = {
  parent: vault
  name: vaultSecretNames.insightsInstrumentationKey
  properties: {
    attributes: {
      enabled: true
    }
    value: insights.properties.InstrumentationKey
  }
}
resource vaultSecretsOpenAIApiKey 'Microsoft.KeyVault/vaults/secrets@2023-02-01' = {
  parent: vault
  name: vaultSecretNames.openAIApiKey
  properties: {
    attributes: {
      enabled: true
    }
    value: openAIApiKey
  }
}
resource vaultSecretsTranslatorKey 'Microsoft.KeyVault/vaults/secrets@2023-02-01' = {
  parent: vault
  name: vaultSecretNames.translatorKey
  properties: {
    attributes: {
      enabled: true
    }
    value: translatorKey
  }
}
