"""
Document Parser Service
=======================
Handles extraction of safety observation text from uploaded files.
Supported formats: PDF, DOCX, TXT, CSV, XLSX.
"""

import os
import io
import uuid
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

# Lazy imports to ensure graceful degradation if dependencies are missing
try:
    import pymupdf as fitz
except ImportError:
    try:
        import fitz
    except ImportError:
        fitz = None

try:
    import docx
except ImportError:
    docx = None

try:
    import pandas as pd
except ImportError:
    pd = None

if not all([fitz, docx, pd]):
    logger.warning("Some document parser dependencies are not fully installed. Import formats will be limited.")

class DocumentParserService:
    """Service for extracting text and tabular data from various document formats."""

    SUPPORTED_MIME_TYPES = {
        'application/pdf': 'pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
        'text/plain': 'txt',
        'text/csv': 'csv',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'xlsx',
    }

    @staticmethod
    async def parse_document(file_obj, filename: str, mime_type: str) -> Dict[str, Any]:
        """
        Parses an uploaded file based on its mime type and extension.
        Returns a dictionary containing extracted text and metadata.
        """
        extension = filename.split('.')[-1].lower() if '.' in filename else ''
        
        # Fallback to extension if MIME is generic/application/octet-stream
        if mime_type not in DocumentParserService.SUPPORTED_MIME_TYPES:
            mime_mapping = {
                'pdf': 'application/pdf',
                'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'txt': 'text/plain',
                'csv': 'text/csv',
                'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            }
            if extension in mime_mapping:
                mime_type = mime_mapping[extension]
            else:
                raise ValueError(f"Unsupported file type: {filename} ({mime_type})")

        format_type = DocumentParserService.SUPPORTED_MIME_TYPES[mime_type]
        file_content = await file_obj.read()
        
        extracted_text = ""
        tabular_data = []
        is_tabular = False

        try:
            if format_type == 'pdf':
                extracted_text = DocumentParserService._parse_pdf(file_content)
            elif format_type == 'docx':
                extracted_text = DocumentParserService._parse_docx(file_content)
            elif format_type == 'txt':
                extracted_text = file_content.decode('utf-8', errors='replace')
            elif format_type == 'csv':
                tabular_data = DocumentParserService._parse_csv(file_content)
                is_tabular = True
            elif format_type == 'xlsx':
                tabular_data = DocumentParserService._parse_xlsx(file_content)
                is_tabular = True

            # Text validation for documents
            if not is_tabular and not extracted_text.strip():
                raise ValueError("No extractable text found in the document. Scanned images are not currently supported.")

        except Exception as e:
            logger.error(f"Error parsing {filename}: {str(e)}")
            raise ValueError(f"Failed to parse document: {str(e)}")

        return {
            "upload_id": str(uuid.uuid4()),
            "filename": filename,
            "format": format_type,
            "is_tabular": is_tabular,
            "extracted_text": extracted_text.strip() if not is_tabular else None,
            "tabular_data": tabular_data if is_tabular else None,
            "parsed_at": datetime.utcnow().isoformat()
        }

    @staticmethod
    def _parse_pdf(content: bytes) -> str:
        if fitz is None:
            raise ImportError("PyMuPDF is not installed. Please install it to parse PDF files.")
        text_blocks = []
        try:
            doc = fitz.open(stream=content, filetype="pdf")
            for page in doc:
                text_blocks.append(page.get_text())
            doc.close()
            return "\n\n".join(text_blocks)
        except Exception as e:
            logger.error(f"PyMuPDF failed: {e}")
            raise

    @staticmethod
    def _parse_docx(content: bytes) -> str:
        if docx is None:
            raise ImportError("python-docx is not installed. Please install it to parse DOCX files.")
        try:
            doc = docx.Document(io.BytesIO(content))
            return "\n".join([paragraph.text for paragraph in doc.paragraphs])
        except Exception as e:
            logger.error(f"python-docx failed: {e}")
            raise

    @staticmethod
    def _parse_csv(content: bytes) -> List[Dict[str, Any]]:
        if pd is None:
            raise ImportError("pandas is not installed. Please install it to parse CSV files.")
        try:
            df = pd.read_csv(io.BytesIO(content))
            return df.fillna("").to_dict('records')
        except Exception as e:
            logger.error(f"pandas CSV parsing failed: {e}")
            raise

    @staticmethod
    def _parse_xlsx(content: bytes) -> List[Dict[str, Any]]:
        if pd is None:
            raise ImportError("pandas is not installed. Please install it to parse XLSX files.")
        try:
            df = pd.read_excel(io.BytesIO(content), engine='openpyxl')
            return df.fillna("").to_dict('records')
        except Exception as e:
            logger.error(f"pandas XLSX parsing failed: {e}")
            raise

document_parser = DocumentParserService()
