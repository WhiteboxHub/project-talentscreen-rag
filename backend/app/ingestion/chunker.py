"""Semantic Chunking Service (PDF Part 4.4).

Uses section-aware chunking with overlap to preserve context between
adjacent chunks. Semantic chunking keeps related information together
so each chunk represents a meaningful piece of knowledge.
"""

from typing import List
from langchain.text_splitter import RecursiveCharacterTextSplitter
from app.core.config import settings
import re


class ResumeChunker:
    """Semantic chunker with section awareness and configurable overlap.
    
    Primary strategy: section_aware_chunk() — splits by resume/document
    section headers first, then applies recursive splitting within each section.
    
    Fallback: standard recursive splitting if section detection finds nothing.
    """

    def __init__(self, chunk_size: int = None, chunk_overlap: int = None):
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )

    def section_aware_chunk(self, text: str) -> List[str]:
        """Semantic chunking: split by section headers first, then subdivide.
        
        Resume sections: EXPERIENCE, EDUCATION, SKILLS, SUMMARY, PROJECTS, etc.
        JD sections: RESPONSIBILITIES, REQUIREMENTS, QUALIFICATIONS, etc.
        Policy/SOP sections: PROCEDURE, GUIDELINES, PROCESS, SCOPE, etc.
        """
        # All known section headers across document types
        sections = [
            # Resume sections
            "EXPERIENCE", "EDUCATION", "SKILLS", "SUMMARY", "OBJECTIVE",
            "PROJECTS", "CERTIFICATIONS", "LANGUAGES", "AWARDS",
            "WORK HISTORY", "PROFESSIONAL EXPERIENCE", "TECHNICAL SKILLS",
            "PROFESSIONAL SUMMARY", "CAREER SUMMARY", "KEY SKILLS",
            "ACCOMPLISHMENTS", "ACHIEVEMENTS", "PUBLICATIONS",
            "PROFESSIONAL DEVELOPMENT", "TRAINING",
            # Job Description sections
            "RESPONSIBILITIES", "REQUIREMENTS", "QUALIFICATIONS",
            "ROLE OVERVIEW", "ABOUT THE ROLE", "WHAT YOU'LL DO",
            "PREFERRED SKILLS", "REQUIRED SKILLS", "NICE TO HAVE",
            "BENEFITS", "COMPENSATION", "ABOUT US",
            # Policy / SOP / Interview sections
            "PROCEDURE", "GUIDELINES", "PROCESS", "SCOPE",
            "PURPOSE", "POLICY", "DEFINITIONS", "COMPLIANCE",
            "EVALUATION CRITERIA", "INTERVIEW QUESTIONS",
            "ASSESSMENT GUIDELINES", "BEST PRACTICES",
            "ESCALATION", "APPROVAL PROCESS",
        ]
        
        # Build regex pattern for section headers
        # Match headers that appear at start of line, possibly with #, **, or : formatting
        section_patterns = []
        for s in sections:
            # Match: "SKILLS", "## Skills", "**Skills**", "Skills:", etc.
            section_patterns.append(rf"(?:^|\n)(?:#+\s*|[*_]{{2,}})?{s}(?:[*_]{{2,}})?\s*[:]*\s*(?:\n|$)")
        
        pattern = "|".join(section_patterns)
        
        # Find all section positions
        matches = list(re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE))
        
        if not matches:
            # No section headers found — fall back to recursive splitting
            return self.text_splitter.split_text(text)
        
        # Split text by section boundaries
        parts = []
        for i, match in enumerate(matches):
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            section_text = text[start:end].strip()
            if section_text:
                parts.append(section_text)
        
        # Include any text before the first section header
        pre_section = text[:matches[0].start()].strip()
        if pre_section and len(pre_section) > 50:
            parts.insert(0, pre_section)
        
        # Apply recursive splitting within each section
        chunks = []
        for part in parts:
            if len(part) <= self.chunk_size:
                chunks.append(part)
            else:
                chunks.extend(self.text_splitter.split_text(part))
        
        return chunks if chunks else self.text_splitter.split_text(text)

    def chunk(self, text: str) -> List[str]:
        """Primary chunking method — uses semantic section-aware chunking.
        
        Falls back to recursive character splitting if semantic chunking
        produces no results (e.g., unstructured text without headers).
        """
        chunks = self.section_aware_chunk(text)
        
        # Filter out very small chunks (noise)
        chunks = [c for c in chunks if len(c.strip()) > 30]
        
        if not chunks:
            chunks = self.text_splitter.split_text(text)
        
        return chunks
