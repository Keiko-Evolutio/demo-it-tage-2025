# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license.
# See LICENSE file in the project root for full license information.

"""Document processor for extracting text from various file formats."""

import io
import logging
from typing import List, Tuple, Optional
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
    async def extract_text(file_content: bytes, filename: str) -> str:
        """
        Extract text from document.
        
        :param file_content: Binary content of the file
        :param filename: Name of the file (used to determine type)
        :return: Extracted text content
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
    async def _extract_from_pdf(file_content: bytes) -> str:
        """
        Extract text from PDF file.
        
        :param file_content: Binary content of PDF
        :return: Extracted text
        """
        try:
            from PyPDF2 import PdfReader
            
            pdf_file = io.BytesIO(file_content)
            reader = PdfReader(pdf_file)
            
            text_parts = []
            for page_num, page in enumerate(reader.pages, 1):
                text = page.extract_text()
                if text.strip():
                    text_parts.append(f"[Page {page_num}]\n{text}")
            
            return "\n\n".join(text_parts)
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}")
            raise ValueError(f"Failed to extract text from PDF: {str(e)}")
    
    @staticmethod
    async def _extract_from_docx(file_content: bytes) -> str:
        """
        Extract text from DOCX file.
        
        :param file_content: Binary content of DOCX
        :return: Extracted text
        """
        try:
            from docx import Document
            
            docx_file = io.BytesIO(file_content)
            doc = Document(docx_file)
            
            text_parts = []
            for para in doc.paragraphs:
                if para.text.strip():
                    text_parts.append(para.text)
            
            return "\n\n".join(text_parts)
        except Exception as e:
            logger.error(f"Error extracting text from DOCX: {e}")
            raise ValueError(f"Failed to extract text from DOCX: {str(e)}")
    
    @staticmethod
    async def _extract_from_text(file_content: bytes) -> str:
        """
        Extract text from plain text file.
        
        :param file_content: Binary content of text file
        :return: Decoded text
        """
        try:
            # Try UTF-8 first, fallback to latin-1
            try:
                return file_content.decode('utf-8')
            except UnicodeDecodeError:
                return file_content.decode('latin-1')
        except Exception as e:
            logger.error(f"Error extracting text from text file: {e}")
            raise ValueError(f"Failed to extract text from text file: {str(e)}")
    
    @staticmethod
    async def chunk_text(text: str, sentences_per_chunk: int = 4) -> List[str]:
        """
        Split text into chunks based on sentences.
        
        :param text: Text to chunk
        :param sentences_per_chunk: Number of sentences per chunk
        :return: List of text chunks
        """
        try:
            import nltk
            try:
                nltk.data.find('tokenizers/punkt')
            except LookupError:
                nltk.download('punkt', quiet=True)
            
            sentences = nltk.sent_tokenize(text)
            
            chunks = []
            for i in range(0, len(sentences), sentences_per_chunk):
                chunk = ' '.join(sentences[i:i + sentences_per_chunk])
                if chunk.strip():
                    chunks.append(chunk)
            
            return chunks
        except Exception as e:
            logger.error(f"Error chunking text: {e}")
            # Fallback: simple split by newlines
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            return ['\n'.join(lines[i:i+10]) for i in range(0, len(lines), 10)]

