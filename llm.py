"""The only place that calls a language model.

Settings come from .env:
    LLM_PROVIDER=anthropic
    LLM_MODEL=claude-opus-5-5
    ANTHROPIC_API_KEY=...

Every successful answer is cached in themes/<theme>/llm_cache/<hash>.json, the hash covering
provider, model, task, system prompt and prompt. A cached call never touches the network.
"""
import hashlib
import json
import logging
import os
import re

from dotenv import load_dotenv

ROOT = os.path.dirname(os.path.abspath(__file__))
THEMES_DIR = os.path.join(ROOT, "themes")
LOG_PATH = os.path.join(ROOT, "data", "llm.log")

load_dotenv(os.path.join(ROOT, ".env"))

os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
log = logging.getLogger("llm")
if not log.handlers:
    handler = logging.FileHandler(LOG_PATH, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    log.addHandler(handler)
    log.setLevel(logging.INFO)


class LLMUnavailable(Exception):
    """No cached answer and the model cannot be called (no key, no network, bad settings)."""


def settings():
    return os.getenv("LLM_PROVIDER", "anthropic"), os.getenv("LLM_MODEL", "claude-opus-5-5")


def _cache_path(theme, key):
    folder = os.path.join(THEMES_DIR, theme, "llm_cache")
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, f"{key}.json")


def _parse_json(text):
    """Parse the model's answer, tolerating a ```json fence around it."""
    text = text.strip()
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.S)
    if fence:
        text = fence.group(1)
    return json.loads(text)


def _call_anthropic(model, system, prompt):
    import anthropic

    client = anthropic.Anthropic()
    try:
        response = client.beta.messages.create(
            model=model,
            max_tokens=16000,
            system=system,
            messages=[{"role": "user", "content": prompt}],
            output_config={"effort": "medium"},
            # if the model declines, the API retries on another model in the same call
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
    except anthropic.AuthenticationError as e:
        raise LLMUnavailable("clé API invalide ou absente") from e
    except anthropic.APIConnectionError as e:
        raise LLMUnavailable("pas de connexion au service du modèle") from e
    except anthropic.APIStatusError as e:
        raise LLMUnavailable(f"erreur du service du modèle ({e.status_code})") from e
    if response.stop_reason == "refusal":
        raise ValueError("le modèle a refusé de répondre")
    if response.stop_reason == "max_tokens":
        raise ValueError("réponse tronquée")
    return "".join(b.text for b in response.content if b.type == "text")


def _call(provider, model, system, prompt):
    if provider == "anthropic":
        if not (os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN")):
            raise LLMUnavailable("ANTHROPIC_API_KEY absent du fichier .env")
        return _call_anthropic(model, system, prompt)
    raise LLMUnavailable(f"fournisseur inconnu dans .env : {provider}")


def ask_json(theme, task, system, prompt, validate):
    """Ask the model for JSON, validate it, cache it.

    `validate(data)` returns the cleaned data or raises ValueError.
    Returns the cleaned data, or None if two attempts gave invalid JSON (logged).
    Raises LLMUnavailable when there is no cache and the model cannot be reached.
    """
    provider, model = settings()
    key = hashlib.sha256(
        json.dumps([provider, model, task, system, prompt], ensure_ascii=False).encode("utf-8")
    ).hexdigest()[:24]
    path = _cache_path(theme, key)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)["result"]

    for attempt in (1, 2):
        try:
            raw = _call(provider, model, system, prompt)
            result = validate(_parse_json(raw))
        except (ValueError, TypeError, KeyError) as e:  # json.JSONDecodeError is a ValueError
            log.warning("%s %s: réponse invalide (essai %d): %s", theme, task, attempt, e)
            continue
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"theme": theme, "task": task, "provider": provider, "model": model,
                       "result": result}, f, ensure_ascii=False, indent=1)
        return result
    log.error("%s %s: abandonné après 2 réponses invalides", theme, task)
    return None
