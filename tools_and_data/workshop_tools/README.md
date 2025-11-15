# Workshop Tools - IT-Tage 2025

Helper-Bibliothek für den AI Agents Workshop.

## Installation

```bash
pip install -e tools_and_data/workshop_tools
```

## Verwendung

### Vector Database (Azure AI Search)

```python
from workshop_tools import VectorDB

# Initialisieren
vector_db = VectorDB()

# Suchen
results = vector_db.search("Python Tutorial", top_k=5)
for result in results:
    print(result['content'])

# Dokumente hochladen
documents = [
    {"id": "1", "content": "Python ist eine Programmiersprache"},
    {"id": "2", "content": "Azure ist eine Cloud-Plattform"}
]
vector_db.upload_documents(documents)
```

### Bing Search

```python
from workshop_tools import BingSearch

# Initialisieren
bing = BingSearch()

# Web-Suche
results = bing.search("Azure AI", count=5)
for result in results:
    print(result['name'], result['url'])

# News-Suche
news = bing.search_news("Künstliche Intelligenz", count=5)

# Bild-Suche
images = bing.search_images("Python Logo", count=5)
```

### Document Intelligence

```python
from workshop_tools import DocumentIntelligence

doc_intel = DocumentIntelligence()
result = doc_intel.analyze_document("document.pdf")
```

### Vision

```python
from workshop_tools import Vision

vision = Vision()
result = vision.analyze_image("image.jpg")
```

### Language

```python
from workshop_tools import Language

language = Language()
sentiment = language.analyze_sentiment("Das ist ein toller Workshop!")
key_phrases = language.extract_key_phrases("Azure AI ist sehr leistungsfähig")
```

### Translator

```python
from workshop_tools import Translator

translator = Translator()
result = translator.translate("Hello World", target_language="de")
```

### Content Safety

```python
from workshop_tools import ContentSafety

safety = ContentSafety()
result = safety.analyze_text("Beispieltext")
```

## Features

- Automatische Authentifizierung (Managed Identity / Service Principal)
- Rate Limiting (verhindert zu viele API-Aufrufe)
- API Keys aus Key Vault
- Einfache API
- Fehlerbehandlung

## Konfiguration

Die Bibliothek liest Konfiguration aus Environment Variables:

```bash
# Azure Authentifizierung
AZURE_TENANT_ID=...
AZURE_CLIENT_ID=...
AZURE_CLIENT_SECRET=...

# Key Vault
KEYVAULT_ENDPOINT=https://kv-ws-it-tage-2025.vault.azure.net/

# Vector DB
VECTOR_DB_ENDPOINT=https://search-workshop-it-tage-2025.search.windows.net/
VECTOR_DB_INDEX_NAME=workshop-documents

# Bing Search
BING_SEARCH_ENDPOINT=https://api.bing.microsoft.com/v7.0/search
```

Alternativ können die Werte auch direkt beim Initialisieren übergeben werden.

## Support

Bei Fragen oder Problemen wende dich an das Workshop-Team.

