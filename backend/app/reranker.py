import logging
from sentence_transformers import CrossEncoder

logger = logging.getLogger(__name__)
_model = None
_model_name = 'cross-encoder/ms-marco-MiniLM-L-6-v2'

def load_reranker_model_on_startup():
    """
    Loads the CrossEncoder model into memory.
    This is called by the FastAPI lifespan event to ensure the model is
    loaded in the main process before any workers are forked.
    """
    global _model
    if _model is None:
        logger.info(f"--- RERANKER MODEL LOAD START (LIFESPAN) ---")
        logger.info(f"Loading reranker model '{_model_name}'...")
        _model = CrossEncoder(_model_name)
        logger.info(f"--- RERANKER MODEL LOAD COMPLETE ---")

# --- THIS IS THE MISSING FUNCTION ---
def warmup_reranker():
    """
    Runs a dummy prediction to initialize all PyTorch components in the main process.
    This prevents deadlocks in forked Uvicorn workers on macOS.
    """

    if _model is not None:
        logger.info("--- RERANKER WARM-UP START ---")
        try:
            # A tiny, fast, fake prediction to force PyTorch to initialize.
            _model.predict([("dummy query", "dummy text")], show_progress_bar=False)
            logger.info("--- RERANKER WARM-UP COMPLETE ---")
        except Exception as e:
            logger.error(f"Reranker warm-up failed: {e}")
# --- END OF MISSING FUNCTION ---

def _get_model():
    """Simple getter to ensure the model is loaded."""
    if _model is None:
        # This should not happen if the lifespan event works, but it's a safe fallback.
        load_reranker_model_on_startup()
        warmup_reranker() # Also warm up if loaded lazily
    return _model

def rerank(query: str, candidates: list, top_k: int = 5):
    """Rerank candidate dicts using a cross-encoder."""
    if not candidates:
        return []
    
    model = _get_model()
    
    pairs = []
    for c in candidates:
        text = c.get('meta', {}).get('text', '')
        pairs.append((query, text))
        
    # Ensure progress bar is disabled here as well for safety
    scores = model.predict(pairs, show_progress_bar=False)
    
    for c, s in zip(candidates, scores):
        c['rerank_score'] = float(s)
        
    sorted_c = sorted(candidates, key=lambda x: x['rerank_score'], reverse=True)
    return sorted_c[:top_k]