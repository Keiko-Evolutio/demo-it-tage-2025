#!/bin/bash
# ============================================================================
# Cleanup Script for Azure AI Search (Vector Database)
# ============================================================================
# This script deletes the Azure AI Search service created by vector-search.bicep
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
ENVIRONMENT_NAME="${ENVIRONMENT_NAME}"
SEARCH_SERVICE_NAME="search-workshop-${ENVIRONMENT_NAME}"

# ============================================================================
# Validate configuration
# ============================================================================

if [ -z "$RESOURCE_GROUP" ]; then
    echo -e "${RED}Error: AZURE_RESOURCE_GROUP not set in .env${NC}"
    exit 1
fi

if [ -z "$ENVIRONMENT_NAME" ]; then
    echo -e "${RED}Error: ENVIRONMENT_NAME not set in .env${NC}"
    exit 1
fi

# ============================================================================
# Display information
# ============================================================================

echo -e "${BLUE}============================================================================${NC}"
echo -e "${BLUE}Azure AI Search - Cleanup${NC}"
echo -e "${BLUE}============================================================================${NC}"
echo ""
echo -e "${YELLOW}Resource Group:${NC}    $RESOURCE_GROUP"
echo -e "${YELLOW}Search Service:${NC}    $SEARCH_SERVICE_NAME"
echo -e "${YELLOW}Environment:${NC}       $ENVIRONMENT_NAME"
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
echo -e "${GREEN}Logged in to Azure${NC}"
echo -e "${YELLOW}Current subscription:${NC} $CURRENT_SUBSCRIPTION"
echo ""

# ============================================================================
# Check if resource group exists
# ============================================================================

echo -e "${BLUE}Checking if resource group exists...${NC}"
if ! az group show --name "$RESOURCE_GROUP" &> /dev/null; then
    echo -e "${YELLOW}Resource group '$RESOURCE_GROUP' does not exist${NC}"
    echo -e "${GREEN}Nothing to clean up!${NC}"
    exit 0
fi

echo -e "${GREEN}Resource group exists${NC}"
echo ""

# ============================================================================
# Check if search service exists
# ============================================================================

echo -e "${BLUE}Checking if search service exists...${NC}"
if ! az search service show --name "$SEARCH_SERVICE_NAME" --resource-group "$RESOURCE_GROUP" &> /dev/null; then
    echo -e "${YELLOW}Search service '$SEARCH_SERVICE_NAME' does not exist${NC}"
    echo -e "${GREEN}Nothing to clean up!${NC}"
    exit 0
fi

echo -e "${GREEN}Search service exists${NC}"
echo ""

# Get search service details
SEARCH_ENDPOINT=$(az search service show --name "$SEARCH_SERVICE_NAME" --resource-group "$RESOURCE_GROUP" --query "properties.hostName" -o tsv)
SEARCH_SKU=$(az search service show --name "$SEARCH_SERVICE_NAME" --resource-group "$RESOURCE_GROUP" --query "sku.name" -o tsv)

echo -e "${YELLOW}Search Service Details:${NC}"
echo -e "  Name:     $SEARCH_SERVICE_NAME"
echo -e "  Endpoint: https://$SEARCH_ENDPOINT/"
echo -e "  SKU:      $SEARCH_SKU"
echo ""

# ============================================================================
# Confirmation
# ============================================================================

echo -e "${RED}============================================================================${NC}"
echo -e "${RED}WARNING: This will DELETE the Azure AI Search service!${NC}"
echo -e "${RED}============================================================================${NC}"
echo ""
echo -e "${YELLOW}This action will:${NC}"
echo -e "  1. Delete all indexes and their data"
echo -e "  2. Delete all indexers, data sources, and skillsets"
echo -e "  3. Delete the entire search service"
echo ""
echo -e "${RED}This action CANNOT be undone!${NC}"
echo ""

read -p "Are you sure you want to continue? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo -e "${YELLOW}Cleanup cancelled${NC}"
    exit 0
fi

echo ""

# ============================================================================
# Delete search service
# ============================================================================

echo -e "${BLUE}============================================================================${NC}"
echo -e "${BLUE}Deleting Azure AI Search service...${NC}"
echo -e "${BLUE}============================================================================${NC}"
echo ""

echo -e "${YELLOW}Deleting search service '$SEARCH_SERVICE_NAME'...${NC}"

if az search service delete \
    --name "$SEARCH_SERVICE_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --yes \
    2>&1; then
    echo -e "${GREEN}✓ Search service deleted successfully${NC}"
else
    echo -e "${RED}✗ Failed to delete search service${NC}"
    exit 1
fi

echo ""

# ============================================================================
# Verify deletion
# ============================================================================

echo -e "${BLUE}Verifying deletion...${NC}"

if az search service show --name "$SEARCH_SERVICE_NAME" --resource-group "$RESOURCE_GROUP" &> /dev/null; then
    echo -e "${RED}✗ Search service still exists${NC}"
    exit 1
else
    echo -e "${GREEN}✓ Search service successfully deleted${NC}"
fi

echo ""

# ============================================================================
# Summary
# ============================================================================

echo -e "${GREEN}============================================================================${NC}"
echo -e "${GREEN}Cleanup completed successfully!${NC}"
echo -e "${GREEN}============================================================================${NC}"
echo ""
echo -e "${YELLOW}Deleted resources:${NC}"
echo -e "  - Azure AI Search service: $SEARCH_SERVICE_NAME"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo -e "  - To recreate the search service, run:"
echo -e "    ${BLUE}./tools_and_data/vector_db/bicep/deploy-vector-search.sh${NC}"
echo ""

