# App Control Commands

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

