// ============================================================================
// Azure AI Search (Vector Database) - Complete Workshop Stack
// ============================================================================
// Dieses Modul erstellt die komplette Infrastruktur für den Vector DB Workshop:
// - Azure AI Services (für OpenAI Embeddings + Chat)
// - Embedding Model Deployment (text-embedding-3-small)
// - Chat Model Deployment (gpt-4o-mini)
// - Azure AI Search (Vector Database)
// - Storage Account + Blob Container (für Dokumente)
// - AI Project + Connections (für Azure AI Foundry)
// ============================================================================

// ============================================================================
// PARAMETER
// ============================================================================

@description('Name der Umgebung (z.B. it-tage-2025)')
param environmentName string

@description('Azure Region für die Ressource')
param location string = resourceGroup().location

@description('SKU des Search Service (basic, standard, standard2, standard3)')
@allowed([
  'basic'
  'standard'
  'standard2'
  'standard3'
  'storage_optimized_l1'
  'storage_optimized_l2'
])
param searchServiceSku string = 'standard'

@description('Semantic Search aktivieren (disabled, free, standard)')
@allowed([
  'disabled'
  'free'
  'standard'
])
param semanticSearch string = 'free'

@description('Embedding Model Name')
param embeddingModelName string = 'text-embedding-3-small'

@description('Embedding Model Version')
param embeddingModelVersion string = '1'

@description('Embedding Deployment Capacity (TPM in thousands)')
param embeddingDeploymentCapacity int = 120

@description('Chat Model Name')
param chatModelName string = 'gpt-4o-mini'

@description('Chat Model Version')
param chatModelVersion string = '2024-07-18'

@description('Chat Deployment Capacity (TPM in thousands)')
param chatDeploymentCapacity int = 30

@description('Storage Account SKU')
@allowed([
  'Standard_LRS'
  'Standard_GRS'
  'Standard_RAGRS'
  'Standard_ZRS'
])
param storageAccountSku string = 'Standard_LRS'

@description('Blob Container Name für Workshop-Dokumente')
param blobContainerName string = 'workshop-documents'

@description('Index Name für Vector Search')
param searchIndexName string = 'workshop-documents'

@description('Tags für alle Ressourcen')
param tags object = {
  purpose: 'workshop'
  event: 'IT-Tage-2025'
  environment: environmentName
  tool: 'vector-database'
}

// ============================================================================
// VARIABLEN
// ============================================================================

// Resource Names (müssen global eindeutig sein)
var aiServicesName = 'ai-services-vector-db-${environmentName}'
var aiProjectName = 'ai-project-vector-db-${environmentName}'
var searchServiceName = 'search-vector-db-${environmentName}'
var storageAccountName = 'stvectordb${replace(environmentName, '-', '')}' // Storage names: no hyphens, lowercase
var embeddingDeploymentName = embeddingModelName
var chatDeploymentName = chatModelName

// Connection Names
var connOpenAiName = 'conn-openai'
var connSearchName = 'conn-search'
var connStorageName = 'conn-storage'

// ============================================================================
// RESSOURCEN
// ============================================================================

// 1) Azure AI Services (für OpenAI Embeddings + Chat)
resource aiServices 'Microsoft.CognitiveServices/accounts@2025-04-01-preview' = {
  name: aiServicesName
  location: location
  kind: 'AIServices'
  tags: tags
  sku: { name: 'S0' }
  identity: { type: 'SystemAssigned' }
  properties: {
    customSubDomainName: aiServicesName
    publicNetworkAccess: 'Enabled'
    disableLocalAuth: false
    allowProjectManagement: true
  }
}

// 2) Embedding Model Deployment
resource embeddingDeployment 'Microsoft.CognitiveServices/accounts/deployments@2025-04-01-preview' = {
  parent: aiServices
  name: embeddingDeploymentName
  sku: {
    name: 'GlobalStandard'
    capacity: embeddingDeploymentCapacity
  }
  properties: {
    model: {
      name: embeddingModelName
      publisher: 'OpenAI'
      format: 'OpenAI'
      version: embeddingModelVersion
    }
  }
}

