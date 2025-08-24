from sentence_transformers import SentenceTransformer
from .config import settings
import numpy as np
import logging
import time
import torch

logger = logging.getLogger(__name__)

_model = None

# This is the function that will be called ONCE when the app starts.
def load_model_on_startup():
    """
    Loads the SentenceTransformer model into memory.
    This is called by the FastAPI lifespan event to ensure the model is
    loaded in the main process before any workers are forked.
    """
    global _model
    if _model is None:
        logger.info("--- AI MODEL LOAD START (LIFESPAN) ---")
        logger.info(f"Loading embedding model '{settings.EMBEDDING_MODEL}'...")
        start_time = time.time()

        # Explicitly check for MPS and fallback to CPU
        # This is good practice for robustness on Mac.
        device = "mps" if torch.backends.mps.is_available() else "cpu"
        logger.info(f"Using PyTorch device: {device}")
        
        _model = SentenceTransformer(settings.EMBEDDING_MODEL, device=device)
        
        end_time = time.time()
        logger.info(f"--- AI MODEL LOAD COMPLETE --- (Took {end_time - start_time:.2f} seconds)")

def _get_model():
    """Simple getter to ensure the model is loaded."""
    if _model is None:
        # This should ideally not be called if the lifespan event works correctly,
        # but it's a good fallback.
        load_model_on_startup()
    return _model

def get_embedding_for_text(text: str) -> list:
    m = _get_model()
    emb = m.encode([text], show_progress_bar=False)[0]
    return emb.astype("float32").tolist()

def get_embeddings_for_texts(texts: list) -> list:
    m = _get_model()
    embs = m.encode(texts, show_progress_bar=False)
    return [e.astype("float32").tolist() for e in embs]