import logging
try:
    import spacy
except Exception:
    spacy = None
from .graph import _get_driver
from .config import settings

logger = logging.getLogger(__name__)

_nlp = None
def _load_spacy():
    global _nlp
    if _nlp is None:
        if spacy is None:
            raise RuntimeError('spaCy is not installed; please pip install spacy and download a model (python -m spacy download en_core_web_sm)')
        try:
            _nlp = spacy.load('en_core_web_sm')
        except Exception:
            # try to download
            import subprocess, sys
            subprocess.check_call([sys.executable, '-m', 'spacy', 'download', 'en_core_web_sm'])
            _nlp = spacy.load('en_core_web_sm')
    return _nlp

def enrich_page_entities(url: str, text: str):
    nlp = _load_spacy()
    doc = nlp(text[:20000])  # limit length for speed
    entities = set([(ent.text.strip(), ent.label_) for ent in doc.ents if ent.text.strip()])
    drv = _get_driver()
    with drv.session() as session:
        # ensure page node exists
        session.run('MERGE (p:WebPage {url:$url})', url=url)
        for ent_text, ent_label in entities:
            # merge entity node
            session.run('MERGE (e:Entity {name:$name}) SET e.label=$label', name=ent_text, label=ent_label)
            # create MENTIONS edge
            session.run('MATCH (p:WebPage {url:$url}), (e:Entity {name:$name}) MERGE (p)-[:MENTIONS]->(e)', url=url, name=ent_text)
    return {'url': url, 'entities': list(entities)}
