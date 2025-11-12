#!/usr/bin/env python3
"""
Script to check the Azure AI Search index schema.
"""
import asyncio
import os
from azure.identity import DefaultAzureCredential
from azure.search.documents.indexes.aio import SearchIndexClient


async def check_schema():
    """Check the index schema."""
    search_endpoint = os.environ.get('AZURE_AI_SEARCH_ENDPOINT')
    index_name = os.environ.get('AZURE_SEARCH_INDEX', 'index_sample')
    
    if not search_endpoint:
        print("ERROR: AZURE_AI_SEARCH_ENDPOINT environment variable not set")
        return False
    
    print(f"Checking schema for index '{index_name}' at {search_endpoint}")
    
    try:
        credential = DefaultAzureCredential()
        async with SearchIndexClient(endpoint=search_endpoint, credential=credential) as client:
            index = await client.get_index(index_name)
            print(f"\n✅ Index '{index_name}' exists")
            print(f"\nFields:")
            for field in index.fields:
                print(f"  - {field.name}: {field.type} (key={field.key}, filterable={field.filterable})")
            return True
    except Exception as e:
        if "not found" in str(e).lower():
            print(f"ℹ️  Index '{index_name}' does not exist")
            return True
        else:
            print(f"❌ Error checking index: {e}")
            return False
    finally:
        await credential.close()


if __name__ == "__main__":
    asyncio.run(check_schema())

