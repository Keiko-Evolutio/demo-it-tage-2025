#!/bin/bash
# ============================================================================
# Deployment Script for Document Intelligence Workshop Stack
# ============================================================================
# This script deploys the complete infrastructure for the Document Intelligence Workshop:
# - Azure AI Document Intelligence (Form Recognizer)
# - Storage Account + Blob Container
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
BICEP_FILE="$SCRIPT_DIR/document-intelligence.bicep"

# Deployment parameters
DOCUMENT_INTELLIGENCE_SKU="S0"
STORAGE_ACCOUNT_SKU="Standard_LRS"
BLOB_CONTAINER_NAME="sample-documents"

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
echo -e "${BLUE}Document Intelligence Workshop Stack - Deployment${NC}"
echo -e "${BLUE}============================================================================${NC}"
echo ""
echo -e "${YELLOW}Configuration:${NC}"
echo -e "  Resource Group:         $RESOURCE_GROUP"
echo -e "  Location:               $LOCATION"
echo -e "  Environment:            $ENVIRONMENT_NAME"
echo -e "  Document Intelligence:  $DOCUMENT_INTELLIGENCE_SKU"
echo -e "  Storage SKU:            $STORAGE_ACCOUNT_SKU"
echo -e "  Blob Container:         $BLOB_CONTAINER_NAME"
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
echo -e "${BLUE}Deploying Document Intelligence Workshop Stack...${NC}"
echo -e "${BLUE}============================================================================${NC}"
echo ""

DEPLOYMENT_NAME="document-intelligence-$(date +%Y%m%d-%H%M%S)"
echo -e "${YELLOW}Deployment name:${NC} $DEPLOYMENT_NAME"
echo ""

az deployment group create \
    --name "$DEPLOYMENT_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --template-file "$BICEP_FILE" \
    --parameters \
        environmentName="$ENVIRONMENT_NAME" \
        location="$LOCATION" \
        documentIntelligenceSku="$DOCUMENT_INTELLIGENCE_SKU" \
        storageAccountSku="$STORAGE_ACCOUNT_SKU" \
        blobContainerName="$BLOB_CONTAINER_NAME"

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✓ Deployment completed${NC}"
else
    echo ""
    echo -e "${RED}✗ Deployment failed${NC}"
    exit 1
fi

# ============================================================================
# Retrieve deployment outputs
# ============================================================================

echo ""
echo -e "${BLUE}Retrieving deployment outputs...${NC}"

