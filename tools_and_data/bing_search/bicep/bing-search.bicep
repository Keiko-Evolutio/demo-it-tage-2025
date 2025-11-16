// ============================================================================
// Azure AI Search (Bing Search Grounding) - Bicep Module
// ============================================================================
// Dieses Modul erstellt einen Azure AI Search Service für den Workshop.
// Der Service wird für Bing Grounding verwendet mit einem Agent verbunden.
// ============================================================================

// ============================================================================
// PARAMETER
// ============================================================================

@description('Name der Umgebung (z.B. it-tage-2025)')
param environmentName string

@description('Azure Region für die Ressource')
param location string = resourceGroup().location

@description('SKU für Grounding with Bing Search (G1)')
@allowed([ 'G1' ])
param bingGroundingSku string = 'G1'

@description('SKU für Azure AI Search (z.B. basic, standard, standard2, storage_optimized_l1)')
param searchSku string = 'basic'

@description('AOAI Modell/Deployment-ID für den Agenten (z.B. gpt-4o-mini)')
param agentModel string = 'gpt-4o'

@description('Name des Modell-Deployments im AI Services Account')
param openAiDeploymentName string = agentModel

@description('Name des Modells für das Deployment')
param openAiDeploymentModelName string = agentModel

@description('Publisher des Modells')
param openAiDeploymentModelPublisher string = 'OpenAI'

@description('Format des Modells')
@allowed([ 'OpenAI', 'Microsoft' ])
param openAiDeploymentModelFormat string = 'OpenAI'

@description('Version des Modells')
param openAiDeploymentModelVersion string = '2024-05-13'

@description('SKU für das Modell-Deployment')
param openAiDeploymentSku string = 'GlobalStandard'

@description('Kapazität des Modell-Deployments')
param openAiDeploymentCapacity int = 30

@description('Name des Agents')
param agentName string = 'agent-${environmentName}'

@description('Azure AI Search Indexname, den der Agent abfragt (muss existieren)')
param searchIndexName string = 'docs'

@description('Tags')
param tags object = {
  purpose: 'workshop'
  event: 'IT-Tage-2025'
  environment: environmentName
  tool: 'bing-grounding'
}

// ---------------------------
// Names
// ---------------------------
var bingGroundingName = 'bing-grounding-bing-search-${environmentName}'
var aiServicesName    = 'ai-services-bing-search-${environmentName}'
var aiProjectName     = 'ai-project-bing-search-${environmentName}'
var searchName        = 'ai-search-bing-search-${environmentName}'
var currentResourceGroupName = resourceGroup().name

// Connection Names
var connOpenAiName = 'conn-aiservices'
var connSearchName = 'conn-search'
var connBingName   = 'conn-bing-grounding'
var capabilityHostName = 'agents-host'

// ---------------------------
// Resources
// ---------------------------

// 1) Grounding with Bing Search (separates RP)
resource bingGrounding 'Microsoft.Bing/accounts@2020-06-10' = {
  name: bingGroundingName
  location: 'global'
  tags: tags
  sku: {
    name: bingGroundingSku
  }
  kind: 'Bing.Grounding'
  properties: {}
}

// 2) Azure AI Services (Foundry "Account" / Hub)
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

// 3) Azure AI Project (unterhalb AI Services)
resource aiProject 'Microsoft.CognitiveServices/accounts/projects@2025-10-01-preview' = {
  parent: aiServices
  name: aiProjectName
  location: location
  tags: tags
  identity: { type: 'SystemAssigned' }
  properties: {
    description: 'AI Project with Azure AI Search + Bing Grounding'
    displayName: 'Workshop Project'
  }
}

// 4) Modell-Deployment direkt im AI Services Account
resource aiModelDeployment 'Microsoft.CognitiveServices/accounts/deployments@2025-04-01-preview' = {
  parent: aiServices
  name: openAiDeploymentName
  sku: {
    name: openAiDeploymentSku
    capacity: openAiDeploymentCapacity
  }
  properties: {
    model: {
      name: openAiDeploymentModelName
      publisher: openAiDeploymentModelPublisher
      format: openAiDeploymentModelFormat
      version: openAiDeploymentModelVersion
    }
  }
}

