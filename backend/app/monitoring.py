from prometheus_client import Counter, Gauge, Histogram
import time

# Counters
REQUEST_COUNT = Counter('app_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'http_status'])
QUERY_COUNT = Counter('app_queries_total', 'Total user queries processed')
CACHE_HITS = Counter('app_cache_hits_total', 'Cache hits')
CACHE_MISSES = Counter('app_cache_misses_total', 'Cache misses')
CRAWL_PAGES = Counter('app_crawl_pages_total', 'Total pages crawled')
INGESTED_PAGES = Counter('app_ingested_pages_total', 'Total pages ingested')

# Gauges
IN_PROGRESS_REQUESTS = Gauge('app_inprogress_requests', 'Number of in-progress requests')
HALLUCINATION_GAUGE = Gauge('app_hallucination_score', 'Last computed hallucination score')

# Histograms
REQUEST_LATENCY = Histogram('app_request_latency_seconds', 'Request latency', ['endpoint'])

# Helper decorator for timing
def observe_latency(endpoint):
    def decorator(func):
        def wrapper(*args, **kwargs):
            start = time.time()
            try:
                return func(*args, **kwargs)
            finally:
                elapsed = time.time() - start
                REQUEST_LATENCY.labels(endpoint=endpoint).observe(elapsed)
        return wrapper
    return decorator
