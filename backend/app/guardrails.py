import re
import logging
from .config import settings

logger = logging.getLogger(__name__)

# simple PII regexes
EMAIL_RE = re.compile(r"[\w\.-]+@[\w\.-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(r"\+?\d[\d \-()]{7,}\d")
SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")

# disallowed keywords example (customize)
DISALLOWED_KEYWORDS = ["bomb", "explosive", "kill", "terrorist"]  # extend as needed

def detect_pii(text: str):
    emails = EMAIL_RE.findall(text)
    phones = PHONE_RE.findall(text)
    ssns = SSN_RE.findall(text)
    return {'emails': emails, 'phones': phones, 'ssns': ssns}

def redact_pii(text: str):
    text = EMAIL_RE.sub('[REDACTED_EMAIL]', text)
    text = SSN_RE.sub('[REDACTED_SSN]', text)
    text = PHONE_RE.sub('[REDACTED_PHONE]', text)
    return text

def contains_disallowed(text: str):
    lower = text.lower()
    for kw in DISALLOWED_KEYWORDS:
        if kw in lower:
            return True, kw
    return False, None

# optional: call OpenAI moderation API if configured
def check_moderation_with_openai(text: str):
    try:
        import openai
    except Exception:
        logger.info('openai not installed; skipping moderation')
        return {'result': 'skipped', 'reason': 'openai_not_installed'}
    if not settings.OPENAI_API_KEY:
        return {'result': 'skipped', 'reason': 'no_api_key'}
    openai.api_key = settings.OPENAI_API_KEY
    try:
        resp = openai.Moderation.create(input=text)
        return {'result': resp['results'][0]}
    except Exception as e:
        logger.exception('OpenAI moderation call failed: %s', e)
        return {'result': 'error', 'error': str(e)}
