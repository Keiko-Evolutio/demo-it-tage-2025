"""Azure AI Search ingestion pipeline for the workshop."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient, SearchIndexerClient
from azure.search.documents.indexes.models import (
    AzureOpenAIEmbeddingSkill,
    AzureOpenAIVectorizer,
    AzureOpenAIVectorizerParameters,
    DefaultCognitiveServicesAccount,
    FieldMapping,
    FieldMappingFunction,
    HnswAlgorithmConfiguration,
    IndexProjectionMode,
    IndexingParameters,
    IndexingParametersConfiguration,
    InputFieldMappingEntry,
    OutputFieldMappingEntry,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SearchIndexer,
    SearchIndexerDataContainer,
    SearchIndexerDataSourceConnection,
    SearchIndexerIndexProjection,
    SearchIndexerIndexProjectionSelector,
    SearchIndexerIndexProjectionsParameters,
    SearchIndexerSkillset,
    SearchableField,
    SemanticConfiguration,
    SemanticField,
    SemanticPrioritizedFields,
    SemanticSearch,
    SimpleField,
    SplitSkill,
    VectorSearch,
    VectorSearchProfile,
)


@dataclass
class PipelineConfig:
    """Typed configuration for the ingestion pipeline."""

    endpoint: str
    admin_key: str
    index_name: str
    storage_connection_string: str
    storage_container: str
    openai_endpoint: str
    openai_api_key: str
    openai_deployment: str
    openai_model: str
    openai_api_version: str
    vector_dimensions: int = 1536
    chunk_size: int = 1200
    chunk_overlap: int = 150


class VectorSearchPipeline:
    """Creates the Azure AI Search resources required for the workshop."""

    def __init__(
        self,
        config: Optional[PipelineConfig] = None,
    ) -> None:
        self.config = config or self._load_from_env()

        self.credential = AzureKeyCredential(self.config.admin_key)
        self.index_client = SearchIndexClient(endpoint=self.config.endpoint, credential=self.credential)
        self.indexer_client = SearchIndexerClient(endpoint=self.config.endpoint, credential=self.credential)

        self.data_source_name = f"{self.config.index_name}-blob"
        self.skillset_name = f"{self.config.index_name}-skillset"
        self.indexer_name = f"{self.config.index_name}-indexer"

    @staticmethod
    def _load_from_env() -> PipelineConfig:
        """Build configuration from environment variables."""
        endpoint = os.getenv("VECTOR_DB_ENDPOINT")
        admin_key = os.getenv("VECTOR_DB_ADMIN_KEY")
        index_name = os.getenv("VECTOR_DB_INDEX_NAME", "workshop-documents")
        storage_connection_string = os.getenv("FILE_STORAGE_CONNECTION_STRING")
        storage_container = os.getenv("FILE_STORAGE_CONTAINER_NAME", "workshop-documents")
        openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        openai_api_key = os.getenv("AZURE_OPENAI_API_KEY")
        openai_deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
        openai_model = os.getenv("AZURE_OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
        openai_api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
        vector_dimensions = int(os.getenv("VECTOR_DB_VECTOR_DIMENSIONS", "1536"))
        chunk_size = int(os.getenv("VECTOR_DB_CHUNK_SIZE", "1200"))
        chunk_overlap = int(os.getenv("VECTOR_DB_CHUNK_OVERLAP", "150"))

        if not all([endpoint, admin_key, storage_connection_string, openai_endpoint, openai_api_key, openai_deployment]):
            raise ValueError(
                "Missing Azure configuration. Please ensure VECTOR_DB_ENDPOINT, VECTOR_DB_ADMIN_KEY, "
                "FILE_STORAGE_CONNECTION_STRING, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY and "
                "AZURE_OPENAI_EMBEDDING_DEPLOYMENT are set in tools_and_data/.env."
            )

        return PipelineConfig(
            endpoint=endpoint,
            admin_key=admin_key,
            index_name=index_name,
            storage_connection_string=storage_connection_string,
            storage_container=storage_container,
            openai_endpoint=openai_endpoint,
            openai_api_key=openai_api_key,
            openai_deployment=openai_deployment,
            openai_model=openai_model,
            openai_api_version=openai_api_version,
            vector_dimensions=vector_dimensions,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

    # -------------------------------------------------------------------------
    # Index definition
    # -------------------------------------------------------------------------

    def _build_index(self) -> SearchIndex:
        """Return the workshop index definition."""
        # NOTE: chunk_id and document_id are automatically POPULATED by Azure AI Search
        # when using index projections, but they MUST be defined in the schema.
        # They should NOT be mapped in the index projection mappings.
        # See: https://learn.microsoft.com/en-us/azure/search/search-how-to-define-index-projections
        fields = [
            SearchableField(
                name="chunk_id",
                type=SearchFieldDataType.String,
                key=True,
                filterable=True,
                analyzer_name="keyword",
            ),
            SimpleField(name="document_id", type=SearchFieldDataType.String, filterable=True, facetable=True),
            SearchableField(name="title", type=SearchFieldDataType.String, filterable=True, sortable=True),
            SearchableField(name="content", type=SearchFieldDataType.String),
            SimpleField(name="filepath", type=SearchFieldDataType.String, filterable=True, sortable=True),
            SimpleField(name="blob_uri", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="source_type", type=SearchFieldDataType.String, filterable=True, facetable=True),
            SimpleField(name="last_modified", type=SearchFieldDataType.DateTimeOffset, filterable=True, sortable=True),
            SearchField(
                name="contentVector",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                vector_search_dimensions=self.config.vector_dimensions,
                vector_search_profile_name="content-vector-profile",
            ),
        ]

        vector_search = VectorSearch(
            algorithms=[
                HnswAlgorithmConfiguration(name="contentHnsw"),
            ],
            profiles=[
                VectorSearchProfile(
                    name="content-vector-profile",
                    algorithm_configuration_name="contentHnsw",
                    vectorizer_name="content-vectorizer",
                )
            ],
            vectorizers=[
                AzureOpenAIVectorizer(
                    vectorizer_name="content-vectorizer",
                    parameters=AzureOpenAIVectorizerParameters(
                        resource_url=self.config.openai_endpoint,
                        deployment_name=self.config.openai_deployment,
                        api_key=self.config.openai_api_key,
                        model_name=self.config.openai_model,
                    ),
                )
            ],
        )

        semantic_search = SemanticSearch(
            configurations=[
                SemanticConfiguration(
                    name="workshop-semantic-config",
                    prioritized_fields=SemanticPrioritizedFields(
                        title_field=SemanticField(field_name="title"),
                        content_fields=[SemanticField(field_name="content")],
                    ),
                )
            ]
        )

        return SearchIndex(
            name=self.config.index_name,
            fields=fields,
            vector_search=vector_search,
            semantic_search=semantic_search,
        )

    def create_index(self) -> None:
        """Create the index if it doesn't exist."""
        if self.index_exists():
            print(f"      ℹ️  Index '{self.config.index_name}' existiert bereits")
            return
        index = self._build_index()
        self.index_client.create_index(index)
        print(f"      ℹ️  Index '{self.config.index_name}' wurde neu erstellt")

    def index_exists(self) -> bool:
        """Return True if the index already exists."""
        try:
            self.index_client.get_index(self.config.index_name)
            return True
        except Exception:
            return False

    # -------------------------------------------------------------------------
    # Data source & skillset
    # -------------------------------------------------------------------------

    def create_data_source(self) -> None:
        """Create or update the blob data source."""
        data_source = SearchIndexerDataSourceConnection(
            name=self.data_source_name,
            type="azureblob",
            connection_string=self.config.storage_connection_string,
            container=SearchIndexerDataContainer(name=self.config.storage_container),
            description="Workshop documents stored in Azure Blob Storage",
        )
        self.indexer_client.create_or_update_data_source_connection(data_source)

    def create_skillset(self) -> None:
        """Create the skillset used for chunking and embedding."""
        split_skill = SplitSkill(
            name="chunk-documents",
            description="Split extracted text into overlapping passages",
            context="/document",
            text_split_mode="pages",
            maximum_page_length=self.config.chunk_size,
            page_overlap_length=self.config.chunk_overlap,
            inputs=[
                InputFieldMappingEntry(name="text", source="/document/content"),
            ],
            outputs=[OutputFieldMappingEntry(name="textItems", target_name="chunks")],
        )

        embedding_skill = AzureOpenAIEmbeddingSkill(
            name="chunk-embeddings",
            description="Generate embeddings for every chunk",
            context="/document/chunks/*",
            deployment_name=self.config.openai_deployment,
            resource_url=self.config.openai_endpoint,
            api_key=self.config.openai_api_key,
            model_name=self.config.openai_model,
            dimensions=self.config.vector_dimensions,
            inputs=[InputFieldMappingEntry(name="text", source="/document/chunks/*")],
            outputs=[OutputFieldMappingEntry(name="embedding", target_name="chunkVector")],
        )

        index_projection = SearchIndexerIndexProjection(
            selectors=[
                SearchIndexerIndexProjectionSelector(
                    target_index_name=self.config.index_name,
                    parent_key_field_name="document_id",
                    source_context="/document/chunks/*",
                    mappings=[
                        # Map chunk content (full path to current chunk)
                        InputFieldMappingEntry(name="content", source="/document/chunks/*"),
                        # Map chunk vector (relative to chunk context)
                        InputFieldMappingEntry(name="contentVector", source="/document/chunks/*/chunkVector"),
                        # Map metadata from parent document (absolute paths)
                        InputFieldMappingEntry(name="title", source="/document/metadata_storage_name"),
                        InputFieldMappingEntry(name="filepath", source="/document/metadata_storage_path"),
                        InputFieldMappingEntry(name="blob_uri", source="/document/metadata_storage_path"),
                        InputFieldMappingEntry(name="last_modified", source="/document/metadata_storage_last_modified"),
                        InputFieldMappingEntry(name="source_type", source="/document/metadata_content_type"),
                    ],
                )
            ],
            parameters=SearchIndexerIndexProjectionsParameters(
                projection_mode=IndexProjectionMode.SKIP_INDEXING_PARENT_DOCUMENTS,
            ),
        )

        skillset = SearchIndexerSkillset(
            name=self.skillset_name,
            description="Chunk PDFs and create embeddings via Azure OpenAI",
            skills=[split_skill, embedding_skill],
            cognitive_services_account=DefaultCognitiveServicesAccount(description="Use Search attached cognitive services"),
            index_projection=index_projection,
        )

        self.indexer_client.create_or_update_skillset(skillset)

    # -------------------------------------------------------------------------
    # Indexer
    # -------------------------------------------------------------------------

    def create_indexer(self) -> None:
        """Create the indexer that ties data source, skillset and index together."""
        parameters = IndexingParameters(
            configuration=IndexingParametersConfiguration(
                parsing_mode="default",
                data_to_extract="contentAndMetadata",
                image_action="none",
                indexed_file_name_extensions=".pdf,.docx,.pptx,.txt",
                excluded_file_name_extensions=".png,.jpg,.jpeg",
                query_timeout=None,  # Must be None for azureblob data sources
            )
        )

        indexer = SearchIndexer(
            name=self.indexer_name,
            description="Blob → skillset → vector index pipeline",
            data_source_name=self.data_source_name,
            target_index_name=self.config.index_name,
            skillset_name=self.skillset_name,
            parameters=parameters,
            # No field_mappings or output_field_mappings needed when using index projections
            # All mappings are defined in the skillset's index projection
        )

        self.indexer_client.create_or_update_indexer(indexer)

    # -------------------------------------------------------------------------
    # Public helpers
    # -------------------------------------------------------------------------

    def bootstrap(self, *, force_recreate: bool = True) -> None:
        """
        Create or update pipeline resources.

        Args:
            force_recreate: If True (default), delete all existing resources and recreate from scratch.
                          If False, only run the indexer with reset (for incremental updates).

        Note: force_recreate=False is currently not recommended because Azure AI Search
              indexers don't support true incremental updates. Always use force_recreate=True
              to ensure all documents are properly indexed.
        """
        if force_recreate:
            print("🔧 Lösche alte Ressourcen und erstelle Pipeline neu...")

            # Delete all existing resources in reverse order
            try:
                print("  1/8 Lösche Indexer...")
                try:
                    self.indexer_client.delete_indexer(self.indexer_name)
                    print("      ✅ Indexer gelöscht")
                except:
                    print("      ℹ️  Indexer existiert nicht")
            except Exception as e:
                print(f"      ❌ Fehler beim Löschen des Indexer: {e}")

            try:
                print("  2/8 Lösche Skillset...")
                try:
                    self.indexer_client.delete_skillset(self.skillset_name)
                    print("      ✅ Skillset gelöscht")
                except:
                    print("      ℹ️  Skillset existiert nicht")
            except Exception as e:
                print(f"      ❌ Fehler beim Löschen des Skillset: {e}")

            try:
                print("  3/8 Lösche Data Source...")
                try:
                    self.indexer_client.delete_data_source_connection(self.data_source_name)
                    print("      ✅ Data Source gelöscht")
                except:
                    print("      ℹ️  Data Source existiert nicht")
            except Exception as e:
                print(f"      ❌ Fehler beim Löschen der Data Source: {e}")

            try:
                print("  4/8 Lösche Index...")
                try:
                    self.index_client.delete_index(self.config.index_name)
                    print("      ✅ Index gelöscht")
                except:
                    print("      ℹ️  Index existiert nicht")
            except Exception as e:
                print(f"      ❌ Fehler beim Löschen des Index: {e}")
        else:
            # Incremental mode: just reset and run the indexer
            print("🔧 Starte Indexer für inkrementelle Aktualisierung...")
            print("   (Hinweis: Dies funktioniert nur, wenn Pipeline bereits existiert)")

            try:
                print("  1/1 Indexer zurücksetzen und starten...")
                self.run_indexer(reset=True)
                print("      ✅ Indexer gestartet")
            except Exception as e:
                print(f"      ❌ Fehler: {e}")
                print("\n⚠️  Pipeline existiert möglicherweise nicht!")
                print("   Führe stattdessen aus: pipeline.bootstrap(force_recreate=True)")
                raise

            print("\n✅ Indexer wurde gestartet!")
            print("   Der Indexer verarbeitet jetzt neue Dokumente.")
            return

        # Create all resources (only when force_recreate=True)
        try:
            print("  5/8 Index erstellen...")
            self.create_index()
            print("      ✅ Index erstellt")
        except Exception as e:
            print(f"      ❌ Fehler beim Erstellen des Index: {e}")
            raise

        try:
            print("  6/8 Data Source erstellen...")
            self.create_data_source()
            print("      ✅ Data Source erstellt")
        except Exception as e:
            print(f"      ❌ Fehler beim Erstellen der Data Source: {e}")
            raise

        try:
            print("  7/8 Skillset erstellen...")
            self.create_skillset()
            print("      ✅ Skillset erstellt")
        except Exception as e:
            print(f"      ❌ Fehler beim Erstellen des Skillset: {e}")
            raise

        try:
            print("  8/8 Indexer erstellen und starten...")
            self.create_indexer()
            # The indexer starts automatically after creation
            print("      ✅ Indexer erstellt und gestartet")
        except Exception as e:
            print(f"      ❌ Fehler beim Erstellen des Indexer: {e}")
            raise

        print("\n✅ Pipeline erfolgreich neu erstellt!")
        print("   Der Indexer wurde gestartet und verarbeitet jetzt die Dokumente.")

    def run_indexer(self, *, reset: bool = False) -> None:
        """Trigger the indexer and optionally reset its status."""
        if reset:
            self.indexer_client.reset_indexer(self.indexer_name)
        self.indexer_client.run_indexer(self.indexer_name)

    def get_indexer_status(self) -> str:
        """Return a simple textual representation of the indexer status."""
        try:
            status = self.indexer_client.get_indexer_status(self.indexer_name)
            last_result = status.last_result
            if last_result:
                # Use correct attribute names from IndexerExecutionResult
                item_count = getattr(last_result, 'item_count', 0)
                failed_count = getattr(last_result, 'failed_item_count', 0)
                error_msg = getattr(last_result, 'error_message', '')

                result = f"Status: {last_result.status}"
                result += f"\nItems: {item_count} processed, {failed_count} failed"
                if error_msg:
                    result += f"\nError: {error_msg}"
                return result
            return f"Status: {status.status}"
        except Exception as e:
            return f"Error getting status: {e}"
