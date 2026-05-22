from typing import List
from langchain.text_splitter import RecursiveCharacterTextSplitter
import re

class ResumeChunker:
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )

    def section_aware_chunk(self, text: str) -> List[str]:
        # Define common resume sections
        sections = [
            "EXPERIENCE", "EDUCATION", "SKILLS", "SUMMARY", 
            "PROJECTS", "CERTIFICATIONS", "LANGUAGES", "AWARDS",
            "WORK HISTORY", "PROFESSIONAL EXPERIENCE", "TECHNICAL SKILLS"
        ]
        
        # Simple split by common section headers (all caps or followed by newline)
        # This is a basic implementation; LLM-based section detection is better for production
        pattern = "|".join([rf"(?i)\n{s}\n" for s in sections])
        parts = re.split(pattern, text)
        
        chunks = []
        for part in parts:
            if part.strip():
                chunks.extend(self.text_splitter.split_text(part))
        return chunks

    def chunk(self, text: str) -> List[str]:
        return self.text_splitter.split_text(text)
