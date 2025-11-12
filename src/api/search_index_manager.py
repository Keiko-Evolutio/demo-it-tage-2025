from typing import Optional

import glob
import csv
import json

from azure.core.credentials_async import AsyncTokenCredential
from azure.search.documents.aio import SearchClient
from azure.search.documents.indexes.aio import SearchIndexClient
from azure.search.documents.models import VectorizedQuery 
from azure.search.documents.indexes.models import (
    SearchField,
    SearchFieldDataType,  
    SimpleField,
    SearchIndex,
    VectorSearch,
    VectorSearchProfile,
    HnswAlgorithmConfiguration)
from azure.ai.inference.aio import EmbeddingsClient
from azure.core.exceptions import ResourceNotFoundError, HttpResponseError
from .util import ChatRequest


class SearchIndexManager:
    """
    The class for searching of context for user queries.

    :param endpoint: The search endpoint to be used.
    :param credential: The credential to be used for the search.
    :param index_name: The name of an index to get or to create.
    :param dimensions: The number of dimensions in the embedding. Set this parameter only if
                       embedding model accepts dimensions parameter.
    :param model: The embedding model to be used,
                  must be the same as one use to build the file with embeddings.
    :param embeddings_client: The embedding client.
    """
    
    MIN_DIFF_CHARACTERS_IN_LINE = 5
    MIN_LINE_LENGTH = 5
    
    def __init__(
            self,
            endpoint: str,
            credential: AsyncTokenCredential,
            index_name: str,
            dimensions: Optional[int],
            model: str,
            embeddings_client: EmbeddingsClient,
        ) -> None:
        """Constructor."""
        self._dimensions = dimensions
        self._index_name = index_name
        self._embeddings_client = embeddings_client
        self._endpoint = endpoint
        self._credential = credential
        self._index = None
        self._model = model
        self._client = None

    def _get_client(self):
        """Get search client if it is absent."""
        if self._client is None:
            self._client = SearchClient(
                endpoint=self._endpoint, index_name=self._index.name, credential=self._credential)
        return self._client

    async def search(self, message: ChatRequest) -> tuple[str, list[dict]]:
        """
        Search the message in the vector store.

        :param message: The customer question.
        :return: Tuple of (context string, list of source metadata)
        """
        self._raise_if_no_index()
        embedded_question = (await self._embeddings_client.embed(
            input=message.messages[-1].content,
            dimensions=self._dimensions,
            model=self._model
        ))['data'][0]['embedding']
        vector_query = VectorizedQuery(vector=embedded_question, k_nearest_neighbors=5, fields="embedding")
        response = await self._get_client().search(
            vector_queries=[vector_query],
            select=['token', 'source_document', 'source_url', 'chunk_index', 'page_number'],
        )

        results = []
        sources = []
        async for result in response:
            results.append(result['token'])
            # Collect source metadata
            if 'source_document' in result and result['source_document']:
                source_info = {
                    'document': result.get('source_document', ''),
                    'url': result.get('source_url', ''),
                    'chunk_index': result.get('chunk_index', 0),
                    'page_number': result.get('page_number', None)
                }
                # Avoid duplicate sources
                if source_info not in sources:
                    sources.append(source_info)

        context = "\n------\n".join(results)
        return context, sources
    
    async def upload_documents(self, embeddings_file: str) -> None:
        """
        Upload the embeggings file to index search.

        :param embeddings_file: The embeddings file to upload.
        """
        self._raise_if_no_index()
        documents = []
        index = 0
        with open(embeddings_file, newline='') as fp:
            reader = csv.DictReader(fp)
            for row in reader:
                doc = {
                    'embedId': str(index),
                    'token': row['token'],
                    'embedding': json.loads(row['embedding'])
                }
                # Add optional metadata fields if present
                if 'source_document' in row:
                    doc['source_document'] = row['source_document']
                if 'source_url' in row:
                    doc['source_url'] = row['source_url']
                if 'chunk_index' in row:
                    doc['chunk_index'] = int(row['chunk_index'])
                documents.append(doc)
                index += 1
        await self._get_client().upload_documents(documents)

    async def upload_document_chunks(
        self,
        chunks: list[dict],
        source_document: str,
        source_url: str = ""
    ) -> None:
        """
        Upload document chunks with embeddings to the index.

        :param chunks: List of chunk dictionaries with 'text' and 'page_number' keys
        :param source_document: Name of the source document
        :param source_url: URL of the source document in blob storage
        """
        self._raise_if_no_index()

        # Sanitize document name for use in embedId (Azure AI Search key requirements)
        # Keys can only contain letters, digits, underscore (_), dash (-), or equal sign (=)
        safe_document_name = source_document.replace('.', '_').replace(' ', '_')

        documents = []
        for chunk_index, chunk_data in enumerate(chunks):
            chunk_text = chunk_data['text']
            page_number = chunk_data.get('page_number', None)

            # Generate embedding for chunk
            embedding_response = await self._embeddings_client.embed(
                input=chunk_text,
                dimensions=self._dimensions,
                model=self._model
            )
            embedding = embedding_response['data'][0]['embedding']

            # Create document with metadata
            doc = {
                'embedId': f"{safe_document_name}_{chunk_index}",
                'token': chunk_text,
                'embedding': embedding,
                'source_document': source_document,
                'source_url': source_url,
                'chunk_index': chunk_index,
                'page_number': page_number
            }
            documents.append(doc)

        # Upload all chunks at once
        await self._get_client().upload_documents(documents)

    async def is_index_empty(self) -> bool:
        """
        Return True if the index is empty.

        :return: True f index is empty.
        """
        if self._index is None:
            raise ValueError(
                "Unable to perform the operation as the index is absent. "
                "To create index please call create_index")
        document_count = await self._get_client().get_document_count()
        return document_count == 0

    def _raise_if_no_index(self) -> None:
        """
        Raise the exception if the index was not created.

        :raises: ValueError
        """
        if self._index is None:
            raise ValueError(
                "Unable to perform the operation as the index is absent. "
                "To create index please call create_index")

    async def delete_index(self):
        """Delete the index from vector store."""
        self._raise_if_no_index()
        async with SearchIndexClient(endpoint=self._endpoint, credential=self._credential) as ix_client:
            await ix_client.delete_index(self._index.name)
        self._index = None

    def _check_dimensions(self, vector_index_dimensions: Optional[int] = None) -> int:
        """
        Check that the dimensions are set correctly.

        :return: the correct vector index dimensions.
        :raises: Value error if both dimensions of embedding model and vector_index_dimensions are not set
                 or both of them set and they do not equal each other.
        """
        if vector_index_dimensions is None:
            if self._dimensions is None:
                raise ValueError(
                    "No embedding dimensions were provided in neither dimensions in the constructor nor in vector_index_dimensions"
                    "Dimensions are needed to build the search index, please provide the vector_index_dimensions.")
            vector_index_dimensions = self._dimensions
        if self._dimensions is not None and vector_index_dimensions != self._dimensions:
            raise ValueError("vector_index_dimensions is different from dimensions provided to constructor.")
        return vector_index_dimensions

    async def ensure_index_created(self, vector_index_dimensions: Optional[int] = None) -> None:
        """
        Get the search index. Create the index if it does not exist.

        :param vector_index_dimensions: The number of dimensions in the vector index. This parameter is
               needed if the embedding parameter cannot be set for the given model. It can be
               figured out by loading the embeddings file, generated by build_embeddings_file,
               loading the contents of the first row and 'embedding' column as a JSON and calculating
               the length of the list obtained.
               Also please see the embedding model documentation
               https://platform.openai.com/docs/models#embeddings
        :raises: Value error if both dimensions of embedding model and vector_index_dimensions are not set
                 or both of them set and they do not equal each other.
        """
        vector_index_dimensions = self._check_dimensions(vector_index_dimensions)
        if self._index is None:
            self._index = await SearchIndexManager.get_or_create_index(
                self._endpoint,
                self._credential,
                self._index_name,
                vector_index_dimensions)

    @staticmethod
    async def index_exists(
        endpoint: str,
        credential: AsyncTokenCredential,
        index_name: str) -> bool:
        """
        Check if index exists.

        :param endpoint: The search end point to be used.
        :param credential: The credential to be used for the search.
        :param index_name: The name of an index to get or to create.
        :return: True if index already exists.
        """
        exists = False
        async with SearchIndexClient(endpoint=endpoint, credential=credential) as ix_client:
            try:
                await ix_client.get_index(index_name)
                exists = True
            except ResourceNotFoundError:
                pass
        return exists

    @staticmethod
    async def get_or_create_index(
            endpoint: str,
            credential: AsyncTokenCredential,
            index_name: str,
            dimensions: int,
        ) -> SearchIndex:
        """
        Get o create the search index.

        **Note:** If the search index with index_name exists, the embeddings_file will not be uploaded.
        :param endpoint: The search end point to be used.
        :param credential: The credential to be used for the search.
        :param index_name: The name of an index to get or to create.
        :param dimensions: The number of dimensions in the embedding.
        :return: the search index object.
        """
        index = None
        async with SearchIndexClient(endpoint=endpoint, credential=credential) as ix_client:
            try:
                index = await ix_client.get_index(index_name)
            except ResourceNotFoundError:
                pass
        if index is None:
            index = await SearchIndexManager._index_create(
                endpoint=endpoint,
                credential=credential,
                index_name=index_name,
                dimensions=dimensions
            )
        return index

    async def create_index(
        self,
        vector_index_dimensions: Optional[int] = None) -> bool:
        """
        Create index or return false if it already exists.

        :param vector_index_dimensions: The number of dimensions in the vector index. This parameter is
               needed if the embedding parameter cannot be set for the given model. It can be
               figured out by loading the embeddings file, generated by build_embeddings_file,
               loading the contents of the first row and 'embedding' column as a JSON and calculating
               the length of the list obtained.
               Also please see the embedding model documentation
               https://platform.openai.com/docs/models#embeddings
        :return: True if index was created, False otherwise.
        :raises: Value error if both dimensions of embedding model and vector_index_dimensions are not set
                 or both of them are set and they do not equal each other.
        """
        vector_index_dimensions = self._check_dimensions(vector_index_dimensions)
        try:
            self._index = await SearchIndexManager._index_create(
                endpoint=self._endpoint,
                credential=self._credential,
                index_name=self._index_name,
                dimensions=vector_index_dimensions
            )
            return True
        except HttpResponseError:
            return False
        

    @staticmethod
    async def _index_create(
        endpoint: str,
        credential: AsyncTokenCredential,
        index_name: str,
        dimensions: int) -> SearchIndex:
        """Create the index."""
        async with SearchIndexClient(endpoint=endpoint, credential=credential) as ix_client:
            fields = [
                SimpleField(name="embedId", type=SearchFieldDataType.String, key=True),
                SearchField(
                    name="embedding",
                    type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                    vector_search_dimensions=dimensions,
                    searchable=True,
                    vector_search_profile_name="embedding_config"
                ),
                SimpleField(name="token", type=SearchFieldDataType.String, hidden=False),
                SimpleField(name="source_document", type=SearchFieldDataType.String, hidden=False, filterable=True),
                SimpleField(name="source_url", type=SearchFieldDataType.String, hidden=False),
                SimpleField(name="chunk_index", type=SearchFieldDataType.Int32, hidden=False),
                SimpleField(name="page_number", type=SearchFieldDataType.Int32, hidden=False, filterable=True),
            ]
            vector_search = VectorSearch(
                profiles=[VectorSearchProfile(name="embedding_config",
                                              algorithm_configuration_name="embed-algorithms-config")],
                algorithms=[HnswAlgorithmConfiguration(name="embed-algorithms-config")],
            )
            search_index = SearchIndex(name=index_name, fields=fields, vector_search=vector_search)
            new_index = await ix_client.create_index(search_index)
        return new_index
        

    async def build_embeddings_file(
            self,
            input_directory: str,
            output_file: str,
            sentences_per_embedding: int=4
            ) -> None:
        """
        In this method we do lazy loading of nltk and download the needed data set to split

        document into tokens. This operation takes time that is why we hide import nltk under this
        method. We also do not include nltk into requirements because this method is only used
        during rag generation.
        :param dimensions: The number of dimensions in the embeddings. Must be the same as
               the one used for SearchIndexManager creation.
        :param input_directory: The directory with the embedding files.
        :param output_file: The file csv file to store embeddings.
        :param embeddings_client: The embedding client, used to create embeddings. 
                Must be the same as the one used for SearchIndexManager creation.
        :param sentences_per_embedding: The number of sentences used to build embedding.
        :param model: The embedding model to be used.
        """
        import nltk
        nltk.download('punkt')
        
        from nltk.tokenize import sent_tokenize
        # Split the data to sentence tokens.
        sentence_tokens = []
        globs = glob.glob(input_directory + '/*.md', recursive=True)
        index = 0
        for fle in globs:
            with open(fle) as f:
                for line in f:
                    line = line.strip()
                    # Skip non informative lines.
                    if len(line) < SearchIndexManager.MIN_LINE_LENGTH or len(set(line)) < SearchIndexManager.MIN_DIFF_CHARACTERS_IN_LINE:
                        continue
                    for sentence in sent_tokenize(line):
                        if index % sentences_per_embedding == 0:
                            sentence_tokens.append(sentence)
                        else:
                            sentence_tokens[-1] += ' '
                            sentence_tokens[-1] += sentence
                        index += 1
        
        
        # For each token build the embedding, which will be used in the search.
        batch_size = 2000
        with open(output_file, 'w') as fp:
            writer = csv.DictWriter(fp, fieldnames=['token', 'embedding'])
            writer.writeheader()
            for i in range(0, len(sentence_tokens), batch_size):
                emedding = (await self._embeddings_client.embed(
                    input=sentence_tokens[i:i+min(batch_size, len(sentence_tokens))],
                    dimensions=self._dimensions,
                    model=self._model
                ))["data"]
                for token, float_data in zip(sentence_tokens, emedding):
                    writer.writerow({'token': token, 'embedding': json.dumps(float_data['embedding'])})

    async def close(self):
        """Close the closeable resources, associated with SearchIndexManager."""
        if self._client:
            await self._client.close()
