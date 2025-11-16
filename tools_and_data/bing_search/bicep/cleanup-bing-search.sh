#!/bin/bash
# ============================================================================
# Cleanup Script for Azure AI Search + Bing Grounding Workshop Stack
# ============================================================================
# Removes every resource that tools_and_data/bing_search/bicep/bing-search.bicep
# creates (Bing Grounding account, AI Services + Project, Search service,
# user-assigned identity, deployment script, etc.)
# ============================================================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/../../.env"

if [[ ! -f "$ENV_FILE" ]]; then
    echo -e "${RED}Error: .env file not found at $ENV_FILE${NC}"
    exit 1
fi

set -a
source "$ENV_FILE"
set +a

RESOURCE_GROUP="${AZURE_RESOURCE_GROUP:-}"
LOCATION="${AZURE_LOCATION:-}"
ENVIRONMENT_NAME="${ENVIRONMENT_NAME:-}"

if [[ -z "$RESOURCE_GROUP" || -z "$ENVIRONMENT_NAME" ]]; then
    echo -e "${RED}Error: AZURE_RESOURCE_GROUP and ENVIRONMENT_NAME must be set in .env${NC}"
    exit 1
fi

BING_ACCOUNT="bing-grounding-${ENVIRONMENT_NAME}"
AI_SERVICES="ai-services-${ENVIRONMENT_NAME}"
AI_PROJECT="ai-project-${ENVIRONMENT_NAME}"
SEARCH_SERVICE="ai-search-${ENVIRONMENT_NAME}"
IDENTITY_NAME="identity-create-agent-${ENVIRONMENT_NAME}"
DEPLOY_SCRIPT_NAME="create-agent-${ENVIRONMENT_NAME}"

echo -e "${BLUE}============================================================================${NC}"
echo -e "${BLUE}Cleanup Bing Grounding Workshop Resources${NC}"
echo -e "${BLUE}============================================================================${NC}"
echo -e "${YELLOW}Resource Group:${NC}  $RESOURCE_GROUP"
echo -e "${YELLOW}Environment:${NC}     $ENVIRONMENT_NAME"
echo -e "${YELLOW}Bing Account:${NC}     $BING_ACCOUNT"
echo -e "${YELLOW}AI Services:${NC}      $AI_SERVICES"
echo -e "${YELLOW}AI Project:${NC}       $AI_PROJECT"
echo -e "${YELLOW}Search Service:${NC}   $SEARCH_SERVICE"
echo ""

if ! command -v az >/dev/null 2>&1; then
    echo -e "${RED}Azure CLI not installed. Please install before running this script.${NC}"
    exit 1
fi

echo -e "${BLUE}Checking Azure login...${NC}"
if ! az account show >/dev/null 2>&1; then
    echo -e "${RED}You must run 'az login' first.${NC}"
    exit 1
fi
SUBSCRIPTION_ID=$(az account show --query id -o tsv)

RG_ID="/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}"
BING_ID="${RG_ID}/providers/Microsoft.Bing/accounts/${BING_ACCOUNT}"
AI_SERVICES_ID="${RG_ID}/providers/Microsoft.CognitiveServices/accounts/${AI_SERVICES}"
AI_PROJECT_ID="${AI_SERVICES_ID}/projects/${AI_PROJECT}"
SEARCH_ID="${RG_ID}/providers/Microsoft.Search/searchServices/${SEARCH_SERVICE}"
IDENTITY_ID="${RG_ID}/providers/Microsoft.ManagedIdentity/userAssignedIdentities/${IDENTITY_NAME}"
DEPLOY_SCRIPT_ID="${RG_ID}/providers/Microsoft.Resources/deploymentScripts/${DEPLOY_SCRIPT_NAME}"

if ! az group show --name "$RESOURCE_GROUP" >/dev/null 2>&1; then
    echo -e "${YELLOW}Resource group '$RESOURCE_GROUP' does not exist. Nothing to clean up.${NC}"
    exit 0
fi

echo -e "${RED}============================================================================${NC}"
echo -e "${RED}WARNING: All workshop resources in this resource group will be deleted${NC}"
echo -e "${RED}============================================================================${NC}"
read -p "Type 'yes' to continue: " CONFIRM
if [[ "$CONFIRM" != "yes" ]]; then
    echo -e "${YELLOW}Cleanup aborted.${NC}"
    exit 0
fi
echo ""

delete_if_exists() {
    local description=$1
    local check_cmd=$2
    local delete_cmd=$3

    echo -e "${BLUE}Checking ${description}...${NC}"
    if eval "$check_cmd" >/dev/null 2>&1; then
        echo -e "${YELLOW}Deleting ${description}...${NC}"
        if eval "$delete_cmd" >/dev/null 2>&1; then
            echo -e "${GREEN}✓ ${description} deleted${NC}"
        else
            echo -e "${RED}✗ Failed to delete ${description}${NC}"
            exit 1
        fi
    else
        echo -e "${YELLOW}${description} not found. Skipping.${NC}"
    fi
    echo ""
}

delete_if_exists "Azure AI Search service '$SEARCH_SERVICE'" \
    "az search service show --name \"$SEARCH_SERVICE\" --resource-group \"$RESOURCE_GROUP\"" \
    "az search service delete --name \"$SEARCH_SERVICE\" --resource-group \"$RESOURCE_GROUP\" --yes"

delete_if_exists "AI Project '$AI_PROJECT'" \
    "az rest --method get --url \"https://management.azure.com${AI_PROJECT_ID}?api-version=2025-10-01-preview\"" \
    "az rest --method delete --url \"https://management.azure.com${AI_PROJECT_ID}?api-version=2025-10-01-preview\""

delete_if_exists "AI Services account '$AI_SERVICES'" \
    "az cognitiveservices account show --name \"$AI_SERVICES\" --resource-group \"$RESOURCE_GROUP\"" \
    "az cognitiveservices account delete --name \"$AI_SERVICES\" --resource-group \"$RESOURCE_GROUP\""

if [[ -n "${LOCATION:-}" ]]; then
    echo -e "${BLUE}Purging soft-deleted AI Services account (if any)...${NC}"
    az cognitiveservices account purge \
        --name "$AI_SERVICES" \
        --resource-group "$RESOURCE_GROUP" \
        --location "$LOCATION" \
        >/dev/null || true
    echo ""
fi

delete_if_exists "Bing Grounding account '$BING_ACCOUNT'" \
    "az resource show --ids \"$BING_ID\"" \
    "az resource delete --ids \"$BING_ID\""

delete_if_exists "User-assigned identity '$IDENTITY_NAME'" \
    "az identity show --name \"$IDENTITY_NAME\" --resource-group \"$RESOURCE_GROUP\"" \
    "az identity delete --name \"$IDENTITY_NAME\" --resource-group \"$RESOURCE_GROUP\""

delete_if_exists "deployment script '$DEPLOY_SCRIPT_NAME'" \
    "az resource show --ids \"$DEPLOY_SCRIPT_ID\"" \
    "az resource delete --ids \"$DEPLOY_SCRIPT_ID\""

echo -e "${GREEN}============================================================================${NC}"
echo -e "${GREEN}Cleanup completed successfully${NC}"
echo -e "${GREEN}============================================================================${NC}"
