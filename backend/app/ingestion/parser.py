import PyPDF2
from docx import Document
import pytesseract
from PIL import Image
import io
import os

class ResumeParser:
    @staticmethod
    def extract_text_from_pdf(file_path: str) -> str:
        text = ""
        try:
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                for page_num in range(len(reader.pages)):
                    page = reader.pages[page_num]
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            
            # If text is too short, try OCR
            if len(text.strip()) < 50:
                text = ResumeParser.ocr_pdf(file_path)
        except Exception as e:
            print(f"Error parsing PDF {file_path}: {e}")
        return text

    @staticmethod
    def extract_text_from_docx(file_path: str) -> str:
        try:
            doc = Document(file_path)
            return "\n".join([para.text for para in doc.paragraphs])
        except Exception as e:
            print(f"Error parsing DOCX {file_path}: {e}")
            return ""

    @staticmethod
    def ocr_pdf(file_path: str) -> str:
        # Placeholder for OCR logic (e.g., using pdf2image and pytesseract)
        # requires system dependencies like poppler and tesseract
        return "OCR Text (Simulated)"

    @classmethod
    def parse(cls, file_path: str) -> str:
        ext = os.path.splitext(file_path)[1].lower()
        if ext == '.pdf':
            return cls.extract_text_from_pdf(file_path)
        elif ext in ['.docx', '.doc']:
            return cls.extract_text_from_docx(file_path)
        else:
            return ""
