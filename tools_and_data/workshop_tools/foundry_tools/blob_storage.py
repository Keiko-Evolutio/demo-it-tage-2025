"""Blob Storage Helper for Workshop Tools."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, Optional

from azure.storage.blob import BlobServiceClient, ContainerClient


class BlobStorage:
    """Utility class to interact with the workshop's Azure Blob Storage container."""

    def __init__(
        self,
        connection_string: Optional[str] = None,
        container_name: Optional[str] = None,
    ) -> None:
        possible_env_vars = [
            "FILE_STORAGE_CONNECTION_STRING",
            "STORAGE_CONNECTION_STRING",
            "AZURE_STORAGE_CONNECTION_STRING",
        ]
        conn = connection_string
        if conn is None:
            for var in possible_env_vars:
                conn = os.getenv(var)
                if conn:
                    break

        self.connection_string = conn
        self.container_name = container_name or os.getenv("FILE_STORAGE_CONTAINER_NAME", "workshop-documents")

        if not self.connection_string:
            hint = (
                "Kein Storage Connection String gefunden. "
                "Bitte FILE_STORAGE_CONNECTION_STRING (oder STORAGE_CONNECTION_STRING) in tools_and_data/.env setzen."
            )
            raise ValueError(hint)

        self._service_client = BlobServiceClient.from_connection_string(self.connection_string)
        self._container_client: ContainerClient = self._service_client.get_container_client(self.container_name)

    def ensure_container(self) -> None:
        """Create the workshop container if it does not exist."""
        try:
            self._container_client.create_container()
        except Exception:
            # Container already exists
            pass

    def upload_file(self, file_path: str | Path, *, blob_name: Optional[str] = None, metadata: Optional[dict] = None) -> str:
        """
        Upload a local file to the container.

        Returns the blob URL.
        """
        file_path = Path(file_path)
        if not blob_name:
            blob_name = file_path.name

        self.ensure_container()
        blob_client = self._container_client.get_blob_client(blob_name)
        with file_path.open("rb") as handle:
            blob_client.upload_blob(handle, overwrite=True, metadata=metadata)
        return blob_client.url

    def upload_files(
        self,
        files: Iterable[Path],
        *,
        prefix: Optional[str] = None,
    ) -> list[str]:
        """Upload multiple files and return their blob URLs."""
        uploaded: list[str] = []
        for path in files:
            blob_name = f"{prefix.rstrip('/')}/{path.name}" if prefix else path.name
            uploaded.append(self.upload_file(path, blob_name=blob_name))
        return uploaded

    def list_files(self) -> list[dict]:
        """Return simple metadata for each blob in the container."""
        blobs = []
        for blob in self._container_client.list_blobs():
            blob_client = self._container_client.get_blob_client(blob.name)
            blobs.append(
                {
                    "name": blob.name,
                    "size": blob.size,
                    "last_modified": blob.last_modified,
                    "metadata": blob.metadata or {},
                    "url": blob_client.url,  # Add blob URL
                }
            )
        return blobs

    def delete_blob(self, blob_name: str) -> None:
        """Delete a blob from the container."""
        blob_client = self._container_client.get_blob_client(blob_name)
        blob_client.delete_blob()
