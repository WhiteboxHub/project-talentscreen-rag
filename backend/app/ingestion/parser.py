"""Document Parser (PDF Part 4.3).

Parses documents using IBM Docling (primary) with fallback to PyPDF2/python-docx.
Supports: PDF, DOCX, TXT, MD formats.
Handles resumes, job descriptions, interview guidelines, hiring policies,
recruitment SOPs, and internal knowledge documents.
"""

import os
from app.core.logging import logger

try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False

try:
    from docx import Document
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

try:
    from docling.document_converter import DocumentConverter
    DOCLING_AVAILABLE = True
    logger.info("IBM Docling parser loaded successfully.")
except ImportError:
    DOCLING_AVAILABLE = False
    logger.warning("IBM Docling not installed. Falling back to standard parsers.")


class ResumeParser:
    """Multi-format document parser with Docling primary, PyPDF2/docx fallback.
    
    Docling standardizes different document structures (resumes, JDs,
    policies, interview guides) into a consistent format.
    """

    @staticmethod
    def extract_text_from_pdf(file_path: str) -> str:
        """Extract text from PDF using PyPDF2."""
        if not PYPDF2_AVAILABLE:
            logger.error("PyPDF2 not installed. Cannot parse PDF.")
            return ""
        text = ""
        try:
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                for page_num in range(len(reader.pages)):
                    page = reader.pages[page_num]
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            
            # If text is too short, the PDF may be image-based
            if len(text.strip()) < 50:
                logger.warning(f"PDF text extraction yielded very little text for {file_path}. May need OCR.")
        except Exception as e:
            logger.error(f"Error parsing PDF {file_path}: {e}")
        return text

    @staticmethod
    def extract_text_from_docx(file_path: str) -> str:
        """Extract text from DOCX using python-docx."""
        if not DOCX_AVAILABLE:
            logger.error("python-docx not installed. Cannot parse DOCX.")
            return ""
        try:
            doc = Document(file_path)
            paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
            return "\n".join(paragraphs)
        except Exception as e:
            logger.error(f"Error parsing DOCX {file_path}: {e}")
            return ""

    @staticmethod
    def extract_text_from_txt(file_path: str) -> str:
        """Extract text from plain text or markdown files."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading text file {file_path}: {e}")
            return ""

    @classmethod
    def parse(cls, file_path: str) -> str:
        """Parse a document using the best available parser.
        
        Priority: Docling → Format-specific parser.
        
        Docling converts different document formats into a structured
        representation that can be processed consistently regardless of
        whether the source document is a resume, job description,
        policy document, or interview guide (PDF Part 4.3).
        """
        # Try Docling first if available (handles PDF, DOCX, and more)
        if DOCLING_AVAILABLE:
            try:
                logger.info(f"Using IBM Docling to parse {file_path}")
                converter = DocumentConverter()
                result = converter.convert(file_path)
                text = result.document.export_to_markdown()
                if text and len(text.strip()) > 50:
                    return text
                logger.warning("Docling extracted very short text, falling back to standard parsers.")
            except Exception as e:
                logger.warning(f"Docling failed: {e}. Falling back to standard parsers.")

        # Determine format and use appropriate parser
        ext = os.path.splitext(file_path)[1].lower()
        if ext == '.pdf':
            return cls.extract_text_from_pdf(file_path)
        elif ext in ['.docx', '.doc']:
            return cls.extract_text_from_docx(file_path)
        elif ext in ['.txt', '.md', '.text']:
            return cls.extract_text_from_txt(file_path)
        else:
            logger.warning(f"Unsupported file format: {ext}. Attempting text read.")
            return cls.extract_text_from_txt(file_path)