// 3) Chat Model Deployment
resource chatDeployment 'Microsoft.CognitiveServices/accounts/deployments@2025-04-01-preview' = {
  parent: aiServices
  name: chatDeploymentName
  sku: {
    name: 'GlobalStandard'
    capacity: chatDeploymentCapacity
  }
  properties: {
    model: {
      name: chatModelName
      publisher: 'OpenAI'
      format: 'OpenAI'
      version: chatModelVersion
    }
  }
  dependsOn: [
    embeddingDeployment  // Ensure sequential deployment
  ]
}

// 4) Azure AI Search Service (Vector Database)
resource searchService 'Microsoft.Search/searchServices@2024-06-01-preview' = {
  name: searchServiceName
  location: location
  tags: tags
  identity: { type: 'SystemAssigned' }
  sku: { name: searchServiceSku }
  properties: {
    replicaCount: 1
    partitionCount: 1
    hostingMode: 'default'
    publicNetworkAccess: 'enabled'
    semanticSearch: semanticSearch
    authOptions: { apiKeyOnly: {} }
    disableLocalAuth: false
  }
}

// 5) Storage Account (für Dokumente)
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageAccountName
  location: location
  tags: tags
  kind: 'StorageV2'
  sku: { name: storageAccountSku }
  identity: { type: 'SystemAssigned' }
  properties: {
    accessTier: 'Hot'
    allowBlobPublicAccess: false
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
    publicNetworkAccess: 'Enabled'
  }
}

// 6) Blob Container für Workshop-Dokumente
resource blobContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  name: '${storageAccount.name}/default/${blobContainerName}'
  properties: {
    publicAccess: 'None'
  }
}

// 7) AI Project (für Azure AI Foundry)
resource aiProject 'Microsoft.CognitiveServices/accounts/projects@2025-10-01-preview' = {
  parent: aiServices
  name: aiProjectName
  location: location
  tags: tags
  identity: { type: 'SystemAssigned' }
  properties: {
    description: 'Vector Database Workshop Project'
    displayName: 'Vector DB Workshop'
  }
}

// 8) Connection: OpenAI (AI Services)
resource connOpenAi 'Microsoft.CognitiveServices/accounts/projects/connections@2025-10-01-preview' = {
  parent: aiProject
  name: connOpenAiName
  properties: {
    category: 'AIServices'
    target: aiServices.properties.endpoint
    authType: 'ApiKey'
    isSharedToAll: true
    credentials: {
      key: aiServices.listKeys().key1
    }
    metadata: {
      ApiVersion: '2024-02-15-preview'
      ApiType: 'Azure'
      ResourceId: aiServices.id
    }
  }
}

// 9) Connection: Azure AI Search
resource connSearch 'Microsoft.CognitiveServices/accounts/projects/connections@2025-10-01-preview' = {
  parent: aiProject
  name: connSearchName
  properties: {
    category: 'CognitiveSearch'
    target: 'https://${searchService.name}.search.windows.net/'
    authType: 'ApiKey'
    isSharedToAll: true
    credentials: {
      key: searchService.listAdminKeys().primaryKey
    }
    metadata: {
      ApiVersion: '2024-07-01'
      ResourceId: searchService.id
    }
  }
}

// 10) Connection: Storage Account
resource connStorage 'Microsoft.CognitiveServices/accounts/projects/connections@2025-10-01-preview' = {
  parent: aiProject
  name: connStorageName
  properties: {
    category: 'AzureBlob'
    target: storageAccount.properties.primaryEndpoints.blob
    authType: 'ApiKey'
    isSharedToAll: true
    credentials: {
      key: storageAccount.listKeys().keys[0].value
    }
    metadata: {
      AccountName: storageAccount.name
      ResourceId: storageAccount.id
      ContainerName: blobContainerName
    }
  }
}

// ============================================================================
// OUTPUTS
// ============================================================================

// AI Services (OpenAI) Outputs
@description('AI Services Endpoint (Azure OpenAI)')
output aiServicesEndpoint string = aiServices.properties.endpoint

@description('AI Services API Key')
#disable-next-line outputs-should-not-contain-secrets
output aiServicesApiKey string = aiServices.listKeys().key1

