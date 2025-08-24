from neo4j import GraphDatabase
from .config import settings
import logging
from typing import List

logger = logging.getLogger(__name__)
_driver = None

def _get_driver():
    """
    Initializes and returns a singleton Neo4j driver instance.
    """
    global _driver
    if _driver is None:
        try:
            _driver = GraphDatabase.driver(
                settings.NEO4J_URI, 
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
            )
            _driver.verify_connectivity()
            logger.info("Neo4j driver initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize Neo4j driver: {e}")
            _driver = None # Reset on failure
    return _driver

def add_page_node(url: str, title: str):
    """
    Creates or updates a WebPage node in the graph.
    """
    try:
        drv = _get_driver()
        if not drv: return

        with drv.session() as session:
            session.run(
                "MERGE (p:WebPage {url: $url}) SET p.title = $title", 
                url=url, 
                title=title
            )
    except Exception as e:
        logger.error(f"Failed to add page node for URL {url}: {e}")

def get_all_page_nodes() -> List[dict]:
    """
    Retrieves all WebPage nodes from the graph to display in the UI.
    """
    try:
        drv = _get_driver()
        if not drv: return []

        with drv.session() as session:
            res = session.run("MATCH (p:WebPage) RETURN p.url as url, p.title as title ORDER BY p.title")
            records = [{"url": record["url"], "title": record["title"]} for record in res]
            return records
    except Exception as e:
        logger.error(f"Failed to get all page nodes: {e}")
        return []

def check_pages_exist(urls: List[str]) -> List[str]:
    """
    Checks a list of URLs against the graph and returns the ones that already exist.
    """
    if not urls:
        return []
    
    try:
        drv = _get_driver()
        if not drv: return []

        with drv.session() as session:
            res = session.run(
                "MATCH (p:WebPage) WHERE p.url IN $urls RETURN COLLECT(p.url) AS existing_urls", 
                urls=urls
            )
            record = res.single()
            return record["existing_urls"] if record else []
    except Exception as e:
        logger.error(f"Failed to check if pages exist: {e}")
        return []

# --- THIS IS THE MISSING FUNCTION ---
def clear_graph():
    """
    Deletes all nodes and relationships from the Neo4j graph.
    """
    try:
        drv = _get_driver()
        if not drv: return
        with drv.session() as session:
            # This Cypher query finds all nodes (n) and deletes them along with
            # any relationships attached to them.
            session.run("MATCH (n) DETACH DELETE n")
        logger.info("Neo4j graph has been cleared.")
    except Exception as e:
        logger.error(f"Failed to clear Neo4j graph: {e}")
# --- END OF MISSING FUNCTION ---

def close_driver():
    """
    Closes the Neo4j driver connection. Useful for graceful shutdowns.
    """
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None
        logger.info("Neo4j driver closed.")