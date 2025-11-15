#!/bin/bash
# ============================================================================
# Deployment Script for Azure AI Search (Vector Database)
# ============================================================================
# This script deploys the Azure AI Search service using vector-search.bicep
# ============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ============================================================================
# Load environment variables
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/../../.env"

if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}Error: .env file not found at $ENV_FILE${NC}"
    exit 1
fi

# Load .env file
set -a
source "$ENV_FILE"
set +a

# ============================================================================
# Configuration
# ============================================================================

RESOURCE_GROUP="${AZURE_RESOURCE_GROUP}"
LOCATION="${AZURE_LOCATION}"
ENVIRONMENT_NAME="${ENVIRONMENT_NAME}"
BICEP_FILE="$SCRIPT_DIR/vector-search.bicep"

# Deployment parameters
SEARCH_SERVICE_SKU="standard"
REPLICA_COUNT=1
PARTITION_COUNT=1
SEMANTIC_SEARCH="free"
PUBLIC_NETWORK_ACCESS=true

# ============================================================================
# Validate configuration
# ============================================================================

if [ -z "$RESOURCE_GROUP" ]; then
    echo -e "${RED}Error: AZURE_RESOURCE_GROUP not set in .env${NC}"
    exit 1
fi

if [ -z "$LOCATION" ]; then
    echo -e "${RED}Error: AZURE_LOCATION not set in .env${NC}"
    exit 1
fi

if [ -z "$ENVIRONMENT_NAME" ]; then
    echo -e "${RED}Error: ENVIRONMENT_NAME not set in .env${NC}"
    exit 1
fi

if [ ! -f "$BICEP_FILE" ]; then
    echo -e "${RED}Error: Bicep file not found at $BICEP_FILE${NC}"
    exit 1
fi

# ============================================================================
# Display information
# ============================================================================

echo -e "${BLUE}============================================================================${NC}"
echo -e "${BLUE}Azure AI Search - Deployment${NC}"
echo -e "${BLUE}============================================================================${NC}"
echo ""
echo -e "${YELLOW}Configuration:${NC}"
echo -e "  Resource Group:    $RESOURCE_GROUP"
echo -e "  Location:          $LOCATION"
echo -e "  Environment:       $ENVIRONMENT_NAME"
echo -e "  Search SKU:        $SEARCH_SERVICE_SKU"
echo -e "  Replicas:          $REPLICA_COUNT"
echo -e "  Partitions:        $PARTITION_COUNT"
echo -e "  Semantic Search:   $SEMANTIC_SEARCH"
echo ""

# ============================================================================
# Check if Azure CLI is installed
# ============================================================================

if ! command -v az &> /dev/null; then
    echo -e "${RED}Error: Azure CLI is not installed${NC}"
    echo "Please install it from: https://docs.microsoft.com/cli/azure/install-azure-cli"
    exit 1
fi

# ============================================================================
# Check if logged in to Azure
# ============================================================================

echo -e "${BLUE}Checking Azure login status...${NC}"
if ! az account show &> /dev/null; then
    echo -e "${RED}Error: Not logged in to Azure${NC}"
    echo "Please run: az login"
    exit 1
fi

CURRENT_SUBSCRIPTION=$(az account show --query name -o tsv)
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
echo -e "${GREEN}Logged in to Azure${NC}"
echo -e "${YELLOW}Subscription:${NC} $CURRENT_SUBSCRIPTION"
echo -e "${YELLOW}Subscription ID:${NC} $SUBSCRIPTION_ID"
echo ""

# ============================================================================
# Create resource group if it doesn't exist
# ============================================================================

echo -e "${BLUE}Checking resource group...${NC}"
if ! az group show --name "$RESOURCE_GROUP" &> /dev/null; then
    echo -e "${YELLOW}Resource group does not exist. Creating...${NC}"
    az group create --name "$RESOURCE_GROUP" --location "$LOCATION"
    echo -e "${GREEN}✓ Resource group created${NC}"
else
    echo -e "${GREEN}✓ Resource group exists${NC}"
fi
echo ""

# ============================================================================
# Deploy Bicep template
# ============================================================================

echo -e "${BLUE}============================================================================${NC}"
echo -e "${BLUE}Deploying Azure AI Search service...${NC}"
echo -e "${BLUE}============================================================================${NC}"
echo ""

DEPLOYMENT_NAME="vector-search-$(date +%Y%m%d-%H%M%S)"

