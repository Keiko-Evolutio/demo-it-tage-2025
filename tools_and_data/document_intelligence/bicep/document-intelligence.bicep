// ============================================================================
// Azure AI Document Intelligence (Form Recognizer) - Workshop Stack
// ============================================================================
// Dieses Modul erstellt die komplette Infrastruktur für den Document Intelligence Workshop:
// - Azure AI Document Intelligence (Form Recognizer)
// - Storage Account + Blob Container (für Sample-Dokumente)
// ============================================================================

// ============================================================================
// PARAMETER
// ============================================================================

@description('Name der Umgebung (z.B. it-tage-2025)')
param environmentName string

@description('Azure Region für die Ressource')
param location string = resourceGroup().location

@description('SKU für Document Intelligence (F0=Free, S0=Standard)')
@allowed([
  'F0'
  'S0'
])
param documentIntelligenceSku string = 'S0'

@description('Storage Account SKU')
@allowed([
  'Standard_LRS'
  'Standard_GRS'
  'Standard_RAGRS'
  'Standard_ZRS'
])
param storageAccountSku string = 'Standard_LRS'

@description('Blob Container Name für Sample-Dokumente')
param blobContainerName string = 'sample-documents'

@description('Tags für alle Ressourcen')
param tags object = {
  purpose: 'workshop'
  event: 'IT-Tage-2025'
  environment: environmentName
  tool: 'document-intelligence'
}

// ============================================================================
// VARIABLEN
// ============================================================================

// Resource Names (müssen global eindeutig sein)
var documentIntelligenceName = 'doc-intel-doc-intelligence-${environmentName}'
var storageAccountName = 'stdocintel${replace(environmentName, '-', '')}' // Storage names: no hyphens, lowercase

// ============================================================================
// RESSOURCEN
// ============================================================================

// 1. Azure AI Document Intelligence (Form Recognizer)
resource documentIntelligence 'Microsoft.CognitiveServices/accounts@2023-05-01' = {
  name: documentIntelligenceName
  location: location
  kind: 'FormRecognizer'
  tags: tags
  sku: {
    name: documentIntelligenceSku
  }
  properties: {
    customSubDomainName: documentIntelligenceName
    publicNetworkAccess: 'Enabled'
    networkAcls: {
      defaultAction: 'Allow'
    }
  }
}

// 2. Storage Account für Sample-Dokumente
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageAccountName
  location: location
  tags: tags
  sku: {
    name: storageAccountSku
  }
  kind: 'StorageV2'
  properties: {
    accessTier: 'Hot'
    supportsHttpsTrafficOnly: true
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: true  // Required for Document Intelligence to access blobs via URL
    allowSharedKeyAccess: true
    networkAcls: {
      defaultAction: 'Allow'
      bypass: 'AzureServices'
    }
  }
}

// 3. Blob Service
resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  parent: storageAccount
  name: 'default'
  properties: {
    deleteRetentionPolicy: {
      enabled: true
      days: 7
    }
  }
}

// 4. Blob Container für Sample-Dokumente
resource blobContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: blobService
  name: blobContainerName
  properties: {
    publicAccess: 'Blob'  // Allow public read access to blobs (required for Document Intelligence)
  }
}

// ============================================================================
// OUTPUTS
// ============================================================================

@description('Name des Document Intelligence Service')
output documentIntelligenceName string = documentIntelligence.name

@description('Endpoint des Document Intelligence Service')
output documentIntelligenceEndpoint string = documentIntelligence.properties.endpoint

@description('API Key 1 des Document Intelligence Service')
output documentIntelligenceApiKey string = documentIntelligence.listKeys().key1

@description('API Key 2 des Document Intelligence Service')
output documentIntelligenceApiKey2 string = documentIntelligence.listKeys().key2

@description('Name des Storage Account')
output storageAccountName string = storageAccount.name

@description('Blob Endpoint des Storage Account')
output storageAccountBlobEndpoint string = storageAccount.properties.primaryEndpoints.blob

@description('Connection String des Storage Account')
output storageConnectionString string = 'DefaultEndpointsProtocol=https;AccountName=${storageAccount.name};AccountKey=${storageAccount.listKeys().keys[0].value};EndpointSuffix=${environment().suffixes.storage}'

@description('Name des Blob Containers')
output blobContainerName string = blobContainer.name

