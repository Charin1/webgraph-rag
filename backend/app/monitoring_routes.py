from fastapi import APIRouter
from .eval_monitor import _get_conn
import sqlite3, json, os
from .monitoring import HALLUCINATION_GAUGE
router = APIRouter()

@router.get('/overview')
async def overview():
    # return some simple metrics from metrics.db and Prometheus counters (indirectly)
    data = {}
    # queries count
    try:
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute('SELECT COUNT(*) FROM queries')
        qcount = cur.fetchone()[0]
        cur.execute('SELECT COUNT(*) FROM queries WHERE timestamp > ?', (time.time() - 3600,))
        recent = cur.fetchone()[0]
        data['queries_total'] = qcount
        data['queries_last_hour'] = recent
    except Exception:
        data['queries_total'] = None
        data['queries_last_hour'] = None
    # hallucination score (last known)
    try:
        data['last_hallucination_score'] = float(HALLUCINATION_GAUGE._value.get())
    except Exception:
        data['last_hallucination_score'] = None
    return data
