#!/usr/bin/env python3
"""
Script to clear all documents from the Azure AI Search index.

This script deletes all documents from the Vector DB index while keeping
the index structure intact. Useful for resetting the workshop environment.

Usage:
    python clear_index.py [--delete-index]

Options:
    --delete-index    Delete the entire index (not just documents)
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add workshop_tools to path
WORKSHOP_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(WORKSHOP_ROOT))

from foundry_tools import VectorDB  # noqa: E402


def clear_documents(vector_db: VectorDB) -> bool:
    """
    Clear all documents from the index.

    Args:
        vector_db: VectorDB instance

    Returns:
        True if successful
    """
    import time

    print("Lösche alle Dokumente aus dem Index...")

    try:
        # Get all documents (Azure AI Search max is 1000 per request)
        all_docs = vector_db.search("*", top_k=1000)

        if not all_docs:
            print("Index ist bereits leer!")
            return True

        print(f"Gefunden: {len(all_docs)} Dokumente")

        # Collect document IDs (chunk_id is the key field)
        doc_ids = []
        for doc in all_docs:
            doc_id = doc.get('chunk_id')
            if doc_id:
                doc_ids.append(str(doc_id))

        if not doc_ids:
            print("Keine Dokument-IDs gefunden!")
            return False

        # Azure AI Search has a batch limit of 1000 documents
        # Delete in batches of 100 to be safe
        batch_size = 100
        total_deleted = 0
        total_failed = 0

        print(f"\nLösche {len(doc_ids)} Dokumente in Batches von {batch_size}...")

        for i in range(0, len(doc_ids), batch_size):
            batch = doc_ids[i:i + batch_size]
            print(f"  Batch {i // batch_size + 1}/{(len(doc_ids) + batch_size - 1) // batch_size}: {len(batch)} Dokumente...")

            success = vector_db.delete_documents(batch)

            if success:
                total_deleted += len(batch)
                print(f"    Erfolgreich: {len(batch)} Dokumente gelöscht")
            else:
                total_failed += len(batch)
                print(f"    Fehler: {len(batch)} Dokumente konnten nicht gelöscht werden")

            # Small delay between batches to avoid rate limiting
            if i + batch_size < len(doc_ids):
                time.sleep(0.5)

        print(f"\nGesamt: {total_deleted} erfolgreich, {total_failed} fehlgeschlagen")

        # Wait for Azure AI Search to process the deletions
        print("\nWarte 3 Sekunden auf Verarbeitung durch Azure AI Search...")
        time.sleep(3)

        # Verify
        remaining = vector_db.get_document_count()
        if remaining == 0:
            print("Index ist jetzt leer!")
            return True
        else:
            print(f"Warnung: Noch {remaining} Dokumente im Index")
            print("Hinweis: Azure AI Search kann einige Sekunden brauchen, um Löschungen zu verarbeiten.")
            return False

    except Exception as e:
        print(f"Fehler beim Löschen: {e}")
        import traceback
        traceback.print_exc()
        return False


def delete_index(vector_db: VectorDB) -> bool:
    """
    Delete the entire index.

    Args:
        vector_db: VectorDB instance

    Returns:
        True if successful
    """
    print(f"Lösche Index '{vector_db.index_name}'...")

    if not vector_db.index_exists():
        print("Index existiert nicht!")
        return True

    success = vector_db.delete_index()

    if success:
        print("Index erfolgreich gelöscht!")
        return True
    else:
        print("Fehler beim Löschen des Index")
        return False


def main():
    """Main function."""
    # Load environment variables
    env_path = Path(__file__).parent.parent.parent.parent / ".env"
    load_dotenv(env_path)
    
    print("=" * 60)
    print("Azure AI Search - Index leeren")
    print("=" * 60)

    # Create VectorDB client
    vector_db = VectorDB()

    print(f"\nIndex: {vector_db.index_name}")
    print(f"Endpoint: {vector_db.endpoint}")

    # Check if index exists
    if not vector_db.index_exists():
        print("\nWarnung: Index existiert nicht!")
        return

    # Get current document count
    count = vector_db.get_document_count()
    print(f"Aktuelle Dokumente: {count}")
    
    # Check command line arguments
    delete_entire_index = "--delete-index" in sys.argv

    if delete_entire_index:
        print("\nWARNUNG: Der gesamte Index wird gelöscht!")
        response = input("Fortfahren? (ja/nein): ")

        if response.lower() in ['ja', 'j', 'yes', 'y']:
            success = delete_index(vector_db)
            if success:
                print("\nIndex wurde gelöscht!")
            else:
                print("\nFehler beim Löschen des Index")
                sys.exit(1)
        else:
            print("\nAbgebrochen")
            return
    else:
        if count == 0:
            print("\nIndex ist bereits leer!")
            return

        print(f"\nWARNUNG: {count} Dokumente werden gelöscht!")
        response = input("Fortfahren? (ja/nein): ")

        if response.lower() in ['ja', 'j', 'yes', 'y']:
            success = clear_documents(vector_db)
            if not success:
                print("\nFehler beim Löschen der Dokumente")
                sys.exit(1)
        else:
            print("\nAbgebrochen")
            return

    print("\n" + "=" * 60)
    print("Fertig!")
    print("=" * 60)


if __name__ == "__main__":
    main()

