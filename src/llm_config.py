"""
llm_config.py — single source of truth for the Groq chat model.

Groq decommissions models without notice (llama3-8b-8192 died mid-project
and every LLM stage silently degraded). Hardcoding model ids per call site
made the failure invisible, so all stages now resolve the model here:

    1. GROQ_MODEL env var (explicit override), else
    2. first preferred model that is ACTIVE for the current API key, else
    3. any other active chat-capable model, else
    4. a sane default (the call sites degrade gracefully if it 400s).

The resolved model is cached for the process lifetime.
"""

import logging
import os
import re
import threading
import time
from typing import Optional

logger = logging.getLogger(__name__)

# Order matters: best quality/fit first.
PREFERRED_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "qwen/qwen3.6-27b",
]

DEFAULT_MODEL = "llama-3.1-8b-instant"

# Model id fragments that are not general chat models.
_EXCLUDE = ("whisper", "tts", "guard", "embed", "compound", "orpheus", "playai")

_resolved: Optional[str] = None


def get_chat_model() -> str:
    """Return the chat model id to use for all Groq calls (cached)."""
    global _resolved
    if _resolved:
        return _resolved

    override = os.getenv("GROQ_MODEL", "").strip()
    if override:
        _resolved = override
        logger.info("Using GROQ_MODEL override: %s", override)
        return _resolved

    active = _list_active_models()
    if active:
        for preferred in PREFERRED_MODELS:
            if preferred in active:
                _resolved = preferred
                logger.info("Auto-selected Groq model: %s", preferred)
                return _resolved
        fallbacks = [m for m in active if not any(x in m for x in _EXCLUDE)]
        if fallbacks:
            _resolved = fallbacks[0]
            logger.info("No preferred model active; using %s", fallbacks[0])
            return _resolved

    _resolved = DEFAULT_MODEL
    logger.warning("Could not list Groq models; defaulting to %s", DEFAULT_MODEL)
    return _resolved


def _list_active_models() -> list:
    try:
        import groq
    except ImportError:
        return []

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return []

    try:
        client = groq.Groq(api_key=api_key)
        return sorted(m.id for m in client.models.list().data if getattr(m, "active", True))
    except Exception as e:
        logger.warning("Groq model listing failed: %s", e)
        return []


# ---------------------------------------------------------------------------
# Shared throttling. The Groq key caps out around ~8,000 tokens/min; bursts
# from the row-level thread pool spam 429s and every call degrades on its
# own. All LLM call sites funnel through call_with_retry(), which paces
# requests globally and honours the server-suggested wait on 429.
# ---------------------------------------------------------------------------

_CALL_LOCK = threading.Lock()
_LAST_CALL = [0.0]
MIN_INTERVAL = float(os.getenv("LLM_MIN_INTERVAL", "0.5"))
MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "3"))
_RETRY_AFTER = re.compile(r"try again in ([\d.]+)\s*s", re.IGNORECASE)


def _pace() -> None:
    with _CALL_LOCK:
        wait = _LAST_CALL[0] + MIN_INTERVAL - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        _LAST_CALL[0] = time.monotonic()


def call_with_retry(fn, what: str = "LLM call"):
    """Run a Groq API call with global pacing + 429 backoff."""
    delay = 2.0
    for attempt in range(MAX_RETRIES + 1):
        _pace()
        try:
            return fn()
        except Exception as e:
            msg = str(e)
            if "429" in msg and attempt < MAX_RETRIES:
                m = _RETRY_AFTER.search(msg)
                wait = min(float(m.group(1)) + 0.3, 15.0) if m else delay
                delay = min(delay * 2, 15.0)
                logger.warning(
                    "%s rate-limited; retrying in %.1fs (%d/%d)",
                    what, wait, attempt + 1, MAX_RETRIES,
                )
                time.sleep(wait)
                continue
            raise


def completion_kwargs(model: str, max_tokens: int) -> dict:
    """Model-aware kwargs so reasoning models keep their answer budget.

    Reasoning models (gpt-oss, qwen3) spend max_tokens on hidden reasoning
    first — with small budgets the visible content comes back EMPTY and
    every downstream JSON parse silently fails. So: suppress reasoning
    where the API allows it, and otherwise widen the budget.
    """
    kw = {"max_tokens": max_tokens}
    if "gpt-oss" in model:
        kw["reasoning_effort"] = "low"
    elif "qwen" in model:
        kw["reasoning_effort"] = "none"
    else:
        # Non-reasoning models (llama…) reject reasoning_effort outright.
        kw["max_tokens"] = max(max_tokens, 1024)
    return kw
