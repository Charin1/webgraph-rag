import logging
from typing import Generator
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

# --- Llama.cpp model instance and initializer ---
# This logic now lives here, breaking the circular dependency.
_llama_model = None

def _init_llama():
    global _llama_model
    if _llama_model is None and settings.USE_LLAMA_CPP and Llama:
        if not settings.LLAMA_MODEL_PATH:
            raise ValueError("LLAMA model path not set in config")
        _llama_model = Llama(model_path=settings.LLAMA_MODEL_PATH, n_ctx=2048)
    return _llama_model

# --- Streaming generator for Google GenAI ---
def stream_google_genai(prompt: str) -> Generator[str, None, None]:
    if genai is None:
        raise RuntimeError('google-generativeai package is not installed')
    if not settings.GOOGLE_API_KEY:
        raise ValueError("GOOGLE_API_KEY not set in config")
    
    genai.configure(api_key=settings.GOOGLE_API_KEY)
    model = genai.GenerativeModel(settings.GOOGLE_MODEL)
    
    try:
        response = model.generate_content(prompt, stream=True)
        for chunk in response:
            if chunk.text:
                yield chunk.text
    except Exception as e:
        logger.exception('Google GenAI streaming error: %s', e)
        yield f"\n\nError during streaming: {e}"

# --- Streaming generator for OpenAI ---
def stream_openai_chat(prompt: str) -> Generator[str, None, None]:
    if openai is None:
        raise RuntimeError('openai package is not installed')
    openai.api_key = settings.OPENAI_API_KEY
    resp = openai.ChatCompletion.create(
        model=settings.OPENAI_MODEL, 
        messages=[{'role':'user','content':prompt}], 
        stream=True, 
        max_tokens=1024, 
        temperature=0.1
    )
    for chunk in resp:
        try:
            choices = chunk.get('choices', [])
            if not choices: continue
            delta = choices[0].get('delta', {})
            text = delta.get('content')
            if text:
                yield text
        except Exception as e:
            logger.exception('OpenAI stream chunk parse error: %s', e)
            continue

# --- Streaming generator for llama.cpp ---
def stream_llama(prompt: str) -> Generator[str, None, None]:
    if Llama is None:
        raise RuntimeError('llama_cpp not available')
    
    llama = _init_llama() # This now calls the function within this same file
    if llama is None:
        raise RuntimeError("Llama.cpp model could not be initialized.")
        
    out = llama.create_completion(prompt=prompt, max_tokens=1024, temperature=0.1, stream=True)
    for chunk in out:
        text = chunk['choices'][0].get('text', '')
        yield text

# --- Main streaming dispatcher ---
def stream_llm(prompt: str) -> Generator[str, None, None]:
    """
    Selects the appropriate LLM based on config and returns its streaming generator.
    """
    if settings.USE_GOOGLE_GENAI:
        logger.info("Using Google GenAI for streaming response.")
        return stream_google_genai(prompt)
    
    if settings.USE_OPENAI:
        logger.info("Using OpenAI for streaming response.")
        return stream_openai_chat(prompt)
    
    if settings.USE_LLAMA_CPP:
        logger.info("Using Llama.cpp for streaming response.")
        return stream_llama(prompt)
        
    raise RuntimeError('No LLM configured for streaming.')