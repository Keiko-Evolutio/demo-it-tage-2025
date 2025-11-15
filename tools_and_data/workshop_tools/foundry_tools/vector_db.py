"""Vector Database (Azure AI Search) helper."""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import ResourceNotFoundError
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    AzureOpenAIVectorizer,
    AzureOpenAIVectorizerParameters,
    HnswAlgorithmConfiguration,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SearchableField,
    SimpleField,
    VectorSearch,
    VectorSearchProfile,
)
from azure.search.documents.models import VectorizedQuery
from dotenv import load_dotenv

from .auth import get_auth
from .rate_limiter import get_rate_limiter


class VectorDB:
    """
    Helper-Klasse für Azure AI Search (Vector Database).
    
    Ermöglicht einfache Vector Search und Hybrid Search.
    Authentifizierung und Rate Limiting sind bereits integriert.
    
    Beispiel:
        vector_db = VectorDB()
        results = vector_db.search("Python Tutorial", top_k=5)
        for result in results:
            print(result['content'])
    """
    
    def __init__(
        self,
        endpoint: Optional[str] = None,
        index_name: Optional[str] = None,
        api_key: Optional[str] = None,
        vector_field: Optional[str] = None,
    ):
        """
        Initialisiert den Vector DB Client.

        Args:
            endpoint: Azure AI Search Endpoint (optional, aus ENV)
            index_name: Name des Search Index (optional, aus ENV)
            api_key: Admin API Key (optional, aus ENV)
        """
        # Load .env file if it exists
        env_path = Path(__file__).parent.parent.parent / ".env"
        if env_path.exists():
            load_dotenv(env_path)

        # Konfiguration aus Environment oder Parameter
        self.endpoint = endpoint or os.getenv(
            "VECTOR_DB_ENDPOINT",
            "https://search-workshop-it-tage-2025.search.windows.net/"
        )
        self.index_name = index_name or os.getenv("VECTOR_DB_INDEX_NAME", "workshop-documents")

        # API Key aus Environment oder Parameter
        self.api_key = api_key or os.getenv("VECTOR_DB_ADMIN_KEY")

        # Authentifizierung: Bevorzuge API Key, fallback auf Azure AD
        if self.api_key:
            self.credential = AzureKeyCredential(self.api_key)
        else:
            self.auth = get_auth()
            self.credential = self.auth.credential

        # Rate Limiter (60 Requests/Minute)
        self.rate_limiter = get_rate_limiter("vector_db", max_requests=60)

        # Rate Limiter for Azure OpenAI Embeddings (10 Requests/Minute to be safe)
        self.openai_rate_limiter = get_rate_limiter("azure_openai_embeddings", max_requests=10)

        # Vector field name
        self.vector_field = vector_field or os.getenv("VECTOR_DB_VECTOR_FIELD", "contentVector")

        # Azure OpenAI Konfiguration (für Query-Embeddings)
        self.openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.openai_api_key = os.getenv("AZURE_OPENAI_API_KEY")
        self.openai_deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
        self.openai_model = os.getenv("AZURE_OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
        self.openai_api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")

        # Search Client initialisieren
        self._client = None
        self._index_client = None
    
    @property
    def client(self) -> SearchClient:
        """Lazy-loaded Search Client."""
        if self._client is None:
            self._client = SearchClient(
                endpoint=self.endpoint,
                index_name=self.index_name,
                credential=self.credential
            )
        return self._client

    @property
    def index_client(self) -> SearchIndexClient:
        """Lazy-loaded Index Client."""
        if self._index_client is None:
            self._index_client = SearchIndexClient(
                endpoint=self.endpoint,
                credential=self.credential
            )
        return self._index_client

    def index_exists(self) -> bool:
        """
        Prüft, ob der Index existiert.

        Returns:
            True wenn Index existiert, sonst False
        """
        try:
            self.index_client.get_index(self.index_name)
            return True
        except ResourceNotFoundError:
            return False
        except Exception as e:
            print(f"Fehler beim Prüfen des Index: {e}")
            return False

    def create_index(self, fields: Optional[List] = None) -> bool:
        """
        Erstellt einen neuen Index.

        Args:
            fields: Liste von Feldern (optional, verwendet Standard-Schema)

        Returns:
            True bei Erfolg
        """
        try:
            if fields is None:
                fields = [
                    SimpleField(name="chunk_id", type=SearchFieldDataType.String, key=True, filterable=True),
                    SimpleField(name="document_id", type=SearchFieldDataType.String, filterable=True, facetable=True),
                    SearchableField(name="title", type=SearchFieldDataType.String, sortable=True, filterable=True),
                    SearchableField(name="content", type=SearchFieldDataType.String),
                    SimpleField(name="filepath", type=SearchFieldDataType.String, filterable=True, sortable=True),
                    SimpleField(name="blob_uri", type=SearchFieldDataType.String, filterable=True),
                    SimpleField(name="chunk_index", type=SearchFieldDataType.Int32, filterable=True, sortable=True),
                    SimpleField(name="chunk_page", type=SearchFieldDataType.Int32, filterable=True, sortable=True),
                    SimpleField(name="source_type", type=SearchFieldDataType.String, filterable=True),
                    SimpleField(name="last_modified", type=SearchFieldDataType.DateTimeOffset, filterable=True, sortable=True),
                    SearchField(
                        name=self.vector_field,
                        type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                        searchable=True,
                        vector_search_dimensions=int(os.getenv("VECTOR_DB_VECTOR_DIMENSIONS", "1536")),
                        vector_search_profile_name="content-vector-profile",
                    ),
                ]

            vector_search = VectorSearch(
                algorithms=[HnswAlgorithmConfiguration(name="contentHnsw")],
                profiles=[
                    VectorSearchProfile(
                        name="content-vector-profile",
                        algorithm_configuration_name="contentHnsw",
                        vectorizer_name="content-vectorizer",
                    )
                ],
            )

            vectorizers = [
                AzureOpenAIVectorizer(
                    vectorizer_name="content-vectorizer",
                    parameters=AzureOpenAIVectorizerParameters(
                        resource_url=self.openai_endpoint,
                        deployment_name=self.openai_deployment,
                        api_key=self.openai_api_key,
                        model_name=self.openai_model,
                    ),
                )
            ]

            index = SearchIndex(name=self.index_name, fields=fields, vector_search=vector_search, vectorizers=vectorizers)
            self.index_client.create_index(index)
            print(f"Index '{self.index_name}' erfolgreich erstellt!")
            return True

        except Exception as e:
            print(f"Fehler beim Erstellen des Index: {e}")
            return False

    def delete_index(self) -> bool:
        """
        Löscht den Index.

        Returns:
            True bei Erfolg
        """
        try:
            self.index_client.delete_index(self.index_name)
            print(f"Index '{self.index_name}' erfolgreich gelöscht!")
            return True
        except Exception as e:
            print(f"Fehler beim Löschen des Index: {e}")
            return False
    
    def search(
        self,
        query: Optional[str] = None,
        top_k: int = 5,
        vector_query: Optional[List[float]] = None,
        vector_text: Optional[str] = None,
        filter_expression: Optional[str] = None,
        vector_weight: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        Führt eine Suche im Vector DB durch.
        
        Args:
            query: Suchtext
            top_k: Anzahl der Ergebnisse
            vector_query: Optional: Vector für Vector Search
            filter_expression: Optional: OData Filter
            
        Returns:
            Liste von Suchergebnissen
        """
        self.rate_limiter.acquire()

        try:
            search_text = query or ""
            vector_queries = None

            if vector_text and not vector_query:
                vector_query = self._embed_text(vector_text)

            if vector_query:
                vector_queries = [
                    VectorizedQuery(
                        vector=vector_query,
                        k_nearest_neighbors=top_k,
                        fields=self.vector_field,
                        weight=vector_weight,
                    )
                ]

            results = self.client.search(
                search_text=search_text,
                top=top_k,
                filter=filter_expression,
                vector_queries=vector_queries,
            )

            return [dict(result) for result in results]

        except Exception as e:
            print(f"Fehler bei der Suche: {e}")
            return []

    def _embed_text(self, text: str) -> List[float]:
        """Generate embeddings for a query using Azure OpenAI with retry logic."""
        if not all([self.openai_endpoint, self.openai_api_key, self.openai_deployment]):
            raise ValueError("Azure OpenAI Konfiguration fehlt. Bitte .env aktualisieren.")

        # Use rate limiter to prevent hitting API limits
        self.openai_rate_limiter.acquire()

        url = (
            f"{self.openai_endpoint}/openai/deployments/{self.openai_deployment}/embeddings"
            f"?api-version={self.openai_api_version}"
        )
        headers = {
            "Content-Type": "application/json",
            "api-key": self.openai_api_key,
        }
        payload = {"input": text, "model": self.openai_model}

        # Retry logic for rate limiting with exponential backoff
        max_retries = 5
        base_delay = 5  # Start with 5 seconds

        for attempt in range(max_retries):
            try:
                response = requests.post(url, json=payload, headers=headers, timeout=30)
                response.raise_for_status()
                data = response.json()
                return data["data"][0]["embedding"]
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:
                    if attempt < max_retries - 1:
                        # Exponential backoff: 5s, 10s, 20s, 40s
                        wait_time = base_delay * (2 ** attempt)

                        # Check if response has Retry-After header
                        retry_after = e.response.headers.get('Retry-After')
                        if retry_after:
                            try:
                                wait_time = max(wait_time, int(retry_after))
                            except ValueError:
                                pass

                        print(f"⚠️  Rate limit erreicht (429). Warte {wait_time} Sekunden... (Versuch {attempt + 1}/{max_retries})")
                        import time
                        time.sleep(wait_time)
                    else:
                        print(f"❌ Rate limit nach {max_retries} Versuchen immer noch aktiv!")
                        raise
                else:
                    raise
    
    def chunk_document(
        self,
        document: Dict[str, Any],
        max_chunk_size: int = 30000
    ) -> List[Dict[str, Any]]:
        """
        Teilt ein großes Dokument in kleinere Chunks auf.

        Args:
            document: Dokument-Dictionary
            max_chunk_size: Maximale Größe pro Chunk in Zeichen (default: 30.000)

        Returns:
            Liste von Chunk-Dokumenten
        """
        content = document.get("content", "")

        # Wenn Dokument klein genug ist, direkt zurückgeben
        if len(content) <= max_chunk_size:
            return [document]

        # Dokument in Chunks aufteilen
        chunks = []
        num_chunks = (len(content) + max_chunk_size - 1) // max_chunk_size

        for i in range(num_chunks):
            start = i * max_chunk_size
            end = min((i + 1) * max_chunk_size, len(content))
            chunk_content = content[start:end]

            # Chunk-Dokument erstellen
            chunk_doc = document.copy()
            chunk_doc["id"] = f"{document['id']}_chunk_{i+1}"
            chunk_doc["content"] = chunk_content
            chunk_doc["chunk_index"] = i + 1
            chunk_doc["total_chunks"] = num_chunks
            chunk_doc["original_id"] = document["id"]

            chunks.append(chunk_doc)

        return chunks

    def upload_documents(self, documents: List[Dict[str, Any]], auto_chunk: bool = True) -> bool:
        """
        Lädt Dokumente in den Index hoch.

        Args:
            documents: Liste von Dokumenten (Dicts)
            auto_chunk: Automatisch große Dokumente in Chunks aufteilen (default: True)

        Returns:
            True bei Erfolg
        """
        # Automatisches Chunking für große Dokumente
        if auto_chunk:
            chunked_documents = []
            for doc in documents:
                chunks = self.chunk_document(doc)
                chunked_documents.extend(chunks)

                if len(chunks) > 1:
                    print(f"Dokument '{doc.get('title', doc.get('id'))}' in {len(chunks)} Chunks aufgeteilt")

            documents = chunked_documents

        # Rate Limiting
        self.rate_limiter.acquire()

        try:
            result = self.client.upload_documents(documents=documents)

            # Detaillierte Fehlerausgabe
            succeeded = 0
            failed = 0
            for r in result:
                if r.succeeded:
                    succeeded += 1
                else:
                    failed += 1
                    print(f"Fehler beim Hochladen von Dokument: {r.key}")
                    print(f"  Status Code: {r.status_code}")
                    print(f"  Error Message: {r.error_message}")

            print(f"Upload-Ergebnis: {succeeded} erfolgreich, {failed} fehlgeschlagen")

            return all(r.succeeded for r in result)
        except Exception as e:
            print(f"Fehler beim Hochladen: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def delete_documents(self, document_ids: List[str]) -> bool:
        """
        Löscht Dokumente aus dem Index.

        Args:
            document_ids: Liste von Dokument-IDs (chunk_id Werte)

        Returns:
            True bei Erfolg
        """
        # Rate Limiting
        self.rate_limiter.acquire()

        try:
            documents = [{"chunk_id": doc_id} for doc_id in document_ids]
            result = self.client.delete_documents(documents=documents)

            # Check results
            succeeded = sum(1 for r in result if r.succeeded)
            failed = sum(1 for r in result if not r.succeeded)

            # Print errors if any
            if failed > 0:
                print(f"Warnung: {failed} von {len(document_ids)} Dokumenten konnten nicht gelöscht werden:")
                for r in result:
                    if not r.succeeded:
                        print(f"  - {r.key}: {r.error_message} (Status: {r.status_code})")

            return all(r.succeeded for r in result)
        except Exception as e:
            print(f"Fehler beim Löschen: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def get_document_count(self) -> int:
        """
        Gibt die Anzahl der Dokumente im Index zurück.

        Returns:
            Anzahl der Dokumente
        """
        try:
            return self.client.get_document_count()
        except Exception as e:
            print(f"Fehler beim Abrufen der Dokumentanzahl: {e}")
            return 0

    def get_indexed_documents(self) -> List[str]:
        """
        Gibt eine Liste aller indexierten Dokumente zurück (basierend auf blob_uri).

        Returns:
            Liste von blob_uri Werten (vollständige Blob-URLs)
        """
        try:
            # Get all unique blob_uris from the index
            results = self.client.search(
                search_text="*",
                select=["blob_uri"],
                top=10000  # Large number to get all documents
            )

            # Extract unique blob_uris
            blob_uris = set()
            for result in results:
                blob_uri = result.get("blob_uri")
                if blob_uri:
                    blob_uris.add(blob_uri)

            return sorted(list(blob_uris))
        except Exception as e:
            print(f"Fehler beim Abrufen der indexierten Dokumente: {e}")
            return []
