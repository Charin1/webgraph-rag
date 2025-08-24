import faulthandler
faulthandler.enable()


import os
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

# then the rest of your imports and app code

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from .api_routes import router
from .config import settings
from .embeddings import load_model_on_startup
from .reranker import load_reranker_model_on_startup, warmup_reranker
from .logging import logger
from .monitoring import IN_PROGRESS_REQUESTS, REQUEST_COUNT

# --- Lifespan Manager ---
# This is the modern FastAPI way to handle startup and shutdown events.
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles application startup and shutdown events.
    """
    logger.info("--- Application Startup ---")
    
    # Pre-loading the AI models here is the key to preventing multi-processing deadlocks on macOS.
    # The models are loaded into the main process before Uvicorn creates any worker processes.
    load_model_on_startup()
    load_reranker_model_on_startup()
    warmup_reranker() # This prevents a deadlock on the first reranker request
    
    # The 'yield' keyword passes control back to FastAPI to start serving requests.
    yield
    
    # This code runs ONCE when the application is shutting down.
    logger.info("--- Application Shutdown ---")


# --- FastAPI App Initialization ---
# The lifespan manager is passed to the FastAPI constructor.
app = FastAPI(title="WebGraph RAG", lifespan=lifespan)


# --- CORS (Cross-Origin Resource Sharing) Middleware ---
# This is the critical fix to allow the frontend (running on a different port)
# to make direct API calls to the backend, bypassing the Vite proxy.
origins = [
    "http://localhost:3000", # The default port for the production frontend build
    "http://localhost:5173", # The port for the Vite development server
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], # Allow all methods (GET, POST, etc.)
    allow_headers=["*"], # Allow all headers
)


# --- Routers ---
# Include the main API router
app.include_router(router, prefix="/api")


# --- Prometheus Metrics ---
# Mount the Prometheus ASGI app at the /metrics endpoint.
try:
    from prometheus_client import make_asgi_app
    prometheus_app = make_asgi_app()
    app.mount('/metrics', prometheus_app)
    logger.info("Prometheus metrics endpoint mounted at /metrics")
except ImportError:
    logger.warning("Prometheus client not installed. Metrics will not be available.")
    prometheus_app = None


# --- Monitoring Middleware ---
@app.middleware('http')
async def add_prometheus_middleware(request: Request, call_next):
    """
    A lightweight middleware to increment Prometheus request counters.
    """
    IN_PROGRESS_REQUESTS.inc()
    try:
        response = await call_next(request)
        # Record status and method labels for completed requests
        REQUEST_COUNT.labels(
            method=request.method, 
            endpoint=request.url.path, 
            http_status=str(response.status_code)
        ).inc()
    finally:
        IN_PROGRESS_REQUESTS.dec()
    return response


# --- Root Endpoint ---
@app.get('/')
async def root():
    """
    A simple health check endpoint.
    """
    return {"status": "ok", "message": "Welcome to WebGraph RAG API"}


# --- Main Entry Point for Local Development ---
if __name__ == '__main__':
    # This block allows you to run the app directly with `python -m app.main`
    uvicorn.run(
        'app.main:app', 
        host=settings.HOST, 
        port=settings.PORT, 
        reload=True
    )