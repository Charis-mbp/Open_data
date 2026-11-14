"""Client for the Hémicycle API (vote predictions per député). The only place that calls it.

Settings in .env:
    HEMICYCLE_API_KEY=...
    HEMICYCLE_BASE_URL=https://...          (API root; not publicly documented, ask the organisers)
    HEMICYCLE_PREDICTION_PATH=/...{scrutin}  (path of the per-député prediction for one scrutin)
    HEMICYCLE_AUTH_HEADER=Authorization      (optional; the key is sent as "Bearer <key>" for Authorization,
                                              raw otherwise, e.g. X-API-Key)

Every successful response is cached in themes/<theme>/hemicycle_cache/<hash>.json, so the page works
offline once a prediction has been fetched. Nothing here ever raises to the caller: failures return None
and are logged in data/hemicycle.log.
"""
import hashlib
import json
import logging
import os
import urllib.error
import urllib.request

from dotenv import load_dotenv

ROOT = os.path.dirname(os.path.abspath(__file__))
THEMES_DIR = os.path.join(ROOT, "themes")
load_dotenv(os.path.join(ROOT, ".env"))

log = logging.getLogger("hemicycle")
if not log.handlers:
    os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
    h = logging.FileHandler(os.path.join(ROOT, "data", "hemicycle.log"), encoding="utf-8")
    h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    log.addHandler(h)
    log.setLevel(logging.INFO)

VOTES = {"pour": "pour", "for": "pour", "contre": "contre", "against": "contre",
         "abstention": "abstention", "abstain": "abstention", "absent": "absent", "non-votant": "absent"}


def configure():
    return bool(os.getenv("HEMICYCLE_API_KEY") and os.getenv("HEMICYCLE_BASE_URL")
                and os.getenv("HEMICYCLE_PREDICTION_PATH"))


def _get(theme, path):
    """GET base+path with the key; cached by theme and hash of the URL. Returns parsed JSON or None."""
    url = os.getenv("HEMICYCLE_BASE_URL", "").rstrip("/") + path
    folder = os.path.join(THEMES_DIR, theme, "hemicycle_cache")
    os.makedirs(folder, exist_ok=True)
    cache = os.path.join(folder, hashlib.sha256(url.encode()).hexdigest()[:24] + ".json")
    if os.path.exists(cache):
        with open(cache, encoding="utf-8") as f:
            return json.load(f)["reponse"]
    header = os.getenv("HEMICYCLE_AUTH_HEADER", "Authorization")
    key = os.getenv("HEMICYCLE_API_KEY", "")
    req = urllib.request.Request(url, headers={
        header: f"Bearer {key}" if header.lower() == "authorization" else key,
        "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ValueError, OSError) as e:
        log.warning("GET %s : %s", url, e)
        return None
    if not data:
        log.warning("GET %s : réponse vide", url)
        return None
    with open(cache, "w", encoding="utf-8") as f:
        json.dump({"url": url, "reponse": data}, f, ensure_ascii=False, indent=1)
    return data


def predictions(theme, scrutin_ref):
    """Per-député predictions for one upcoming scrutin, normalised to
    [{"depute_id": "PA…" or None, "nom": str or None, "vote": pour|contre|abstention|absent}], or None.

    The response format is not documented yet: this accepts a list, or a dict holding the list under
    "predictions" / "deputes" / "votes" / "data", with the député under id/uid/acteurRef/depute_id/nom and
    the vote under vote/prediction/position/predicted_vote.
    """
    if not configure():
        return None
    data = _get(theme, os.getenv("HEMICYCLE_PREDICTION_PATH").replace("{scrutin}", str(scrutin_ref)))
    if isinstance(data, dict):
        data = next((data[k] for k in ("predictions", "deputes", "votes", "data") if isinstance(data.get(k), list)),
                    None)
    if not isinstance(data, list):
        return None
    out = []
    for item in data:
        if not isinstance(item, dict):
            continue
        ident = next((item[k] for k in ("acteurRef", "depute_id", "uid", "id") if item.get(k)), None)
        vote = next((item[k] for k in ("vote", "prediction", "position", "predicted_vote") if item.get(k)), None)
        vote = VOTES.get(str(vote).strip().lower()) if vote else None
        if vote and (ident or item.get("nom")):
            out.append({"depute_id": ident if str(ident).startswith("PA") else None,
                        "nom": item.get("nom") or item.get("name"), "vote": vote})
    return out or None
