import json
import re
from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from app.core.config import settings

class MetadataExtractor:
    def __init__(self):
        self.llm = ChatOpenAI(model_name="gpt-3.5-turbo", api_key=settings.OPENAI_API_KEY)

    def extract_metadata(self, text: str) -> Dict[str, Any]:
        """Extract key details from resume text including skills, experience years, and education."""
        prompt = f"""
        Extract professional metadata from the following resume text. 
        Format as JSON. Include:
        - skills: list of technical skills
        - years_of_experience: total years (integer)
        - education: highest degree and institution
        - domain: primary industry/field (e.g. Fintech, Healthcare, AI)
        
        Resume Text:
        {text[:2000]}
        """
        try:
            response = self.llm.invoke(prompt)
            # Find JSON block in response
            match = re.search(r'\{.*\}', response.content, re.DOTALL)
            if match:
                return json.loads(match.group())
        except Exception as e:
            print(f"Error extracting metadata: {e}")
        
        return {"skills": [], "years_of_experience": 0, "education": "", "domain": ""}

    @staticmethod
    def normalize_skills(skills: List[str]) -> List[str]:
        return [s.lower().strip() for s in skills]
