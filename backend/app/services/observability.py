from langfuse import Langfuse
from app.core.config import settings
import os

class ObservabilityService:
    def __init__(self):
        self.langfuse = None
        if os.getenv("LANGFUSE_PUBLIC_KEY"):
            self.langfuse = Langfuse(
                public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
                secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
                host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
            )

    def trace_retrieval(self, query: str, results: list):
        if self.langfuse:
            trace = self.langfuse.trace(name="candidate_retrieval")
            trace.span(
                name="vector_search",
                input={"query": query},
                output={"results_count": len(results)}
            )

    def trace_generation(self, query: str, response: str, model: str):
        if self.langfuse:
            self.langfuse.generation(
                name="recruiter_chat",
                input=query,
                output=response,
                model=model
            )

observability = ObservabilityService()
