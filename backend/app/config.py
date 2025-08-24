from pydantic_settings import BaseSettings
from typing import Optional
import os

os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

# Define a base directory for the application's data files.
# This ensures all parts of the app look in the same place.
DATA_DIR = os.getenv("DATA_DIR", os.getcwd())

class Settings(BaseSettings):
    GRAPH_ENABLED: bool = True 

    CRAWL_DEFAULT_MAX_PAGES: int = 20
    CRAWL_DEFAULT_MAX_DEPTH: int = 2

    # --- THIS SECTION IS CRITICAL ---
    # You MUST declare the variables here.
    # The values are the defaults if they are not in the .env file.
    FAISS_INDEX_PATH: str = os.path.join(DATA_DIR, "faiss.index")
    FAISS_META_DB_PATH: str = os.path.join(DATA_DIR, "faiss_meta.db")
    # --- END OF CRITICAL SECTION ---

    USE_OPENAI: bool = False
    OPENAI_API_KEY: Optional[str] = None
    USE_LLAMA_CPP: bool = False
    LLAMA_MODEL_PATH: Optional[str] = None
    USE_GOOGLE_GENAI: bool = True
    GOOGLE_API_KEY: Optional[str] = None

    ENABLE_LOGIN_CRAWL: bool = False
    MAX_PAGES_PER_SESSION: int = 1000

    OPENAI_MODEL: str = "gpt-4o-mini"
    GOOGLE_MODEL: str = "gemini-1.5-flash"
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"

    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "password"

    REDIS_URL: Optional[str] = None

    HOST: str = "0.0.0.0"
    PORT: int = 8000

    class Config:
        env_file = ".env"
        extra = 'ignore'

settings = Settings()