@description('AI Services Name')
output aiServicesName string = aiServices.name

@description('Embedding Deployment Name')
output embeddingDeploymentName string = embeddingDeployment.name

@description('Embedding Model Name')
output embeddingModelName string = embeddingModelName

@description('Chat Deployment Name')
output chatDeploymentName string = chatDeployment.name

@description('Chat Model Name')
output chatModelName string = chatModelName

// Azure AI Search Outputs
@description('Search Service Name')
output searchServiceName string = searchService.name

@description('Search Service Endpoint')
output searchServiceEndpoint string = 'https://${searchService.name}.search.windows.net/'

@description('Search Service Admin Key')
#disable-next-line outputs-should-not-contain-secrets
output searchServiceAdminKey string = searchService.listAdminKeys().primaryKey

@description('Search Service Query Key')
#disable-next-line outputs-should-not-contain-secrets
output searchServiceQueryKey string = searchService.listQueryKeys().value[0].key

@description('Search Index Name')
output searchIndexName string = searchIndexName

// Storage Account Outputs
@description('Storage Account Name')
output storageAccountName string = storageAccount.name

@description('Storage Account Blob Endpoint')
output storageAccountBlobEndpoint string = storageAccount.properties.primaryEndpoints.blob

@description('Storage Account Connection String')
#disable-next-line outputs-should-not-contain-secrets
output storageConnectionString string = 'DefaultEndpointsProtocol=https;AccountName=${storageAccount.name};AccountKey=${storageAccount.listKeys().keys[0].value};EndpointSuffix=core.windows.net'

@description('Blob Container Name')
output blobContainerName string = blobContainerName

// AI Project Outputs
@description('AI Project Name')
output aiProjectName string = aiProject.name

@description('AI Project Endpoint')
output aiProjectEndpoint string = 'https://${aiServices.properties.endpoint}/projects/${aiProject.name}'

// ============================================================================
// HINWEISE FÜR WORKSHOP-TEILNEHMER
// ============================================================================
//
// ERSTELLTE RESSOURCEN:
//
// 1. Azure AI Services (OpenAI)
//    - Endpoint: {aiServicesEndpoint}
//    - Embedding Model: {embeddingModelName}
//    - Deployment: {embeddingDeploymentName}
//    - Verwendung: Generierung von Embeddings für Vector Search
//
// 2. Azure AI Search (Vector Database)
//    - Endpoint: {searchServiceEndpoint}
//    - SKU: {searchServiceSku}
//    - Semantic Search: {semanticSearch}
//    - Verwendung: Vector Search, Hybrid Search, Semantic Search
//
// 3. Storage Account + Blob Container
//    - Account: {storageAccountName}
//    - Container: {blobContainerName}
//    - Verwendung: Speicherung von Workshop-Dokumenten
//
// 4. AI Project + Connections
//    - Project: {aiProjectName}
//    - Connections: OpenAI, Search, Storage
//    - Verwendung: Azure AI Foundry Integration
//
// KOSTEN (Schätzung):
//    - AI Services S0: ~0.40€/1000 Tokens (Embeddings)
//    - Search Standard: ~230€/Monat
//    - Storage LRS: ~0.02€/GB/Monat
//    - Semantic Search (Free): 1000 Queries/Monat kostenlos
//
// NÄCHSTE SCHRITTE:
//    1. Dokumente hochladen: python tools_and_data/workshop_tools/azure_tools/blob_store/upload_sample_data.py
//    2. Pipeline erstellen: Siehe Notebook 01_azure_ai_search_complete_guide.ipynb
//    3. Vector Search testen: Siehe Notebook examples
//
// WICHTIGE ENVIRONMENT VARIABLEN (werden automatisch gesetzt):
//    - AZURE_OPENAI_ENDPOINT
//    - AZURE_OPENAI_API_KEY
//    - AZURE_OPENAI_EMBEDDING_DEPLOYMENT
//    - VECTOR_DB_ENDPOINT
//    - VECTOR_DB_ADMIN_KEY
//    - FILE_STORAGE_CONNECTION_STRING
//    - FILE_STORAGE_CONTAINER_NAME
//
// ============================================================================

