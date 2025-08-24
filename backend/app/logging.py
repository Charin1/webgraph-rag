import logging
import sys

def setup_logging():
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    fmt = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
    handler.setFormatter(logging.Formatter(fmt))
    root.handlers = [handler]

setup_logging()
logger = logging.getLogger(__name__)
