# App Control Commands for AI Chat (ai-chat branch)

## Branch
```bash
ai-chat
```

## Befehl: App Stop (Ingress deaktivieren - App sofort nicht erreichbar)
```bash
az containerapp ingress disable \
  --name ca-api-dsdtz57twqe44 \
  --resource-group rg-keiko-ai-chat-demo-westeu
```

## Befehl: App Start (Ingress aktivieren - App sofort erreichbar)
```bash
az containerapp ingress enable \
  --name ca-api-dsdtz57twqe44 \
  --resource-group rg-keiko-ai-chat-demo-westeu \
  --type external \
  --target-port 50505 \
  --transport auto
```

## Status prüfen
```bash
az containerapp show \
  --name ca-api-dsdtz57twqe44 \
  --resource-group rg-keiko-ai-chat-demo-westeu \
  --query "properties.configuration.ingress.fqdn" \
  --output tsv
```

## URL zur App AI-Chat
https://ca-api-dsdtz57twqe44.wonderfulflower-270115ae.westeurope.azurecontainerapps.io/


---


# App Control Commands for AI Chat (ai-chat-with-rag branch)

## Branch
```bash
ai-chat-with-rag
```

## Befehl: App Stop (Ingress deaktivieren - App sofort nicht erreichbar)
```bash
az containerapp ingress disable \
  --name ca-api-q3i3ucwe64hug \
  --resource-group rg-keiko-ai-chat-rag-v3
```

## Befehl: App Start (Ingress aktivieren - App sofort erreichbar)
```bash
az containerapp ingress enable \
  --name ca-api-q3i3ucwe64hug \
  --resource-group rg-keiko-ai-chat-rag-v3 \
  --type external \
  --target-port 50505 \
  --transport auto
```

## Status prüfen
```bash
az containerapp show \
  --name ca-api-q3i3ucwe64hug \
  --resource-group rg-keiko-ai-chat-rag-v3 \
  --query "properties.configuration.ingress.fqdn" \
  --output tsv
```

## URL zur App AI-Chat-with-RAG
https://ca-api-q3i3ucwe64hug.braveground-b1825ebf.eastus2.azurecontainerapps.io/

