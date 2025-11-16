#!/bin/bash
# ============================================================================
# Deployment Script for Azure AI Search + Bing Grounding Workshop Stack
# ============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/../../.env"
BICEP_FILE="$SCRIPT_DIR/bing-search.bicep"

if [[ ! -f "$ENV_FILE" ]]; then
    echo -e "${RED}Error: .env file not found at $ENV_FILE${NC}"
    exit 1
fi

if [[ ! -f "$BICEP_FILE" ]]; then
    echo -e "${RED}Error: Bicep file not found at $BICEP_FILE${NC}"
    exit 1
fi

set -a
source "$ENV_FILE"
set +a

RESOURCE_GROUP="${AZURE_RESOURCE_GROUP:-}"
LOCATION="${AZURE_LOCATION:-}"
ENVIRONMENT_NAME="${ENVIRONMENT_NAME:-}"
AGENT_NAME="${AI_PROJECT_AGENT_NAME:-bing-grounding-agent}"
AGENT_MODEL="${AI_PROJECT_AGENT_MODEL:-gpt-4o}"
SEARCH_INDEX_NAME="${AI_SEARCH_INDEX_NAME:-docs}"
SEARCH_SKU="${AI_SEARCH_SKU:-basic}"
BING_SKU="${BING_GROUNDING_SKU:-G1}"
OPENAI_CAPACITY="${AI_CHAT_DEPLOYMENT_CAPACITY:-5}"

if [[ -z "$RESOURCE_GROUP" || -z "$LOCATION" || -z "$ENVIRONMENT_NAME" ]]; then
    echo -e "${RED}Error: AZURE_RESOURCE_GROUP, AZURE_LOCATION, and ENVIRONMENT_NAME must be set in .env${NC}"
    exit 1
fi

BING_ACCOUNT="bing-grounding-${ENVIRONMENT_NAME}"
AI_SERVICES="ai-services-${ENVIRONMENT_NAME}"
AI_PROJECT="ai-project-${ENVIRONMENT_NAME}"
SEARCH_SERVICE="ai-search-${ENVIRONMENT_NAME}"
SEARCH_CONN_NAME="conn-search"
BING_CONN_NAME="conn-bing-grounding"

echo -e "${BLUE}============================================================================${NC}"
echo -e "${BLUE}Deploy Bing Grounding Workshop Stack${NC}"
echo -e "${BLUE}============================================================================${NC}"
echo -e "${YELLOW}Resource Group:${NC}  $RESOURCE_GROUP"
echo -e "${YELLOW}Location:${NC}        $LOCATION"
echo -e "${YELLOW}Environment:${NC}     $ENVIRONMENT_NAME"
echo -e "${YELLOW}Agent Name:${NC}      $AGENT_NAME"
echo -e "${YELLOW}Agent Model:${NC}     $AGENT_MODEL"
echo -e "${YELLOW}Search SKU:${NC}      $SEARCH_SKU"
echo -e "${YELLOW}Search Index:${NC}    $SEARCH_INDEX_NAME"
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

CURRENT_SUBSCRIPTION=$(az account show --query name -o tsv)
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
echo -e "${GREEN}Logged in to Azure subscription:${NC} $CURRENT_SUBSCRIPTION"
echo ""

if ! az group show --name "$RESOURCE_GROUP" >/dev/null 2>&1; then
    echo -e "${YELLOW}Resource group not found. Creating...${NC}"
    az group create --name "$RESOURCE_GROUP" --location "$LOCATION" >/dev/null
    echo -e "${GREEN}✓ Resource group created${NC}"
else
    echo -e "${GREEN}Resource group exists${NC}"
fi
echo ""

DEPLOYMENT_NAME="bing-grounding-$(date +%Y%m%d-%H%M%S)"
echo -e "${BLUE}Starting deployment: ${DEPLOYMENT_NAME}${NC}"

TEMPLATE_FILE=$(mktemp)
BODY_FILE=$(mktemp)
trap 'rm -f "$TEMPLATE_FILE" "$BODY_FILE"' EXIT

az bicep build -f "$BICEP_FILE" --outfile "$TEMPLATE_FILE" >/dev/null

export PARAM_ENVIRONMENT="$ENVIRONMENT_NAME"
export PARAM_LOCATION="$LOCATION"
export PARAM_BING_SKU="$BING_SKU"
export PARAM_SEARCH_SKU="$SEARCH_SKU"
export PARAM_AGENT_MODEL="$AGENT_MODEL"
export PARAM_AGENT_NAME="$AGENT_NAME"
export PARAM_SEARCH_INDEX="$SEARCH_INDEX_NAME"
export PARAM_OPENAI_CAPACITY="$OPENAI_CAPACITY"