DOCUMENT_INTELLIGENCE_NAME=$(az deployment group show \
    --name "$DEPLOYMENT_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query "properties.outputs.documentIntelligenceName.value" -o tsv)

DOCUMENT_INTELLIGENCE_ENDPOINT=$(az deployment group show \
    --name "$DEPLOYMENT_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query "properties.outputs.documentIntelligenceEndpoint.value" -o tsv)

DOCUMENT_INTELLIGENCE_API_KEY=$(az deployment group show \
    --name "$DEPLOYMENT_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query "properties.outputs.documentIntelligenceApiKey.value" -o tsv)

STORAGE_ACCOUNT_NAME=$(az deployment group show \
    --name "$DEPLOYMENT_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query "properties.outputs.storageAccountName.value" -o tsv)

STORAGE_ACCOUNT_BLOB_ENDPOINT=$(az deployment group show \
    --name "$DEPLOYMENT_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query "properties.outputs.storageAccountBlobEndpoint.value" -o tsv)

STORAGE_CONNECTION_STRING=$(az deployment group show \
    --name "$DEPLOYMENT_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query "properties.outputs.storageConnectionString.value" -o tsv)

BLOB_CONTAINER_NAME_OUTPUT=$(az deployment group show \
    --name "$DEPLOYMENT_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query "properties.outputs.blobContainerName.value" -o tsv)

echo -e "${GREEN}✓ Outputs retrieved${NC}"

# ============================================================================
# Display deployment information
# ============================================================================

echo ""
echo -e "${GREEN}============================================================================${NC}"
echo -e "${GREEN}Deployment completed successfully!${NC}"
echo -e "${GREEN}============================================================================${NC}"
echo ""
echo -e "${YELLOW}Azure AI Document Intelligence:${NC}"
echo -e "  Name:       $DOCUMENT_INTELLIGENCE_NAME"
echo -e "  Endpoint:   $DOCUMENT_INTELLIGENCE_ENDPOINT"
echo -e "  API Key:    ${DOCUMENT_INTELLIGENCE_API_KEY:0:20}..."
echo ""
echo -e "${YELLOW}Storage Account:${NC}"
echo -e "  Name:       $STORAGE_ACCOUNT_NAME"
echo -e "  Endpoint:   $STORAGE_ACCOUNT_BLOB_ENDPOINT"
echo -e "  Container:  $BLOB_CONTAINER_NAME_OUTPUT"
echo ""

# ============================================================================
# Update .env file
# ============================================================================

echo -e "${BLUE}Updating .env file...${NC}"

# Create backup
cp "$ENV_FILE" "$ENV_FILE.backup"

# Update or add Document Intelligence configuration
if grep -q "^DOCUMENT_INTELLIGENCE_SERVICE_NAME=" "$ENV_FILE"; then
    sed -i.bak "s|^DOCUMENT_INTELLIGENCE_SERVICE_NAME=.*|DOCUMENT_INTELLIGENCE_SERVICE_NAME=\"$DOCUMENT_INTELLIGENCE_NAME\"|" "$ENV_FILE"
else
    echo "" >> "$ENV_FILE"
    echo "# Azure Document Intelligence (Form Recognizer)" >> "$ENV_FILE"
    echo "DOCUMENT_INTELLIGENCE_SERVICE_NAME=\"$DOCUMENT_INTELLIGENCE_NAME\"" >> "$ENV_FILE"
fi

if grep -q "^DOCUMENT_INTELLIGENCE_ENDPOINT=" "$ENV_FILE"; then
    sed -i.bak "s|^DOCUMENT_INTELLIGENCE_ENDPOINT=.*|DOCUMENT_INTELLIGENCE_ENDPOINT=\"$DOCUMENT_INTELLIGENCE_ENDPOINT\"|" "$ENV_FILE"
else
    echo "DOCUMENT_INTELLIGENCE_ENDPOINT=\"$DOCUMENT_INTELLIGENCE_ENDPOINT\"" >> "$ENV_FILE"
fi

if grep -q "^DOCUMENT_INTELLIGENCE_API_KEY=" "$ENV_FILE"; then
    sed -i.bak "s|^DOCUMENT_INTELLIGENCE_API_KEY=.*|DOCUMENT_INTELLIGENCE_API_KEY=\"$DOCUMENT_INTELLIGENCE_API_KEY\"|" "$ENV_FILE"
else
    echo "DOCUMENT_INTELLIGENCE_API_KEY=\"$DOCUMENT_INTELLIGENCE_API_KEY\"" >> "$ENV_FILE"
fi

# Update Storage Account configuration for Document Intelligence
if grep -q "^DOC_INTEL_STORAGE_ACCOUNT_NAME=" "$ENV_FILE"; then
    sed -i.bak "s|^DOC_INTEL_STORAGE_ACCOUNT_NAME=.*|DOC_INTEL_STORAGE_ACCOUNT_NAME=\"$STORAGE_ACCOUNT_NAME\"|" "$ENV_FILE"
else
    echo "DOC_INTEL_STORAGE_ACCOUNT_NAME=\"$STORAGE_ACCOUNT_NAME\"" >> "$ENV_FILE"
fi

if grep -q "^DOC_INTEL_STORAGE_ENDPOINT=" "$ENV_FILE"; then
    sed -i.bak "s|^DOC_INTEL_STORAGE_ENDPOINT=.*|DOC_INTEL_STORAGE_ENDPOINT=\"$STORAGE_ACCOUNT_BLOB_ENDPOINT\"|" "$ENV_FILE"
else
    echo "DOC_INTEL_STORAGE_ENDPOINT=\"$STORAGE_ACCOUNT_BLOB_ENDPOINT\"" >> "$ENV_FILE"
fi

if grep -q "^DOC_INTEL_STORAGE_CONNECTION_STRING=" "$ENV_FILE"; then
    sed -i.bak "s|^DOC_INTEL_STORAGE_CONNECTION_STRING=.*|DOC_INTEL_STORAGE_CONNECTION_STRING=\"$STORAGE_CONNECTION_STRING\"|" "$ENV_FILE"
else
    echo "DOC_INTEL_STORAGE_CONNECTION_STRING=\"$STORAGE_CONNECTION_STRING\"" >> "$ENV_FILE"
fi

if grep -q "^DOC_INTEL_CONTAINER_NAME=" "$ENV_FILE"; then
    sed -i.bak "s|^DOC_INTEL_CONTAINER_NAME=.*|DOC_INTEL_CONTAINER_NAME=\"$BLOB_CONTAINER_NAME_OUTPUT\"|" "$ENV_FILE"
else
    echo "DOC_INTEL_CONTAINER_NAME=\"$BLOB_CONTAINER_NAME_OUTPUT\"" >> "$ENV_FILE"
fi

# Remove backup files
rm -f "$ENV_FILE.bak"

echo -e "${GREEN}✓ .env file updated${NC}"
echo -e "${YELLOW}Backup saved to:${NC} $ENV_FILE.backup"
echo ""

# ============================================================================
# Next steps
# ============================================================================

echo -e "${YELLOW}Next steps:${NC}"
echo -e "  1. Upload sample documents to Blob Storage:"
echo -e "     ${BLUE}python tools_and_data/document_intelligence/examples/upload_sample_data.py${NC}"
echo ""
echo -e "  2. Run the example notebooks:"
echo -e "     ${BLUE}tools_and_data/document_intelligence/examples/01_document_analysis.ipynb${NC}"
echo -e "     ${BLUE}tools_and_data/document_intelligence/examples/02_prebuilt_models.ipynb${NC}"
echo ""
echo -e "  3. To delete the Document Intelligence service:"
echo -e "     ${BLUE}./tools_and_data/document_intelligence/bicep/cleanup-document-intelligence.sh${NC}"
echo ""