// 5) Azure AI Search (Cognitive Search)
resource search 'Microsoft.Search/searchServices@2025-05-01' = {
  name: searchName
  location: location
  sku: { name: toLower(searchSku) }
  properties: {
    authOptions: { apiKeyOnly: {} }
    replicaCount: 1
    partitionCount: 1
    semanticSearch: 'free'
    disableLocalAuth: false
    publicNetworkAccess: 'enabled'
  }
  tags: tags
}

// 6) Connections im Project
// 6a) AI Services (Modelle im gleichen Account) via ApiKey
resource connOpenAi 'Microsoft.CognitiveServices/accounts/projects/connections@2025-10-01-preview' = {
  parent: aiProject
  name: connOpenAiName
  properties: {
    category: 'AIServices'
    // Endpoint des AI Services Accounts (Foundry)
    target: aiServices.properties.endpoint
    authType: 'ApiKey'
    metadata: {
      ApiType: 'azure'
      ResourceId: aiServices.id
    }
    credentials: {
      key: aiServices.listKeys().key1
    }
  }
}

// 6b) Cognitive Search via AccountKey
resource connSearch 'Microsoft.CognitiveServices/accounts/projects/connections@2025-10-01-preview' = {
  parent: aiProject
  name: connSearchName
  properties: {
    category: 'CognitiveSearch'
    target: search.properties.endpoint
    authType: 'ApiKey'
    metadata: {
      ApiType: 'azure'
      ResourceId: search.id
    }
    credentials: {
      key: search.listAdminKeys().primaryKey
    }
  }
}

// 6c) Grounding with Bing Search via ApiKey
resource connBing 'Microsoft.CognitiveServices/accounts/projects/connections@2025-10-01-preview' = {
  parent: aiProject
  name: connBingName
  properties: {
    category: 'GroundingWithBingSearch'
    // Verwende das öffentliche Bing Grounding Endpoint
    target: bingGrounding.properties.endpoint
    authType: 'ApiKey'
    credentials: {
      key: bingGrounding.listKeys().key1
    }
  }
}

// 7a) Capability Host auf Account-Ebene
resource capabilityHostAccount 'Microsoft.CognitiveServices/accounts/capabilityHosts@2025-10-01-preview' = {
  parent: aiServices
  name: capabilityHostName
  properties: {
    capabilityHostKind: 'Agents'
    aiServicesConnections: [
      connOpenAi.name
    ]
  }
  dependsOn: [
    aiModelDeployment
  ]
}

// 7b) Capability Host auf Projektebene – Standard Setup, verwendet eigene Ressourcen
resource capabilityHost 'Microsoft.CognitiveServices/accounts/projects/capabilityHosts@2025-10-01-preview' = {
  parent: aiProject
  name: capabilityHostName
  properties: {
    capabilityHostKind: 'Agents'
    aiServicesConnections: [
      connOpenAi.name
    ]
    // Optional: BYO Storage / Vektorspeicher:
    // threadStorageConnections: [ 'conn-storage' ]
    // storageConnections: [ 'conn-storage' ]
  }
  dependsOn: [
    capabilityHostAccount
    aiModelDeployment
  ]
}

// 8) Verwaltete Identität + Rollenzuweisung für das Deployment Script
resource createAgentIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: 'identity-create-agent-${environmentName}'
  location: location
  tags: tags
}

resource createAgentRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: aiProject
  name: guid(aiProject.id, 'create-agent-mi-role')
  properties: {
    principalId: createAgentIdentity.properties.principalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '25fbc0a9-bd7c-42a3-aa1a-3b75d497ee68')
    principalType: 'ServicePrincipal'
  }
}

resource createAgentDataRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: aiProject
  name: guid(aiProject.id, 'create-agent-ai-developer-role')
  properties: {
    principalId: createAgentIdentity.properties.principalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '64702f94-c441-49e6-a78b-ef80e0188fee')
    principalType: 'ServicePrincipal'
  }
}