python3 - "$TEMPLATE_FILE" "$BODY_FILE" <<'PY'
import json, os, sys
template_path, body_path = sys.argv[1], sys.argv[2]
template = json.load(open(template_path))
params = {
    "environmentName": os.environ["PARAM_ENVIRONMENT"],
    "location": os.environ["PARAM_LOCATION"],
    "bingGroundingSku": os.environ["PARAM_BING_SKU"],
    "searchSku": os.environ["PARAM_SEARCH_SKU"],
    "agentModel": os.environ["PARAM_AGENT_MODEL"],
    "agentName": os.environ["PARAM_AGENT_NAME"],
    "searchIndexName": os.environ["PARAM_SEARCH_INDEX"],
    "openAiDeploymentCapacity": int(os.environ["PARAM_OPENAI_CAPACITY"]),
}
body = {
    "properties": {
        "mode": "Incremental",
        "template": template,
        "parameters": {k: {"value": v} for k, v in params.items()},
    }
}
json.dump(body, open(body_path, "w"))
PY

az rest --method put \
    --url "https://management.azure.com/subscriptions/${SUBSCRIPTION_ID}/resourcegroups/${RESOURCE_GROUP}/providers/Microsoft.Resources/deployments/${DEPLOYMENT_NAME}?api-version=2024-08-01" \
    --body @"$BODY_FILE" >/dev/null

az deployment group wait \
    --name "$DEPLOYMENT_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --created >/dev/null

PROVISIONING_STATE=$(az deployment group show \
    --name "$DEPLOYMENT_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query "properties.provisioningState" -o tsv)

if [[ "$PROVISIONING_STATE" != "Succeeded" ]]; then
    echo -e "${RED}Deployment failed with state: $PROVISIONING_STATE${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Deployment completed${NC}"
echo ""

echo -e "${BLUE}Fetching resource details...${NC}"

AI_PROJECT_ENDPOINT="https://${AI_SERVICES}.services.ai.azure.com/api/projects/${AI_PROJECT}"
AI_SERVICES_ENDPOINT="https://${AI_SERVICES}.services.ai.azure.com"
SEARCH_ENDPOINT="https://${SEARCH_SERVICE}.search.windows.net"

BING_KEY=$(az rest --method post \
    --url "https://management.azure.com/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.Bing/accounts/${BING_ACCOUNT}/listKeys?api-version=2020-06-10" \
    --query key1 -o tsv)

SEARCH_ADMIN_KEY=$(az search admin-key show \
    --service-name "$SEARCH_SERVICE" \
    --resource-group "$RESOURCE_GROUP" \
    --query primaryKey -o tsv)

if [[ -z "$BING_KEY" || -z "$SEARCH_ADMIN_KEY" ]]; then
    echo -e "${RED}Failed to retrieve required keys.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Resource details retrieved${NC}"
echo ""

echo -e "${BLUE}Updating .env file...${NC}"
cp "$ENV_FILE" "$ENV_FILE.backup"

update_env_var() {
    local key="$1"
    local value="$2"
    if grep -q "^${key}=" "$ENV_FILE"; then
        sed -i.tmp "s|^${key}=.*|${key}=\"${value}\"|" "$ENV_FILE"
        rm -f "$ENV_FILE.tmp"
    else
        echo "${key}=\"${value}\"" >> "$ENV_FILE"
    fi
}

update_env_var "BING_GROUNDING_RESOURCE_NAME" "$BING_ACCOUNT"
update_env_var "BING_GROUNDING_ENDPOINT" "https://api.bing.microsoft.com/"
update_env_var "BING_GROUNDING_API_KEY" "$BING_KEY"

update_env_var "AI_SEARCH_ENDPOINT" "$SEARCH_ENDPOINT"
update_env_var "AI_SEARCH_INDEX_NAME" "$SEARCH_INDEX_NAME"
update_env_var "AI_SEARCH_ADMIN_KEY" "$SEARCH_ADMIN_KEY"

update_env_var "AI_PROJECT_ACCOUNT_NAME" "$AI_SERVICES"
update_env_var "AI_PROJECT_NAME" "$AI_PROJECT"
update_env_var "AI_PROJECT_ENDPOINT" "$AI_PROJECT_ENDPOINT"
update_env_var "AI_PROJECT_AGENT_NAME" "$AGENT_NAME"
update_env_var "AI_PROJECT_AGENT_MODEL" "$AGENT_MODEL"
update_env_var "AI_PROJECT_SEARCH_CONNECTION_NAME" "$SEARCH_CONN_NAME"
update_env_var "AI_PROJECT_BING_CONNECTION_NAME" "$BING_CONN_NAME"

echo -e "${GREEN}✓ .env updated (backup saved to ${ENV_FILE}.backup)${NC}"
echo ""

echo -e "${GREEN}============================================================================${NC}"
echo -e "${GREEN}Deployment finished successfully!${NC}"
echo -e "${GREEN}============================================================================${NC}"
