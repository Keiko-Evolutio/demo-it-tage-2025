#!/usr/bin/env python3
"""
Delete all files from Azure Blob Storage container.

This script deletes all blobs from the container.
Use with caution - this operation cannot be undone!

Usage:
    python delete_all_blobs.py [--confirm]
"""

from pathlib import Path
from dotenv import load_dotenv
import sys

WORKSHOP_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(WORKSHOP_ROOT))

from foundry_tools import BlobStorage  # noqa: E402


def delete_all_blobs(storage: BlobStorage, confirm: bool = False) -> int:
    """
    Delete all blobs from the container.

    Args:
        storage: BlobStorage instance
        confirm: If True, skip confirmation prompt

    Returns:
        Number of deleted blobs
    """
    files = storage.list_files()

    if not files:
        print("Keine Dateien im Container gefunden.")
        return 0

    print(f"\nGefundene Dateien: {len(files)}")
    print()

    # Show files to be deleted
    for blob in files:
        name = blob['name']
        size = blob['size']
        
        if size < 1024:
            size_str = f"{size} B"
        elif size < 1024 * 1024:
            size_str = f"{size / 1024:.2f} KB"
        else:
            size_str = f"{size / (1024 * 1024):.2f} MB"

        print(f"  - {name} ({size_str})")

    print()

    # Confirmation
    if not confirm:
        print("=" * 80)
        print(f"WARNUNG: {len(files)} Dateien werden PERMANENT gelöscht!")
        print("=" * 80)
        response = input("\nMöchten Sie fortfahren? (ja/nein): ")

        if response.lower() not in ['ja', 'j', 'yes', 'y']:
            print("\nAbgebrochen.")
            return 0

    # Delete all blobs
    print()
    print("Lösche Dateien...")
    deleted_count = 0

    for blob in files:
        blob_name = blob['name']
        try:
            blob_client = storage._container_client.get_blob_client(blob_name)
            blob_client.delete_blob()
            print(f"  ✓ Gelöscht: {blob_name}")
            deleted_count += 1
        except Exception as e:
            print(f"  ✗ Fehler beim Löschen von {blob_name}: {e}")

    return deleted_count


def main() -> None:
    """Main function."""
    env_path = Path(__file__).parent.parent.parent.parent / ".env"
    load_dotenv(env_path)

    # Check for --confirm flag
    confirm = "--confirm" in sys.argv

    print("=" * 80)
    print("Azure Blob Storage - Alle Dateien löschen")
    print("=" * 80)

    storage = BlobStorage()

    print(f"\nContainer: {storage.container_name}")
    print()

    deleted_count = delete_all_blobs(storage, confirm=confirm)

    print()
    print("=" * 80)
    if deleted_count > 0:
        print(f"✓ {deleted_count} Dateien erfolgreich gelöscht!")
    else:
        print("Keine Dateien gelöscht.")
    print("=" * 80)


if __name__ == "__main__":
    main()

