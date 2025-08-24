import asyncio
import json
import logging
import os
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .cache import get_cached, set_cached
from .config import settings
from .eval_monitor import log_query
from .graph import check_pages_exist, clear_graph, get_all_page_nodes
from .guardrails import redact_pii
from .ingestion import ingest_urls
from .jobs import create_job, get_job_status
from .llm import ask_llm
from .llm_stream import stream_llm
from .monitoring import CACHE_HITS, CACHE_MISSES
from .retriever import hybrid_retrieve
from .vectorstore_faiss_prod import reset_store # Import the async reset function

# --- Setup ---
router = APIRouter()
logger = logging.getLogger(__name__)


# --- Pydantic Models ---
class CrawlRequest(BaseModel):
    urls: List[str]
    max_pages: Optional[int] = None
    max_depth: Optional[int] = None

class ChatRequest(BaseModel):
    query: str


# --- API Endpoints ---

@router.post('/crawl')
async def crawl_endpoint(req: CrawlRequest, background_tasks: BackgroundTasks):
    """
    Starts a crawl and ingestion job for new URLs, skipping existing ones.
    """
    existing_urls = check_pages_exist(req.urls)
    urls_to_crawl = [url for url in req.urls if url not in existing_urls]
    
    message = f"Skipped {len(existing_urls)} existing URL(s)."
    
    if not urls_to_crawl:
        return {
            "status": "skipped", 
            "job_id": None, 
            "message": f"All {len(req.urls)} requested URL(s) are already in the knowledge base."
        }

    job_id = create_job()
    
    pages_to_crawl = req.max_pages if req.max_pages is not None else settings.CRAWL_DEFAULT_MAX_PAGES
    crawl_depth = req.max_depth if req.max_depth is not None else settings.CRAWL_DEFAULT_MAX_DEPTH

    background_tasks.add_task(ingest_urls, urls_to_crawl, job_id, pages_to_crawl, crawl_depth)
    
    return {
        "status": "started", 
        "job_id": job_id, 
        "message": f"{message} Starting crawl for {len(urls_to_crawl)} new URL(s)."
    }

@router.get('/ingestion_status/{job_id}')
async def get_ingestion_status(job_id: str):
    """
    Allows the frontend to poll for the status of an ingestion job.
    """
    status = get_job_status(job_id)
    if not status:
        return {"status": "not_found", "progress": ""}
    return status

@router.get('/sources')
async def get_sources_list():
    """
    Returns a list of all ingested pages from the graph DB for the UI.
    """
    nodes = get_all_page_nodes()
    return {"sources": nodes}

@router.get('/config')
async def get_app_config():
    """
    Exposes non-sensitive configuration to the frontend.
    """
    return {
        "crawl_default_max_pages": settings.CRAWL_DEFAULT_MAX_PAGES,
        "crawl_default_max_depth": settings.CRAWL_DEFAULT_MAX_DEPTH,
    }

@router.post('/reset_knowledge_base')
async def reset_knowledge_base():
    """
    Deletes all data from Neo4j and the FAISS vector store, and resets the store connection.
    """
    logger.warning("--- KNOWLEDGE BASE RESET INITIATED ---")
    
    clear_graph()
    
    faiss_index_path = settings.FAISS_INDEX_PATH
    
    try:
        if os.path.exists(faiss_index_path):
            os.remove(faiss_index_path)
            logger.info(f"Deleted FAISS index file: {faiss_index_path}")
        
        # This is now an async function and must be awaited.
        # It handles flushing Redis and resetting the in-memory store instance.
        await reset_store()

    except Exception as e:
        logger.error(f"Error during knowledge base reset: {e}")
        return {"status": "error", "message": "Failed to reset knowledge base."}

    return {"status": "success", "message": "Knowledge base has been cleared."}

@router.post('/chat')
async def chat_endpoint(req: ChatRequest):
    """
    Handles a non-streaming chat request with caching.
    """
    cached = await get_cached(req.query)
    if cached:
        CACHE_HITS.inc()
        return {"from_cache": True, "answer": cached}

    CACHE_MISSES.inc()
    # hybrid_retrieve is now an async function and must be awaited.
    candidates = await hybrid_retrieve(req.query, top_k=5)

    if not candidates:
        no_context_answer = "I'm sorry, but I couldn't find any relevant information in my knowledge base to answer that question. Please try rephrasing your query or adding more sources."
        return {"from_cache": False, "answer": no_context_answer, "sources": []}

    context = "\n\n".join([c.get('meta', {}).get('text', '')[:800] for c in candidates])
    prompt = f"Use the following context to answer the question:\n{context}\n\nQuestion: {req.query}"
    answer = ask_llm(prompt)
    
    await set_cached(req.query, answer, expire=3600)
    
    asyncio.create_task(_log_query_async(req.query, candidates, answer))
    
    return {"from_cache": False, "answer": answer, "sources": candidates}

@router.post('/chat_stream')
async def chat_stream(request: Request):
    """
    Handles a streaming chat request.
    """
    body = await request.json()
    query = body.get('query')
    
    # hybrid_retrieve is now an async function and must be awaited.
    candidates = await hybrid_retrieve(query, top_k=5)

    if not candidates:
        async def no_context_stream():
            yield "I'm sorry, but I couldn't find any relevant information in my knowledge base to answer that question."
            footer = {'sources': [], 'hallucination_score': 0.0}
            yield '\n' + json.dumps(footer)
        return StreamingResponse(no_context_stream(), media_type='text/plain')

    context = "\n\n".join([c.get('meta', {}).get('text', '')[:800] for c in candidates])
    prompt = f"Use the following context to answer the question:\n{context}\n\nQuestion: {query}"
    
    async def event_stream():
        full_response_text = ""
        for chunk in stream_llm(prompt):
            safe_chunk = redact_pii(chunk)
            full_response_text += safe_chunk
            yield safe_chunk
        
        try:
            from .eval_monitor import hallucination_score
            source_texts = [c.get('meta', {}).get('text', '') for c in candidates]
            score = hallucination_score(full_response_text, source_texts)
        except Exception as e:
            logger.error(f"Failed to calculate hallucination score: {e}")
            score = 0.0
            
        footer = {'sources': candidates, 'hallucination_score': score}
        yield '\n' + json.dumps(footer)

    return StreamingResponse(event_stream(), media_type='text/plain')


# --- Helper Functions ---
async def _log_query_async(query, candidates, answer):
    """Helper to log queries without blocking the main request."""
    try:
        log_query(query, candidates, answer)
    except Exception as e:
        logger.exception('Failed to log query: %s', e)