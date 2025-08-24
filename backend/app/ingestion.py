import uuid
import logging
from typing import List, Dict

from bs4 import BeautifulSoup
from readability import Document

from .crawler_robust import crawl
from .embeddings import get_embeddings_for_texts, get_embedding_for_text
from .graph import add_page_node
from .jobs import update_job_status, update_job_sub_step
from .monitoring import CRAWL_PAGES, INGESTED_PAGES
from .vectorstore_faiss_prod import get_store # Use the singleton getter

# --- Setup ---
logger = logging.getLogger(__name__)

# --- Constants ---
CHUNK_SIZE = 800
CHUNK_OVERLAP = 100
EMBEDDING_BATCH_SIZE = 32

# --- Helper Functions ---
def extract_main_text(html: str) -> dict:
    """Strips HTML down to the main article text."""
    doc = Document(html)
    title = doc.title()
    summary = doc.summary()
    txt = BeautifulSoup(summary, "html.parser").get_text(separator="\n", strip=True)
    return {"title": title, "text": txt}

def chunk_text(text: str, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP) -> List[str]:
    """Splits a long text into smaller, overlapping chunks."""
    tokens = text.split()
    if not tokens:
        return []
    chunks = []
    i = 0
    while i < len(tokens):
        chunk = tokens[i:i + chunk_size]
        chunks.append(" ".join(chunk))
        i += chunk_size - overlap
    return chunks


# --- Main Ingestion Logic ---
async def ingest_urls(urls: List[str], job_id: str, max_pages: int = 20, max_depth: int = 2):
    """
    Crawls and ingests URLs, updating the job status with granular sub-steps and detailed logging.
    """
    try:
        update_job_status(job_id, "running", f"Starting crawl (max pages: {max_pages}, max depth: {max_depth})...")
        raw_pages = await crawl(urls, max_pages=max_pages, max_depth=max_depth)
        
        if not raw_pages:
            update_job_status(job_id, "failed", "No pages found or all pages failed to crawl.")
            return

        summary = {"pages": 0, "chunks": 0}
        total_pages = len(raw_pages)
        
        sub_step_template = [
            {"name": "Extracting & Chunking", "status": "pending", "detail": ""},
            {"name": "Generating Embeddings", "status": "pending", "detail": ""},
            {"name": "Upserting to Vector Store", "status": "pending", "detail": ""},
        ]

        for i, page in enumerate(raw_pages):
            main_progress_text = f"Processing page {i+1}/{total_pages}: {page['url']}"
            update_job_status(job_id, "running", main_progress_text, sub_steps=sub_step_template)
            
            url = page["url"]
            html = page["html"]
            CRAWL_PAGES.inc()
            
            # --- Step 1: Extract & Chunk ---
            update_job_sub_step(job_id, "Extracting & Chunking", "running")
            meta = extract_main_text(html)
            title = meta.get("title") or url
            text = meta.get("text") or ""
            
            if not text.strip():
                for step in sub_step_template:
                    update_job_sub_step(job_id, step["name"], "completed", "Skipped (empty page)")
                continue

            chunks = chunk_text(text)
            
            logger.info(f"Job {job_id}: Page '{title}' | Extracted text length: {len(text)} chars | Created {len(chunks)} chunks.")

            update_job_sub_step(job_id, "Extracting & Chunking", "completed", f"{len(chunks)} chunks found")

            # --- Step 2: Generate Embeddings (with smart logic) ---
            update_job_sub_step(job_id, "Generating Embeddings", "running", "Preparing...")
            
            all_chunk_texts = chunks
            all_embeddings = []
            total_chunks = len(all_chunk_texts)

            if total_chunks == 1:
                progress_detail = "(1/1 chunks)"
                update_job_sub_step(job_id, "Generating Embeddings", "running", progress_detail)
                logger.info(f"Job {job_id}: Using fast path for single chunk on page {url}")
                embedding = get_embedding_for_text(all_chunk_texts[0])
                all_embeddings.append(embedding)
            elif total_chunks > 1:
                for j in range(0, total_chunks, EMBEDDING_BATCH_SIZE):
                    batch_texts = all_chunk_texts[j:j + EMBEDDING_BATCH_SIZE]
                    batch_embeddings = get_embeddings_for_texts(batch_texts)
                    all_embeddings.extend(batch_embeddings)
                    
                    progress_detail = f"({min(j + EMBEDDING_BATCH_SIZE, total_chunks)}/{total_chunks} chunks)"
                    update_job_sub_step(job_id, "Generating Embeddings", "running", progress_detail)
                    logger.info(f"Job {job_id}: Embedding progress {progress_detail} for page {url}")

            update_job_sub_step(job_id, "Generating Embeddings", "completed", f"{total_chunks} embeddings generated")

            # --- Step 3: Upsert to Vector Store ---
            update_job_sub_step(job_id, "Upserting to Vector Store", "running")
            to_upsert = []
            for k, chunk in enumerate(all_chunk_texts):
                to_upsert.append({
                    "uuid": str(uuid.uuid4()), 
                    "page_url": url, 
                    "title": title,
                    "text": chunk,
                    "embedding": all_embeddings[k]
                })

            if to_upsert:
                # This is now an async function and must be awaited.
                await get_store().upsert_chunks(to_upsert)
                add_page_node(url, title)
                INGESTED_PAGES.inc(len(to_upsert))
                summary["pages"] += 1
                summary["chunks"] += len(to_upsert)
            update_job_sub_step(job_id, "Upserting to Vector Store", "completed")

        final_progress = f"Completed. Ingested {summary['pages']} pages and {summary['chunks']} chunks."
        update_job_status(job_id, "completed", final_progress, sub_steps=[])
        logger.info(f"Job {job_id} completed: {final_progress}")

    except Exception as e:
        logger.exception(f"Job {job_id} failed: {e}")
        update_job_status(job_id, "failed", f"An error occurred: {str(e)}")