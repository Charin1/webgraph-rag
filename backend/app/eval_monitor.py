import sqlite3
import time
import logging
from typing import List, Dict, Optional
from .config import settings

logger = logging.getLogger(__name__)
DB = 'metrics.db'

def _get_conn():
    conn = sqlite3.connect(DB, check_same_thread=False)
    cur = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS queries
                   (id INTEGER PRIMARY KEY AUTOINCREMENT, query TEXT, timestamp REAL, candidates TEXT, answer TEXT)''')
    conn.commit()
    return conn

def log_query(query: str, candidates: List[Dict], answer: str):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute('INSERT INTO queries (query, timestamp, candidates, answer) VALUES (?,?,?,?)',
                (query, time.time(), str(candidates), answer))
    conn.commit()
    conn.close()

def compute_precision_at_k(predicted_ids: List[str], ground_truth_ids: List[str], k: int = 5) -> float:
    if not ground_truth_ids:
        return 0.0
    pred_k = predicted_ids[:k]
    hits = sum(1 for p in pred_k if p in ground_truth_ids)
    return hits / min(k, len(ground_truth_ids))

def compute_mrr(predicted_ids: List[str], ground_truth_ids: List[str]) -> float:
    for i, p in enumerate(predicted_ids):
        if p in ground_truth_ids:
            return 1.0 / (i+1)
    return 0.0

# hallucination detector using spaCy NER: flag entities in answer not present in sources
def hallucination_score(answer: str, source_texts: List[str]) -> float:
    try:
        import spacy
        nlp = spacy.load('en_core_web_sm')
    except Exception as e:
        logger.warning('spaCy not available for hallucination detection: %s', e)
        return 0.0
    ans_doc = nlp(answer)
    ans_ents = set([ent.text.strip().lower() for ent in ans_doc.ents])
    src_ents = set()
    for t in source_texts:
        doc = nlp(t[:10000])
        for ent in doc.ents:
            src_ents.add(ent.text.strip().lower())
    if not ans_ents:
        return 0.0
    # proportion of answer entities that are NOT in sources
    missing = [e for e in ans_ents if e not in src_ents]
    return len(missing) / len(ans_ents)