echo -e "${YELLOW}Deployment name:${NC} $DEPLOYMENT_NAME"
echo ""

# Deploy with parameters
az deployment group create \
    --name "$DEPLOYMENT_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --template-file "$BICEP_FILE" \
    --parameters \
        environmentName="$ENVIRONMENT_NAME" \
        location="$LOCATION" \
        searchServiceSku="$SEARCH_SERVICE_SKU" \
        replicaCount=$REPLICA_COUNT \
        partitionCount=$PARTITION_COUNT \
        semanticSearch="$SEMANTIC_SEARCH" \
        publicNetworkAccess=$PUBLIC_NETWORK_ACCESS

echo ""
echo -e "${GREEN}✓ Deployment completed${NC}"
echo ""

# ============================================================================
# Get deployment outputs
# ============================================================================

echo -e "${BLUE}Retrieving deployment outputs...${NC}"

SEARCH_SERVICE_NAME=$(az deployment group show \
    --name "$DEPLOYMENT_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query "properties.outputs.searchServiceName.value" \
    -o tsv)

SEARCH_ENDPOINT=$(az deployment group show \
    --name "$DEPLOYMENT_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query "properties.outputs.searchServiceEndpoint.value" \
    -o tsv)

SEARCH_ADMIN_KEY=$(az deployment group show \
    --name "$DEPLOYMENT_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query "properties.outputs.searchServiceAdminKey.value" \
    -o tsv)

SEARCH_QUERY_KEY=$(az deployment group show \
    --name "$DEPLOYMENT_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query "properties.outputs.searchServiceQueryKey.value" \
    -o tsv)

echo ""
echo -e "${GREEN}✓ Outputs retrieved${NC}"
echo ""

# ============================================================================
# Display results
# ============================================================================

echo -e "${GREEN}============================================================================${NC}"
echo -e "${GREEN}Deployment completed successfully!${NC}"
echo -e "${GREEN}============================================================================${NC}"
echo ""
echo -e "${YELLOW}Azure AI Search Service:${NC}"
echo -e "  Name:       $SEARCH_SERVICE_NAME"
echo -e "  Endpoint:   $SEARCH_ENDPOINT"
echo -e "  Admin Key:  ${SEARCH_ADMIN_KEY:0:20}..."
echo -e "  Query Key:  ${SEARCH_QUERY_KEY:0:20}..."
echo ""

# ============================================================================
# Update .env file
# ============================================================================

echo -e "${BLUE}Updating .env file...${NC}"

# Create backup
cp "$ENV_FILE" "$ENV_FILE.backup"

# Update or add environment variables
update_env_var() {
    local key=$1
    local value=$2
    
    if grep -q "^${key}=" "$ENV_FILE"; then
        # Update existing variable
        sed -i.tmp "s|^${key}=.*|${key}=\"${value}\"|" "$ENV_FILE"
        rm -f "$ENV_FILE.tmp"
    else
        # Add new variable
        echo "${key}=\"${value}\"" >> "$ENV_FILE"
    fi
}

update_env_var "VECTOR_DB_SERVICE_NAME" "$SEARCH_SERVICE_NAME"
update_env_var "VECTOR_DB_ENDPOINT" "$SEARCH_ENDPOINT"
update_env_var "VECTOR_DB_ADMIN_KEY" "$SEARCH_ADMIN_KEY"
update_env_var "VECTOR_DB_QUERY_KEY" "$SEARCH_QUERY_KEY"

echo -e "${GREEN}✓ .env file updated${NC}"
echo -e "${YELLOW}Backup saved to:${NC} $ENV_FILE.backup"
echo ""

# ============================================================================
# Next steps
# ============================================================================

echo -e "${YELLOW}Next steps:${NC}"
echo -e "  1. Upload documents to Blob Storage:"
echo -e "     ${BLUE}python tools_and_data/workshop_tools/azure_tools/blob_store/upload_sample_data.py${NC}"
echo ""
echo -e "  2. Run the notebook to create index and index documents:"
echo -e "     ${BLUE}tools_and_data/vector_db/examples/01_azure_ai_search_complete_guide.ipynb${NC}"
echo ""
echo -e "  3. To delete the search service:"
echo -e "     ${BLUE}./tools_and_data/vector_db/bicep/cleanup-vector-search.sh${NC}"
echo ""

