# backend/app/graph_routes.py

from fastapi import APIRouter
from .graph import _get_driver
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get('/get_full_graph')
async def get_full_graph_data(limit: int = 100):
    """
    Fetches nodes and relationships to visualize the entire knowledge graph.
    """
    drv = _get_driver()
    q = """
    MATCH (n)
    WITH n LIMIT $limit
    OPTIONAL MATCH (n)-[r]->(m)
    RETURN n, r, m
    """
    nodes = {}
    edges = []
    with drv.session() as session:
        res = session.run(q, limit=limit)
        for record in res:
            n, r, m = record["n"], record["r"], record["m"]
            
            if n.id not in nodes:
                nodes[n.id] = {
                    "id": n.id,
                    "label": n.get("title", n.get("name", "Node")),
                    "group": list(n.labels)[0] # e.g., "WebPage" or "Entity"
                }
            
            if m and r:
                if m.id not in nodes:
                    nodes[m.id] = {
                        "id": m.id,
                        "label": m.get("title", m.get("name", "Node")),
                        "group": list(m.labels)[0]
                    }
                edges.append({
                    "source": r.start_node.id,
                    "target": r.end_node.id,
                    "label": type(r).__name__
                })

    return {"nodes": list(nodes.values()), "edges": edges}