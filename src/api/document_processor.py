# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license.
# See LICENSE file in the project root for full license information.

"""Document processor for extracting text from various file formats."""

import io
import logging
from typing import List, Tuple, Optional, Dict, Any
from pathlib import Path

from .util import get_logger

logger = get_logger(
    name="document_processor",
    log_level=logging.INFO,
    log_to_console=True
)


class DocumentProcessor:
    """
    Processes documents and extracts text content.
    
    Supports: PDF, DOCX, TXT, MD
    """
    
    SUPPORTED_EXTENSIONS = {'.pdf', '.docx', '.txt', '.md'}
    
    @staticmethod
    def is_supported(filename: str) -> bool:
        """
        Check if file format is supported.
        
        :param filename: Name of the file
        :return: True if supported, False otherwise
        """
        ext = Path(filename).suffix.lower()
        return ext in DocumentProcessor.SUPPORTED_EXTENSIONS
    
    @staticmethod
    async def extract_text(file_content: bytes, filename: str) -> Tuple[str, Dict[int, int]]:
        """
        Extract text from document with page mapping.

        :param file_content: Binary content of the file
        :param filename: Name of the file (used to determine type)
        :return: Tuple of (extracted text, character_position -> page_number mapping)
        """
        ext = Path(filename).suffix.lower()

        if ext == '.pdf':
            return await DocumentProcessor._extract_from_pdf(file_content)
        elif ext == '.docx':
            return await DocumentProcessor._extract_from_docx(file_content)
        elif ext in {'.txt', '.md'}:
            return await DocumentProcessor._extract_from_text(file_content)
        else:
            raise ValueError(f"Unsupported file format: {ext}")
    
    @staticmethod
    async def _extract_from_pdf(file_content: bytes) -> Tuple[str, Dict[int, int]]:
        """
        Extract text from PDF file with page mapping.

        :param file_content: Binary content of PDF
        :return: Tuple of (extracted text, character_position -> page_number mapping)
        """
        try:
            from PyPDF2 import PdfReader

            pdf_file = io.BytesIO(file_content)
            reader = PdfReader(pdf_file)

            text_parts = []
            char_to_page = {}  # Maps character position to page number
            current_pos = 0

            for page_num, page in enumerate(reader.pages, 1):
                text = page.extract_text()
                if text.strip():
                    page_text = text
                    text_parts.append(page_text)

                    # Map character positions to page number
                    page_length = len(page_text)
                    for i in range(current_pos, current_pos + page_length):
                        char_to_page[i] = page_num

                    current_pos += page_length + 2  # +2 for "\n\n" separator

            full_text = "\n\n".join(text_parts)
            return full_text, char_to_page
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}")
            raise ValueError(f"Failed to extract text from PDF: {str(e)}")
    
    @staticmethod
    async def _extract_from_docx(file_content: bytes) -> Tuple[str, Dict[int, int]]:
        """
        Extract text from DOCX file.

        :param file_content: Binary content of DOCX
        :return: Tuple of (extracted text, empty dict - DOCX has no page numbers)
        """
        try:
            from docx import Document

            docx_file = io.BytesIO(file_content)
            doc = Document(docx_file)

            text_parts = []
            for para in doc.paragraphs:
                if para.text.strip():
                    text_parts.append(para.text)

            full_text = "\n\n".join(text_parts)
            return full_text, {}  # DOCX has no page numbers
        except Exception as e:
            logger.error(f"Error extracting text from DOCX: {e}")
            raise ValueError(f"Failed to extract text from DOCX: {str(e)}")
    
    @staticmethod
    async def _extract_from_text(file_content: bytes) -> Tuple[str, Dict[int, int]]:
        """
        Extract text from plain text file.

        :param file_content: Binary content of text file
        :return: Tuple of (decoded text, empty dict - text files have no page numbers)
        """
        try:
            # Try UTF-8 first, fallback to latin-1
            try:
                text = file_content.decode('utf-8')
            except UnicodeDecodeError:
                text = file_content.decode('latin-1')
            return text, {}  # Text files have no page numbers
        except Exception as e:
            logger.error(f"Error extracting text from text file: {e}")
            raise ValueError(f"Failed to extract text from text file: {str(e)}")
    
    @staticmethod
    async def chunk_text(
        text: str,
        char_to_page: Dict[int, int],
        sentences_per_chunk: int = 4
    ) -> List[Dict[str, Any]]:
        """
        Split text into chunks based on sentences with page number tracking.

        :param text: Text to chunk
        :param char_to_page: Mapping of character position to page number
        :param sentences_per_chunk: Number of sentences per chunk
        :return: List of chunk dictionaries with 'text' and 'page_number' keys
        """
        try:
            import nltk
            try:
                nltk.data.find('tokenizers/punkt')
            except LookupError:
                nltk.download('punkt', quiet=True)

            sentences = nltk.sent_tokenize(text)

            chunks = []
            current_pos = 0

            for i in range(0, len(sentences), sentences_per_chunk):
                chunk_text = ' '.join(sentences[i:i + sentences_per_chunk])
                if chunk_text.strip():
                    # Find the page number for this chunk (use the first character's page)
                    chunk_start_pos = text.find(chunk_text, current_pos)
                    page_number = char_to_page.get(chunk_start_pos, None)

                    chunks.append({
                        'text': chunk_text,
                        'page_number': page_number
                    })

                    current_pos = chunk_start_pos + len(chunk_text)

            return chunks
        except Exception as e:
            logger.error(f"Error chunking text: {e}")
            # Fallback: simple split by newlines without page numbers
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            return [
                {'text': '\n'.join(lines[i:i+10]), 'page_number': None}
                for i in range(0, len(lines), 10)
            ]

