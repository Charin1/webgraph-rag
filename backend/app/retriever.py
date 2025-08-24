import logging
import asyncio

from .embeddings import get_embedding_for_text
from .reranker import rerank
from .vectorstore_faiss_prod import get_store

logger = logging.getLogger(__name__)

async def hybrid_retrieve(query: str, top_k: int = 5):
    """
    Performs an async vector search and then runs the synchronous, CPU-bound
    reranker in a separate thread to avoid deadlocks.
    """
    store = get_store()
    
    # 1. Initial dense vector search (async and non-blocking)
    q_emb = get_embedding_for_text(query)
    
    if not q_emb:
        logger.error("Failed to generate query embedding. Aborting retrieval.")
        return []

    # Fetch slightly more candidates for the reranker to work with
    vec_results = await store.search(q_emb, top_k=top_k * 3)
    
    # 2. Convert to a standard candidate format
    candidates = []
    for r in vec_results:
        candidates.append({'type': 'vector', 'score': r.get('score', 0.0), 'meta': r})

    if not candidates:
        return []

    # --- THIS IS THE FINAL FIX ---
    # The bypass has been removed. We are now re-enabling the call
    # to the reranker, which is the final step in the RAG pipeline.
    reranked = await asyncio.to_thread(rerank, query=query, candidates=candidates, top_k=top_k)
    # --- END OF FIX ---
    
    return reranked