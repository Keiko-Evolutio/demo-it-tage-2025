#!/bin/bash
# ============================================================================
# Cleanup Script for Document Intelligence Workshop Stack
# ============================================================================
# This script deletes all resources created by the Document Intelligence deployment
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

# Resource names
DOCUMENT_INTELLIGENCE_NAME="doc-intel-doc-intelligence-${ENVIRONMENT_NAME}"
STORAGE_ACCOUNT_NAME="stdocintel${ENVIRONMENT_NAME//-/}"

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
echo -e "${BLUE}Document Intelligence Workshop Stack - Cleanup${NC}"
echo -e "${BLUE}============================================================================${NC}"
echo ""
echo -e "${YELLOW}Resource Group:${NC}              $RESOURCE_GROUP"
echo -e "${YELLOW}Environment:${NC}                 $ENVIRONMENT_NAME"
echo -e "${YELLOW}Document Intelligence:${NC}       $DOCUMENT_INTELLIGENCE_NAME"
echo -e "${YELLOW}Storage Account:${NC}             $STORAGE_ACCOUNT_NAME"
echo ""

# ============================================================================
# Confirmation
# ============================================================================

echo -e "${RED}WARNING: This will delete all Document Intelligence resources!${NC}"
echo -e "${YELLOW}Do you want to continue? (yes/no)${NC}"
read -r CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo -e "${YELLOW}Cleanup cancelled${NC}"
    exit 0
fi

# ============================================================================
# Check if Azure CLI is installed
# ============================================================================

if ! command -v az &> /dev/null; then
    echo -e "${RED}Error: Azure CLI is not installed${NC}"
    exit 1
fi

# ============================================================================
# Check if logged in to Azure
# ============================================================================

echo ""
echo -e "${BLUE}Checking Azure login status...${NC}"
if ! az account show &> /dev/null; then
    echo -e "${RED}Error: Not logged in to Azure${NC}"
    echo "Please run: az login"
    exit 1
fi

CURRENT_SUBSCRIPTION=$(az account show --query name -o tsv)
echo -e "${GREEN}Logged in to Azure${NC}"
echo -e "${YELLOW}Subscription:${NC} $CURRENT_SUBSCRIPTION"
echo ""

# ============================================================================
# Delete resources
# ============================================================================

echo -e "${BLUE}============================================================================${NC}"
echo -e "${BLUE}Deleting Document Intelligence Workshop Stack...${NC}"
echo -e "${BLUE}============================================================================${NC}"
echo ""

# Delete Document Intelligence
echo -e "${BLUE}Deleting Document Intelligence: $DOCUMENT_INTELLIGENCE_NAME${NC}"
if az cognitiveservices account show --name "$DOCUMENT_INTELLIGENCE_NAME" --resource-group "$RESOURCE_GROUP" &> /dev/null; then
    az cognitiveservices account delete --name "$DOCUMENT_INTELLIGENCE_NAME" --resource-group "$RESOURCE_GROUP" --yes
    echo -e "${GREEN}✓ Document Intelligence deleted${NC}"
else
    echo -e "${YELLOW}⚠ Document Intelligence not found (may already be deleted)${NC}"
fi

# Delete Storage Account
echo -e "${BLUE}Deleting Storage Account: $STORAGE_ACCOUNT_NAME${NC}"
if az storage account show --name "$STORAGE_ACCOUNT_NAME" --resource-group "$RESOURCE_GROUP" &> /dev/null; then
    az storage account delete --name "$STORAGE_ACCOUNT_NAME" --resource-group "$RESOURCE_GROUP" --yes
    echo -e "${GREEN}✓ Storage Account deleted${NC}"
else
    echo -e "${YELLOW}⚠ Storage Account not found (may already be deleted)${NC}"
fi

# ============================================================================
# Completion
# ============================================================================

echo ""
echo -e "${GREEN}============================================================================${NC}"
echo -e "${GREEN}Cleanup completed successfully!${NC}"
echo -e "${GREEN}============================================================================${NC}"
echo ""
echo -e "${YELLOW}Note:${NC} The .env file has not been modified."
echo -e "      You may want to remove the Document Intelligence configuration manually."
echo ""

