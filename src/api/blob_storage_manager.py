# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license.
# See LICENSE file in the project root for full license information.

"""Blob storage manager for document uploads."""

import logging
from typing import Optional
from datetime import datetime, timedelta

from azure.core.credentials_async import AsyncTokenCredential
from azure.storage.blob.aio import BlobServiceClient, ContainerClient
from azure.storage.blob import BlobSasPermissions, generate_blob_sas
from azure.core.exceptions import ResourceExistsError

from .util import get_logger

logger = get_logger(
    name="blob_storage_manager",
    log_level=logging.INFO,
    log_to_console=True
)


class BlobStorageManager:
    """
    Manages document uploads to Azure Blob Storage.
    
    :param blob_endpoint: Azure Storage Blob endpoint
    :param credential: Azure credential for authentication
    :param container_name: Name of the blob container (default: 'documents')
    """
    
    def __init__(
        self,
        blob_endpoint: str,
        credential: AsyncTokenCredential,
        container_name: str = 'documents',
        storage_account_name: Optional[str] = None
    ) -> None:
        """Initialize blob storage manager."""
        self._blob_endpoint = blob_endpoint
        self._credential = credential
        self._container_name = container_name
        self._storage_account_name = storage_account_name
        self._blob_service_client: Optional[BlobServiceClient] = None
        self._container_client: Optional[ContainerClient] = None
    
    async def _get_blob_service_client(self) -> BlobServiceClient:
        """Get or create blob service client."""
        if self._blob_service_client is None:
            self._blob_service_client = BlobServiceClient(
                account_url=self._blob_endpoint,
                credential=self._credential
            )
        return self._blob_service_client
    
    async def _get_container_client(self) -> ContainerClient:
        """Get or create container client."""
        if self._container_client is None:
            blob_service_client = await self._get_blob_service_client()
            self._container_client = blob_service_client.get_container_client(
                self._container_name
            )
        return self._container_client
    
    async def ensure_container_exists(self) -> None:
        """
        Ensure the blob container exists, create if not.
        """
        try:
            container_client = await self._get_container_client()
            await container_client.create_container()
            logger.info(f"Created blob container: {self._container_name}")
        except ResourceExistsError:
            logger.info(f"Blob container already exists: {self._container_name}")
        except Exception as e:
            logger.error(f"Error ensuring container exists: {e}")
            raise
    
    async def upload_document(
        self,
        filename: str,
        file_content: bytes,
        metadata: Optional[dict] = None
    ) -> str:
        """
        Upload document to blob storage.
        
        :param filename: Name of the file
        :param file_content: Binary content of the file
        :param metadata: Optional metadata to attach to the blob
        :return: Blob URL
        """
        try:
            # Generate unique blob name with timestamp
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            blob_name = f"{timestamp}_{filename}"
            
            container_client = await self._get_container_client()
            blob_client = container_client.get_blob_client(blob_name)
            
            # Upload blob
            await blob_client.upload_blob(
                file_content,
                overwrite=True,
                metadata=metadata or {}
            )
            
            blob_url = blob_client.url
            logger.info(f"Uploaded document to blob storage: {blob_name}")
            
            return blob_url
        except Exception as e:
            logger.error(f"Error uploading document to blob storage: {e}")
            raise
    
    async def delete_document(self, blob_name: str) -> None:
        """
        Delete document from blob storage.
        
        :param blob_name: Name of the blob to delete
        """
        try:
            container_client = await self._get_container_client()
            blob_client = container_client.get_blob_client(blob_name)
            await blob_client.delete_blob()
            logger.info(f"Deleted document from blob storage: {blob_name}")
        except Exception as e:
            logger.error(f"Error deleting document from blob storage: {e}")
            raise
    
    async def list_documents(self) -> list:
        """
        List all documents in the container.

        :return: List of blob names
        """
        try:
            container_client = await self._get_container_client()
            blobs = []
            async for blob in container_client.list_blobs():
                blobs.append({
                    'name': blob.name,
                    'size': blob.size,
                    'created': blob.creation_time,
                    'metadata': blob.metadata
                })
            return blobs
        except Exception as e:
            logger.error(f"Error listing documents from blob storage: {e}")
            raise

    async def generate_sas_url(
        self,
        blob_name: str,
        expiry_hours: int = 1
    ) -> str:
        """
        Generate a SAS URL for a blob with read permissions.

        :param blob_name: Name of the blob
        :param expiry_hours: Number of hours until the SAS token expires (default: 1)
        :return: Blob URL with SAS token
        """
        try:
            # Get account key from blob service client
            blob_service_client = await self._get_blob_service_client()

            # For managed identity, we need to use user delegation key
            # Get user delegation key
            delegation_key = await blob_service_client.get_user_delegation_key(
                key_start_time=datetime.utcnow(),
                key_expiry_time=datetime.utcnow() + timedelta(hours=expiry_hours)
            )

            # Generate SAS token using user delegation key
            from azure.storage.blob import generate_blob_sas, UserDelegationKey, ContentSettings

            # Extract original filename from blob_name (remove timestamp prefix)
            # Format: 20251112_103403_Azure-AI-Foundry...pdf
            original_filename = blob_name
            if '_' in blob_name:
                parts = blob_name.split('_', 2)
                if len(parts) >= 3:
                    original_filename = parts[2]

            sas_token = generate_blob_sas(
                account_name=self._storage_account_name,
                container_name=self._container_name,
                blob_name=blob_name,
                user_delegation_key=delegation_key,
                permission=BlobSasPermissions(read=True),
                expiry=datetime.utcnow() + timedelta(hours=expiry_hours),
                content_disposition=f'inline; filename="{original_filename}"',  # Display in browser with filename
                content_type='application/pdf'  # Set correct MIME type for PDF
            )

            # Construct full URL with SAS token
            blob_url = f"{self._blob_endpoint}{self._container_name}/{blob_name}?{sas_token}"

            return blob_url
        except Exception as e:
            logger.error(f"Error generating SAS URL for blob {blob_name}: {e}")
            raise

    async def close(self) -> None:
        """Close blob service client."""
        if self._blob_service_client:
            await self._blob_service_client.close()

