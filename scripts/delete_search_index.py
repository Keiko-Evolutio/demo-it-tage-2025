#!/usr/bin/env python3
# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license.
# See LICENSE file in the project root for full license information.

"""Script to delete the Azure AI Search index."""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path to import from src
sys.path.insert(0, str(Path(__file__).parent.parent))

from azure.identity.aio import DefaultAzureCredential
from azure.search.documents.indexes.aio import SearchIndexClient


async def delete_index():
    """Delete the search index."""
    # Get configuration from environment
    search_endpoint = os.environ.get('AZURE_AI_SEARCH_ENDPOINT')
    index_name = os.environ.get('AZURE_SEARCH_INDEX', 'rag-index')
    
    if not search_endpoint:
        print("ERROR: AZURE_AI_SEARCH_ENDPOINT environment variable not set")
        return False
    
    print(f"Deleting index '{index_name}' from {search_endpoint}")
    
    try:
        credential = DefaultAzureCredential()
        async with SearchIndexClient(endpoint=search_endpoint, credential=credential) as client:
            await client.delete_index(index_name)
            print(f"✅ Successfully deleted index '{index_name}'")
            return True
    except Exception as e:
        if "not found" in str(e).lower():
            print(f"ℹ️  Index '{index_name}' does not exist (already deleted or never created)")
            return True
        else:
            print(f"❌ Error deleting index: {e}")
            return False
    finally:
        await credential.close()


if __name__ == "__main__":
    success = asyncio.run(delete_index())
    sys.exit(0 if success else 1)

