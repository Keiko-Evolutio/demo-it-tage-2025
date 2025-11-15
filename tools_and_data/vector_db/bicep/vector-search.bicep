// ============================================================================
// Azure AI Search (Vector Database) - Bicep Module
// ============================================================================
// Dieses Modul erstellt einen Azure AI Search Service für den Workshop.
// Der Service wird für Vector Search, Hybrid Search und Semantic Search verwendet.
// ============================================================================

// ============================================================================
// PARAMETER
// ============================================================================

@description('Name der Umgebung (z.B. it-tage-2025)')
param environmentName string

@description('Azure Region für die Ressource')
param location string = resourceGroup().location

@description('SKU des Search Service (Basic, Standard, Standard2, Standard3, Storage_Optimized_L1, Storage_Optimized_L2)')
@allowed([
  'basic'
  'standard'
  'standard2'
  'standard3'
  'storage_optimized_l1'
  'storage_optimized_l2'
])
param searchServiceSku string = 'standard'

@description('Anzahl der Replicas (1-12, abhängig von SKU)')
@minValue(1)
@maxValue(12)
param replicaCount int = 1

@description('Anzahl der Partitions (1-12, abhängig von SKU)')
@minValue(1)
@maxValue(12)
param partitionCount int = 1

@description('Semantic Search aktivieren (free, standard)')
@allowed([
  'disabled'
  'free'
  'standard'
])
param semanticSearch string = 'free'

@description('Public Network Access aktivieren')
param publicNetworkAccess bool = true

@description('Tags für die Ressource')
param tags object = {
  purpose: 'workshop'
  event: 'IT-Tage-2025'
  environment: environmentName
  tool: 'vector-database'
}

// ============================================================================
// VARIABLEN
// ============================================================================

// Search Service Name (muss global eindeutig sein)
var searchServiceName = 'search-workshop-${environmentName}'

// Managed Identity für sichere Authentifizierung
var searchIdentityProvider = {
  type: 'SystemAssigned'
}

// ============================================================================
// RESSOURCEN
// ============================================================================

// Azure AI Search Service
resource searchService 'Microsoft.Search/searchServices@2024-06-01-preview' = {
  name: searchServiceName
  location: location
  tags: tags
  
  // Managed Identity aktivieren
  identity: searchIdentityProvider
  
  // SKU und Kapazität
  sku: {
    name: searchServiceSku
  }
  
  properties: {
    // Replicas für Hochverfügbarkeit und Load Balancing
    replicaCount: replicaCount
    
    // Partitions für Skalierung der Datenmenge
    partitionCount: partitionCount
    
    // Hosting Mode (default = Standard)
    hostingMode: 'default'
    
    // Public Network Access
    publicNetworkAccess: publicNetworkAccess ? 'enabled' : 'disabled'
    
    // Semantic Search Konfiguration
    // Free Tier: 1000 Queries/Monat kostenlos
    // Standard Tier: Unbegrenzt, aber kostenpflichtig
    semanticSearch: semanticSearch
    
    // Authentifizierung
    // Sowohl API Keys als auch RBAC werden unterstützt
    authOptions: {
      // API Key Authentication aktivieren (für einfachen Zugriff)
      apiKeyOnly: {}
    }
    
    // Disable Local Auth = false bedeutet API Keys sind aktiviert
    // Für Workshop: API Keys + RBAC (Hybrid-Ansatz)
    disableLocalAuth: false
    
    // Network Rules (optional, für erweiterte Sicherheit)
    // networkRuleSet: {
    //   ipRules: []
    // }
  }
}

// ============================================================================
// OUTPUTS
// ============================================================================

@description('Name des Search Service')
output searchServiceName string = searchService.name

@description('Resource ID des Search Service')
output searchServiceId string = searchService.id

@description('Endpoint des Search Service')
output searchServiceEndpoint string = 'https://${searchService.name}.search.windows.net/'

@description('Admin Key des Search Service (für Management-Operationen)')
#disable-next-line outputs-should-not-contain-secrets
output searchServiceAdminKey string = searchService.listAdminKeys().primaryKey

@description('Query Key des Search Service (für Read-Only Operationen)')
#disable-next-line outputs-should-not-contain-secrets
output searchServiceQueryKey string = searchService.listQueryKeys().value[0].key

@description('Principal ID der Managed Identity')
output searchServicePrincipalId string = searchService.identity.principalId

@description('Tenant ID der Managed Identity')
output searchServiceTenantId string = searchService.identity.tenantId

// ============================================================================
// HINWEISE FÜR STUDENTEN
// ============================================================================
// 
// 1. KOSTEN:
//    - Basic SKU: ~70€/Monat
//    - Standard SKU: ~230€/Monat (empfohlen für Workshop)
//    - Semantic Search (Free): Kostenlos (1000 Queries/Monat)
//
// 2. KAPAZITÄT:
//    - Replicas: Erhöhen die Verfügbarkeit und Query-Performance
//    - Partitions: Erhöhen die Speicherkapazität und Indexing-Performance
//    - Standard SKU: Bis zu 25 GB pro Partition
//
// 3. RATE LIMITS:
//    - Basic: 3 Queries/Sekunde pro Replica
//    - Standard: 15 Queries/Sekunde pro Replica
//    - Indexing: 180 Dokumente/Sekunde (Standard)
//
// 4. AUTHENTIFIZIERUNG:
//    - API Keys: Einfach, aber weniger sicher
//    - RBAC (Managed Identity): Sicherer, empfohlen für Produktion
//    - Hybrid: Beide Methoden aktiviert (für Workshop)
//
// 5. SEMANTIC SEARCH:
//    - Free Tier: 1000 Queries/Monat kostenlos
//    - Verbessert Relevanz durch KI-basiertes Ranking
//    - Automatische Zusammenfassungen (Captions)
//    - Hervorhebung relevanter Passagen (Highlights)
//
// 6. NÄCHSTE SCHRITTE:
//    - Index erstellen (automatisch beim ersten Upload)
//    - Dokumente hochladen (siehe Notebook 02_upload_documents.ipynb)
//    - Suchen durchführen (siehe Notebook 03_vector_search.ipynb)
//    - RBAC-Rollen zuweisen (siehe assign-rbac-roles.sh)
//
// ============================================================================

