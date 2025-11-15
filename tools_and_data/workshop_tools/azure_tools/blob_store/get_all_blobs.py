#!/usr/bin/env python3
"""
List all files currently in Azure Blob Storage.
"""

from pathlib import Path
from dotenv import load_dotenv
import sys

WORKSHOP_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(WORKSHOP_ROOT))

from foundry_tools import BlobStorage  # noqa: E402


def main() -> None:
    """List all files in the blob storage container."""
    env_path = Path(__file__).parent.parent.parent.parent / ".env"
    load_dotenv(env_path)

    storage = BlobStorage()

    print("=" * 80)
    print(f"Blob Storage Container: {storage.container_name}")
    print("=" * 80)
    print()

    files = storage.list_files()

    if not files:
        print("Keine Dateien im Container gefunden.")
        return

    print(f"Gefundene Dateien: {len(files)}")
    print()

    # Sort by name
    files.sort(key=lambda x: x['name'])

    # Print table header
    print(f"{'Name':<60} {'Größe':>12} {'Letzte Änderung':<20}")
    print("-" * 95)

    # Print each file
    for blob in files:
        name = blob['name']
        size = blob['size']
        last_modified = blob['last_modified'].strftime('%Y-%m-%d %H:%M:%S') if blob['last_modified'] else 'N/A'
        
        # Format size
        if size < 1024:
            size_str = f"{size} B"
        elif size < 1024 * 1024:
            size_str = f"{size / 1024:.2f} KB"
        else:
            size_str = f"{size / (1024 * 1024):.2f} MB"

        print(f"{name:<60} {size_str:>12} {last_modified:<20}")

    print()
    print("=" * 80)
    print(f"Gesamt: {len(files)} Dateien")
    print("=" * 80)


if __name__ == "__main__":
    main()

