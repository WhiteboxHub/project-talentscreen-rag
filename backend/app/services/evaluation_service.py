from typing import List, Dict, Any
from langchain_openai import ChatOpenAI
from app.core.config import settings

class EvaluationService:
    def __init__(self):
        self.llm = ChatOpenAI(model_name="gpt-4", api_key=settings.OPENAI_API_KEY)

    def evaluate_faithfulness(self, query: str, context: str, response: str) -> Dict[str, Any]:
        """Check if the answer is grounded in the context."""
        prompt = f"""
        Evaluation Task: Faithfulness
        
        System Context: {context}
        Query: {query}
        Generated Answer: {response}
        
        Does the Answer contain information NOT found in the Context (Hallucinations)? 
        Return a JSON with "faithfulness_score" (0-1) and "reasoning".
        """
        eval_resp = self.llm.invoke(prompt)
        return eval_resp.content

    def evaluate_relevance(self, query: str, context: str) -> Dict[str, Any]:
        """Check if the retrieved context is relevant to the query."""
        prompt = f"""
        Evaluation Task: Context Relevance
        
        Query: {query}
        Retrieved Context: {context}
        
        Is the retrieved context useful to answer the query?
        Return a JSON with "relevance_score" (0-1) and "reasoning".
        """
        eval_resp = self.llm.invoke(prompt)
        return eval_resp.content
