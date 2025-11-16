#!/usr/bin/env python3
"""
Upload Sample Documents to Azure Blob Storage for Document Intelligence Workshop

This script uploads sample documents from the sample_data directory to Azure Blob Storage.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient

# Colors for terminal output
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color


def print_colored(message: str, color: str = Colors.NC):
    """Print colored message to terminal"""
    print(f"{color}{message}{Colors.NC}")


def main():
    """Main function to upload sample documents"""
    
    # Load environment variables
    env_path = Path(__file__).parent.parent.parent / '.env'
    if not env_path.exists():
        print_colored(f"Error: .env file not found at {env_path}", Colors.RED)
        sys.exit(1)
    
    load_dotenv(env_path)
    
    # Get configuration from environment
    storage_connection_string = os.getenv('DOC_INTEL_STORAGE_CONNECTION_STRING')
    container_name = os.getenv('DOC_INTEL_CONTAINER_NAME')
    
    if not storage_connection_string or not container_name:
        print_colored("Error: DOC_INTEL_STORAGE_CONNECTION_STRING and DOC_INTEL_CONTAINER_NAME must be set in .env", Colors.RED)
        sys.exit(1)
    
    # Sample data directory
    sample_data_dir = Path(__file__).parent.parent / 'sample_data'
    
    if not sample_data_dir.exists():
        print_colored(f"Creating sample_data directory: {sample_data_dir}", Colors.YELLOW)
        sample_data_dir.mkdir(parents=True, exist_ok=True)
    
    # Get list of files to upload
    files_to_upload = list(sample_data_dir.glob('*'))
    files_to_upload = [f for f in files_to_upload if f.is_file()]
    
    if not files_to_upload:
        print_colored("No files found in sample_data directory", Colors.YELLOW)
        print_colored(f"Please add sample documents to: {sample_data_dir}", Colors.YELLOW)
        print_colored("\nSupported file types:", Colors.BLUE)
        print_colored("  - PDF (.pdf)", Colors.BLUE)
        print_colored("  - Images (.jpg, .jpeg, .png, .bmp, .tiff)", Colors.BLUE)
        print_colored("  - Office documents (.docx, .xlsx, .pptx)", Colors.BLUE)
        sys.exit(0)
    
    # Initialize Blob Service Client
    print_colored("=" * 80, Colors.BLUE)
    print_colored("Upload Sample Documents to Azure Blob Storage", Colors.BLUE)
    print_colored("=" * 80, Colors.BLUE)
    print()
    print_colored(f"Container: {container_name}", Colors.YELLOW)
    print_colored(f"Files to upload: {len(files_to_upload)}", Colors.YELLOW)
    print()
    
    try:
        blob_service_client = BlobServiceClient.from_connection_string(storage_connection_string)
        container_client = blob_service_client.get_container_client(container_name)
        
        # Check if container exists
        if not container_client.exists():
            print_colored(f"Container '{container_name}' does not exist. Creating...", Colors.YELLOW)
            container_client.create_container()
            print_colored(f"✓ Container created", Colors.GREEN)
        
        # Upload files
        uploaded_count = 0
        skipped_count = 0
        
        for file_path in files_to_upload:
            blob_name = file_path.name
            blob_client = container_client.get_blob_client(blob_name)
            
            # Check if blob already exists
            if blob_client.exists():
                print_colored(f"⚠ Skipping {blob_name} (already exists)", Colors.YELLOW)
                skipped_count += 1
                continue
            
            # Upload file
            print_colored(f"Uploading {blob_name}...", Colors.BLUE)
            with open(file_path, 'rb') as data:
                blob_client.upload_blob(data)
            
            file_size_kb = file_path.stat().st_size / 1024
            print_colored(f"✓ Uploaded {blob_name} ({file_size_kb:.2f} KB)", Colors.GREEN)
            uploaded_count += 1
        
        # Summary
        print()
        print_colored("=" * 80, Colors.GREEN)
        print_colored("Upload completed!", Colors.GREEN)
        print_colored("=" * 80, Colors.GREEN)
        print_colored(f"Uploaded: {uploaded_count} files", Colors.GREEN)
        print_colored(f"Skipped: {skipped_count} files", Colors.YELLOW)
        print()
        
        # List all blobs in container
        print_colored("Documents in Blob Storage:", Colors.BLUE)
        print_colored("-" * 80, Colors.BLUE)
        
        blobs = list(container_client.list_blobs())
        for idx, blob in enumerate(blobs, start=1):
            size_kb = blob.size / 1024
            print_colored(f"{idx}. {blob.name} ({size_kb:.2f} KB)", Colors.BLUE)
        
        print()
        print_colored("Next steps:", Colors.YELLOW)
        print_colored("  1. Run the example notebooks:", Colors.YELLOW)
        print_colored("     tools_and_data/document_intelligence/examples/01_document_analysis.ipynb", Colors.BLUE)
        print_colored("     tools_and_data/document_intelligence/examples/02_prebuilt_models.ipynb", Colors.BLUE)
        print()
        
    except Exception as e:
        print_colored(f"Error: {str(e)}", Colors.RED)
        sys.exit(1)


if __name__ == '__main__':
    main()

