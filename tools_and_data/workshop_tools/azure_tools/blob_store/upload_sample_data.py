#!/usr/bin/env python3
"""
Upload the PDF sample data set to Azure Blob Storage.
"""

from pathlib import Path
from dotenv import load_dotenv
import sys

WORKSHOP_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(WORKSHOP_ROOT))

from foundry_tools import BlobStorage  # noqa: E402


def main() -> None:
    """Upload sample PDF files to blob storage."""
    env_path = Path(__file__).parent.parent.parent.parent / ".env"
    load_dotenv(env_path)

    storage = BlobStorage()

    sample_dir = Path(__file__).parent.parent.parent.parent / "data"
    files = sorted(sample_dir.glob("*.pdf"))

    if not files:
        print(f"Keine PDF-Dateien in {sample_dir} gefunden.")
        return

    print("=" * 80)
    print(f"Blob Storage Container: {storage.container_name}")
    print("=" * 80)
    print()
    print(f"Lade {len(files)} PDF-Dateien hoch...")
    print()

    uploaded = storage.upload_files(files, prefix="workshop")
    
    for i, url in enumerate(uploaded, start=1):
        filename = url.split('/')[-1]
        print(f"  {i}. {filename}")
        print(f"     {url}")
        print()

    print("=" * 80)
    print(f"Upload abgeschlossen! {len(uploaded)} Dateien hochgeladen.")
    print("=" * 80)


if __name__ == "__main__":
    main()

