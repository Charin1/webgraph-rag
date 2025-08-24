import faiss
import numpy as np
import os
import json
import asyncio
from typing import List, Dict, Optional

from .config import settings
from .cache import get_redis

_lock = asyncio.Lock()
_store_instance = None

class FaissVectorStore:
    def __init__(self):
        self.index_path = settings.FAISS_INDEX_PATH
        self._index = None
        self._dim = None
        if os.path.exists(self.index_path):
            try:
                self._index = faiss.read_index(self.index_path)
                self._dim = self._index.d
            except Exception:
                self._index = None

    def _init_index(self, dim: int):
        idx = faiss.IndexFlatIP(dim)
        self._index = faiss.IndexIDMap(idx)
        self._dim = dim

    # --- THIS IS THE FIX: Make persist() a simple, synchronous function ---
    def persist(self):
        """
        Synchronously writes the FAISS index to disk. This is simpler and
        avoids asyncio/thread deadlocks with the FAISS C++ library.
        """
        if self._index is not None:
            # This is a direct, blocking call. It's fast enough.
            faiss.write_index(self._index, self.index_path)
    # --- END OF FIX ---

    def _normalize(self, vectors: np.ndarray) -> np.ndarray:
        faiss.normalize_L2(vectors)
        return vectors

    async def upsert_chunks(self, chunks: List[Dict]):
        if not chunks: return
        
        redis_client = await get_redis()
        if not redis_client:
            raise ConnectionError("Redis is not available for vector store metadata.")

        async with _lock:
            d = len(chunks[0]["embedding"])
            if self._index is None: self._init_index(d)

            to_add_vectors = []
            to_add_ids = []
            
            async with redis_client.pipeline() as pipe:
                for i, c in enumerate(chunks):
                    new_id = self._index.ntotal + i
                    metadata_key = f"meta:{new_id}"
                    metadata_value = json.dumps({
                        "uuid": c["uuid"],
                        "page_url": c.get("page_url"),
                        "title": c.get("title"),
                        "text": c.get("text")
                    })
                    await pipe.set(metadata_key, metadata_value)
                    
                    vec = np.array(c["embedding"], dtype="float32")
                    to_add_vectors.append(vec)
                    to_add_ids.append(new_id)
                
                await pipe.execute()

            if to_add_vectors:
                vecs = np.vstack(to_add_vectors).astype("float32")
                self._normalize(vecs)
                ids_arr = np.array(to_add_ids, dtype="int64")
                self._index.add_with_ids(vecs, ids_arr)
                
                # --- THIS IS THE FIX: Call the synchronous persist() ---
                self.persist()
                # --- END OF FIX ---

    async def search(self, query_embedding: List[float], top_k: int = 10) -> List[Dict]:
        if self._index is None: return []

        redis_client = await get_redis()
        if not redis_client:
            raise ConnectionError("Redis is not available for vector search metadata.")

        q = np.array([query_embedding], dtype="float32")
        self._normalize(q)
        D, I = self._index.search(q, top_k)
        ids = I[0].tolist()
        scores = D[0].tolist()

        results = []
        
        meta_keys = [f"meta:{int(idx)}" for idx in ids if idx != -1]
        if not meta_keys: return []

        metadata_values = await redis_client.mget(meta_keys)

        for i, meta_val in enumerate(metadata_values):
            if not meta_val: continue
            
            meta = json.loads(meta_val)
            results.append({
                "id": ids[i],
                "uuid": meta["uuid"],
                "page_url": meta["page_url"],
                "title": meta["title"],
                "text": meta["text"],
                "score": float(scores[i]),
            })
        return results

def get_store() -> FaissVectorStore:
    global _store_instance
    if _store_instance is None:
        _store_instance = FaissVectorStore()
    return _store_instance

async def reset_store():
    global _store_instance
    async with _lock:
        # We don't need to close the store instance anymore, just reset it
        _store_instance = None
        redis_client = await get_redis()
        if redis_client:
            await redis_client.flushdb()