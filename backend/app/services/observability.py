import os
from app.core.logging import logger

try:
    from langfuse import Langfuse
    LANGFUSE_AVAILABLE = True
except ImportError:
    LANGFUSE_AVAILABLE = False
    logger.warning("langfuse library not installed. Observability tracing disabled.")


class ObservabilityService:
    """Langfuse-based observability for the complete RAG pipeline.
    
    Traces recruiter queries, retrieval results, reranking, prompt execution,
    LLM responses, and token usage (PDF Part 13.1).
    """

    def __init__(self):
        self.langfuse = None
        pub_key = os.getenv("LANGFUSE_PUBLIC_KEY", "")
        sec_key = os.getenv("LANGFUSE_SECRET_KEY", "")
        if LANGFUSE_AVAILABLE and pub_key and sec_key:
            try:
                self.langfuse = Langfuse(
                    public_key=pub_key,
                    secret_key=sec_key,
                    host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
                )
                logger.info("Langfuse observability initialized successfully.")
            except Exception as e:
                logger.warning(f"Langfuse initialization failed: {e}. Tracing disabled.")
        else:
            logger.info("Langfuse not configured (missing keys). Tracing disabled.")

    def trace_retrieval(self, query: str, results: list, retrieval_type: str = "hybrid"):
        """Trace a retrieval operation — BM25, vector, or hybrid."""
        if not self.langfuse:
            return
        try:
            trace = self.langfuse.trace(name="candidate_retrieval")
            trace.span(
                name=f"{retrieval_type}_search",
                input={"query": query},
                output={"results_count": len(results)}
            )
        except Exception as e:
            logger.warning(f"Langfuse trace_retrieval failed: {e}")

    def trace_reranking(self, query: str, before_count: int, after_count: int):
        """Trace a reranking operation."""
        if not self.langfuse:
            return
        try:
            trace = self.langfuse.trace(name="reranking")
            trace.span(
                name="bge_cross_encoder",
                input={"query": query, "candidates_before": before_count},
                output={"candidates_after": after_count}
            )
        except Exception as e:
            logger.warning(f"Langfuse trace_reranking failed: {e}")

    def trace_generation(self, query: str, response: str, model: str, tokens_used: int = 0):
        """Trace an LLM generation call."""
        if not self.langfuse:
            return
        try:
            self.langfuse.generation(
                name="recruiter_chat",
                input=query,
                output=response,
                model=model,
                usage={"total_tokens": tokens_used} if tokens_used else None
            )
        except Exception as e:
            logger.warning(f"Langfuse trace_generation failed: {e}")

    def trace_query_processing(self, original_query: str, optimized_query: str, expanded_query: str):
        """Trace query understanding, optimization, and expansion."""
        if not self.langfuse:
            return
        try:
            trace = self.langfuse.trace(name="query_processing")
            trace.span(
                name="query_pipeline",
                input={"original_query": original_query},
                output={
                    "optimized_query": optimized_query,
                    "expanded_query": expanded_query
                }
            )
        except Exception as e:
            logger.warning(f"Langfuse trace_query_processing failed: {e}")


observability = ObservabilityService()
