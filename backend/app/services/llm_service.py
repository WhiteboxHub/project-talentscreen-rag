from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from app.core.config import settings
from typing import List, Dict, Any

class LLMService:
    def __init__(self):
        self.llm = ChatOpenAI(
            model_name="gpt-4-turbo", 
            api_key=settings.OPENAI_API_KEY
        )

    def expand_query(self, query: str) -> str:
        """
        Human-like Query Expansion:
        Transforms a simple recruiter query into a semantically rich technical query.
        Example: 'Python dev' -> 'Senior Software Engineer, Python, Django, Flask, Backend Development'
        """
        prompt = f"""
        As a Senior Technical Recruiter, expand the following candidate search query for better AI retrieval.
        Identify synonyms, related technologies, and seniority levels.
        
        Original Query: {query}
        
        Return only the expanded comma-separated keywords.
        """
        try:
            response = self.llm.invoke(prompt)
            return response.content
        except Exception:
            return query

    def stream_response(self, query: str, context_documents: List[Dict[str, Any]]):
        context_text = "\n\n".join([f"Candidate Resume {i+1}:\n{doc['text']}" for i, doc in enumerate(context_documents)])
        
        system_prompt = """
        You are an expert AI Recruitment Assistant. Your goal is to help recruiters find the best candidates.
        Use the provided resume snippets to answer the recruiter's query.
        Be professional, concise, and provide evidence from the resumes for your claims.
        """
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt + "\n\nCONTEXT:\n{context}"),
            ("human", "{query}")
        ])
        
        chain = prompt | self.llm
        return chain.stream({
            "context": context_text,
            "query": query
        })

    def analyze_candidate(self, resume_text: str, role_description: str) -> str:
        prompt = f"""
        Analyze the candidate's suitability for the following role:
        Role: {role_description}
        
        Resume:
        {resume_text}
        
        Provide a detailed analysis including match score (0-100), key strengths, and potential gaps.
        """
        response = self.llm.invoke(prompt)
        return response.content
