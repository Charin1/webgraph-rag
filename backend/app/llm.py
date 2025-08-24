import logging
from .config import settings

logger = logging.getLogger(__name__)

# --- Try importing all potential LLM libraries ---
try:
    import openai
except ImportError:
    openai = None

try:
    from llama_cpp import Llama
except ImportError:
    Llama = None

try:
    import google.generativeai as genai
except ImportError:
    genai = None

# --- Global model instance for Google ---
_google_model = None

def _init_google():
    global _google_model
    if _google_model is None and settings.USE_GOOGLE_GENAI and genai:
        if not settings.GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY not set in config")
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        _google_model = genai.GenerativeModel(settings.GOOGLE_MODEL)
    return _google_model

def ask_llm(prompt: str, max_tokens: int = 1024, temperature: float = 0.1) -> str:
    """
    Sends a prompt to the configured LLM and returns a single, non-streamed response.
    """
    if settings.USE_GOOGLE_GENAI:
        model = _init_google()
        if model is None:
            raise RuntimeError("Google GenAI SDK not available or configured.")
        try:
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Google GenAI API call failed: {e}")
            return "Error: Could not get a response from the Google GenAI API."

    if settings.USE_OPENAI and openai:
        openai.api_key = settings.OPENAI_API_KEY
        resp = openai.ChatCompletion.create(
            model=settings.OPENAI_MODEL,
            messages=[{"role":"user","content":prompt}],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return resp['choices'][0]['message']['content']

    # Non-streaming Llama is removed from here to simplify dependencies.
    # Streaming is the primary use case for it in this app.
    if settings.USE_LLAMA_CPP:
         return "Error: Non-streaming Llama.cpp is not configured in llm.py. Please use the streaming endpoint."

    raise RuntimeError("No LLM has been configured. Please set USE_GOOGLE_GENAI or USE_OPENAI in your .env file.")