resource createAgentManagerRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: aiProject
  name: guid(aiProject.id, 'create-agent-project-manager-role')
  properties: {
    principalId: createAgentIdentity.properties.principalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'eadc314b-1a2d-4efa-be10-5d325db5065e')
    principalType: 'ServicePrincipal'
  }
}

// 9) Erzeuge den Agent per Deployment Script (Agents-API v1)
resource createAgent 'Microsoft.Resources/deploymentScripts@2023-08-01' = {
  name: 'create-agent-${environmentName}'
  location: location
  kind: 'AzureCLI'
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${createAgentIdentity.id}': {}
    }
  }
  properties: {
    azCliVersion: '2.61.0'
    timeout: 'PT30M'
    retentionInterval: 'P1D'
    environmentVariables: [
      { name: 'PROJECT_ENDPOINT', value: 'https://${aiServices.name}.services.ai.azure.com/api/projects/${aiProject.name}' }
      { name: 'AGENT_MODEL', value: agentModel }
      { name: 'AGENT_NAME', value: agentName }
      { name: 'SEARCH_CONN_ID', value: '/subscriptions/${subscription().subscriptionId}/resourceGroups/${currentResourceGroupName}/providers/Microsoft.CognitiveServices/accounts/${aiServices.name}/projects/${aiProject.name}/connections/${connSearch.name}' }
      { name: 'BING_CONN_ID', value: '/subscriptions/${subscription().subscriptionId}/resourceGroups/${currentResourceGroupName}/providers/Microsoft.CognitiveServices/accounts/${aiServices.name}/projects/${aiProject.name}/connections/${connBing.name}' }
      { name: 'SEARCH_INDEX', value: searchIndexName }
    ]
    scriptContent: '''
      set -euo pipefail

      token=$(az account get-access-token --resource https://ai.azure.com --query accessToken -o tsv)

      payload=$(cat <<JSON
      {
        "model": "${AGENT_MODEL}",
        "name": "${AGENT_NAME}",
        "instructions": "Nutze Azure AI Search für interne Inhalte (Index ${SEARCH_INDEX}) und Bing Grounding für aktuelles Webwissen. Antworte mit Quellenhinweisen.",
        "tools": [
          { "type": "azure_ai_search" },
          {
            "type": "bing_grounding",
            "bing_grounding": {
              "search_configurations": [
                {
                  "connection_id": "${BING_CONN_ID}"
                }
              ]
            }
          }
        ],
        "tool_resources": {
          "azure_ai_search": {
            "indexes": [
              {
                "index_connection_id": "${SEARCH_CONN_ID}",
                "index_name": "${SEARCH_INDEX}",
                "query_type": "semantic"
              }
            ]
          }
        }
      }
JSON
)

      rsp=$(az rest --method post --url "$PROJECT_ENDPOINT/assistants?api-version=v1" \
        --headers Authorization="Bearer $token" Content-Type=application/json \
        --body "$payload")

      # Outputs für Bicep
      printf '{"agent": %s}' "$rsp" > "$AZ_SCRIPTS_OUTPUT_PATH"
    '''
  }
  dependsOn: [
    capabilityHost
    createAgentRole
    createAgentDataRole
    createAgentManagerRole
    aiModelDeployment
  ]
}

// ---------------------------
// Outputs
// ---------------------------
output resourceGroupName string = currentResourceGroupName
output bingGroundingId string = bingGrounding.id
output aiServicesEndpoint string = 'https://${aiServices.name}.services.ai.azure.com'
output aiProjectEndpoint string = 'https://${aiServices.name}.services.ai.azure.com/api/projects/${aiProject.name}'
output openAiAccountId string = aiServices.id
output aiSearchEndpoint string = 'https://${search.name}.search.windows.net'
output connectionIds object = {
  openAi: connOpenAi.id
  search: connSearch.id
  bing: connBing.id
}
output agent object = createAgent.properties.outputs.agent
