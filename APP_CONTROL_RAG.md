# App Control - RAG Version (ai-chat-with-rag)

This document contains commands to control the RAG-enabled AI Chat application deployment.

## Prerequisites

- Azure CLI installed and logged in
- Correct subscription selected
- Access to the resource group

## Environment Information

- **Branch**: `ai-chat-with-rag`
- **Environment Name**: `keiko-ai-chat-rag-demo`
- **Resource Group**: Will be created during deployment (e.g., `rg-keiko-ai-chat-rag-demo-westeu`)
- **Location**: West Europe
- **Features**: RAG with Azure AI Search, Document Upload, Source Citations

## Stop the Application

To stop the application and prevent access (while keeping all resources):

```bash
# Switch to RAG environment
azd env select keiko-ai-chat-rag-demo

# Get the Container App name
CONTAINER_APP_NAME=$(azd env get-values | grep SERVICE_API_NAME | cut -d'=' -f2 | tr -d '"')
RESOURCE_GROUP=$(azd env get-values | grep AZURE_RESOURCE_GROUP | cut -d'=' -f2 | tr -d '"')

# Disable ingress (makes app inaccessible)
az containerapp ingress disable \
  --name $CONTAINER_APP_NAME \
  --resource-group $RESOURCE_GROUP

echo "✅ RAG Application stopped successfully"
echo "The app is now inaccessible but all resources are preserved"
```

## Start the Application

To start the application again:

```bash
# Switch to RAG environment
azd env select keiko-ai-chat-rag-demo

# Get the Container App name
CONTAINER_APP_NAME=$(azd env get-values | grep SERVICE_API_NAME | cut -d'=' -f2 | tr -d '"')
RESOURCE_GROUP=$(azd env get-values | grep AZURE_RESOURCE_GROUP | cut -d'=' -f2 | tr -d '"')

# Enable ingress
az containerapp ingress enable \
  --name $CONTAINER_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --type external \
  --target-port 8000 \
  --transport auto

# Get the URL
APP_URL=$(azd env get-values | grep SERVICE_API_URI | cut -d'=' -f2 | tr -d '"')

echo "✅ RAG Application started successfully"
echo "Access the app at: $APP_URL"
```

## Check Application Status

```bash
# Switch to RAG environment
azd env select keiko-ai-chat-rag-demo

# Get the Container App name
CONTAINER_APP_NAME=$(azd env get-values | grep SERVICE_API_NAME | cut -d'=' -f2 | tr -d '"')
RESOURCE_GROUP=$(azd env get-values | grep AZURE_RESOURCE_GROUP | cut -d'=' -f2 | tr -d '"')

# Show app status
az containerapp show \
  --name $CONTAINER_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --query "{name:name, status:properties.provisioningState, ingressEnabled:properties.configuration.ingress.external, url:properties.configuration.ingress.fqdn}" \
  --output table
```

## View Application Logs

```bash
# Switch to RAG environment
azd env select keiko-ai-chat-rag-demo

# Get the Container App name
CONTAINER_APP_NAME=$(azd env get-values | grep SERVICE_API_NAME | cut -d'=' -f2 | tr -d '"')
RESOURCE_GROUP=$(azd env get-values | grep AZURE_RESOURCE_GROUP | cut -d'=' -f2 | tr -d '"')

# Stream logs
az containerapp logs show \
  --name $CONTAINER_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --follow
```

## RAG-Specific Features

### Check Azure AI Search Status

```bash
# Get AI Search endpoint
AI_SEARCH_ENDPOINT=$(azd env get-values | grep AZURE_AI_SEARCH_ENDPOINT | cut -d'=' -f2 | tr -d '"')

echo "Azure AI Search Endpoint: $AI_SEARCH_ENDPOINT"
```

### Check Blob Storage

```bash
# Get Storage Account name
STORAGE_ACCOUNT=$(azd env get-values | grep AZURE_STORAGE_ACCOUNT_NAME | cut -d'=' -f2 | tr -d '"')
RESOURCE_GROUP=$(azd env get-values | grep AZURE_RESOURCE_GROUP | cut -d'=' -f2 | tr -d '"')

# List documents container
az storage blob list \
  --account-name $STORAGE_ACCOUNT \
  --container-name documents \
  --auth-mode login \
  --output table
```

## Cost Management

### Estimated Monthly Costs (when running)

- **Azure AI Foundry Project**: ~€10-20/month
- **Container App**: ~€5-10/month (minimal usage)
- **Azure AI Search (Basic)**: ~€50-100/month
- **Storage Account**: ~€1-5/month
- **Application Insights**: ~€5-10/month
- **Total**: ~€70-145/month

### Cost Optimization

1. **Stop when not in use**: Use the stop command above
2. **Delete when done**: `azd down` (removes all resources)
3. **Monitor usage**: Check Azure Cost Management regularly

## Troubleshooting

### App not accessible after start

```bash
# Check ingress configuration
az containerapp ingress show \
  --name $CONTAINER_APP_NAME \
  --resource-group $RESOURCE_GROUP
```

### Document upload fails

1. Check blob storage permissions
2. Verify storage account is accessible
3. Check application logs for errors

### RAG search not working

1. Verify Azure AI Search is deployed
2. Check if index exists
3. Verify embeddings model is deployed
4. Check application logs

## Important Notes

- **Two Deployments**: This is the RAG-enabled version. The basic version is in `ai-chat` branch
- **Separate Resources**: Each deployment has its own resource group and resources
- **Independent Control**: Stopping one deployment doesn't affect the other
- **Data Persistence**: Uploaded documents and indexed data persist when app is stopped
- **Security**: Both deployments can have different authentication settings

## Related Files

- `APP_CONTROL.md`: Control commands for basic version (ai-chat branch)
- `infra/`: Infrastructure as Code (Bicep templates)
- `src/api/`: Backend code with RAG implementation
- `src/frontend/`: Frontend code with upload UI

