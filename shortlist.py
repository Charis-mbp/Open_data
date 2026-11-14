"""Build the shortlist of scrutins for one theme.

Usage: python shortlist.py <theme>      (e.g. python shortlist.py nucleaire)
Writes themes/<theme>/shortlist.json.
"""
import json
import os
import re
import sqlite3
import sys
import unicodedata
from datetime import datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
# Full database built by load_data.py; when it is absent (e.g. on a deploy), the small demo copy
# written by make_demo_db.py, which holds only the shortlisted scrutins.
FULL_DB_PATH = os.path.join(ROOT, "data", "boussole.db")
DEMO_DB_PATH = os.path.join(ROOT, "data", "boussole_demo.db")
DB_PATH = FULL_DB_PATH if os.path.exists(FULL_DB_PATH) else DEMO_DB_PATH
THEMES_DIR = os.path.join(ROOT, "themes")

# Defaults; a theme can override them in theme.json under "shortlist".
MIN_VOTANTS = 50        # pour + contre + abstention
MAX_MEME_COTE = 0.90    # share of expressed votes (pour + contre) on the majority side
MAX_SCRUTINS = 150


def normalise(text):
    """Lower case, no accents, typographic apostrophes made plain."""
    text = unicodedata.normalize("NFKD", str(text).replace("’", "'"))
    return "".join(c for c in text if not unicodedata.combining(c)).lower()


def theme_path(theme, filename):
    return os.path.join(THEMES_DIR, theme, filename)


def read_keywords(theme):
    with open(theme_path(theme, "keywords.txt"), encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]


def read_settings(theme):
    settings = {"min_votants": MIN_VOTANTS, "max_meme_cote": MAX_MEME_COTE, "max_scrutins": MAX_SCRUTINS}
    path = theme_path(theme, "theme.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            settings.update(json.load(f).get("shortlist", {}))
    return settings


def keyword_patterns(keywords):
    # Whole-word match: "EPR" must not match "reprise", "nucléaire" does not match "nucléaires".
    return [(k, re.compile(r"(?<!\w)" + re.escape(normalise(k)) + r"(?!\w)")) for k in keywords]


def build_shortlist(theme):
    keywords = read_keywords(theme)
    settings = read_settings(theme)
    patterns = keyword_patterns(keywords)

    con = sqlite3.connect(DB_PATH)
    rows = con.execute("""
        SELECT s.id, s.numero, s.date, s.titre, s.objet, s.resultat, s.url,
               SUM(v.position = 'pour'), SUM(v.position = 'contre'), SUM(v.position = 'abstention')
        FROM scrutins s JOIN votes v ON v.scrutin_id = s.id
        GROUP BY s.id
    """).fetchall()
    con.close()

    stats = {"correspondances": 0, "moins_de_votants": 0, "trop_desequilibres": 0}
    kept = []
    for sid, numero, date, titre, objet, resultat, url, pour, contre, abst in rows:
        text = normalise(f"{titre} {objet}")
        matched = [k for k, p in patterns if p.search(text)]
        if not matched:
            continue
        stats["correspondances"] += 1
        if pour + contre + abst < settings["min_votants"]:
            stats["moins_de_votants"] += 1
            continue
        exprimes = pour + contre
        if exprimes == 0 or max(pour, contre) / exprimes > settings["max_meme_cote"]:
            stats["trop_desequilibres"] += 1
            continue
        kept.append({
            "id": sid, "numero": numero, "date": date, "titre": titre, "objet": objet,
            "resultat": resultat, "url": url,
            "pour": pour, "contre": contre, "abstention": abst,
            "ecart": round(abs(pour - contre) / exprimes, 4),  # 0 = perfectly even split
            "mots_cles": matched,
        })

    stats["apres_filtres"] = len(kept)
    kept.sort(key=lambda s: (s["ecart"], s["numero"]))
    kept = kept[: settings["max_scrutins"]]
    kept.sort(key=lambda s: (s["date"], s["numero"]))
    stats["retenus"] = len(kept)

    result = {
        "theme": theme,
        "genere_le": datetime.now().isoformat(timespec="seconds"),
        "mots_cles": keywords,
        "regles": settings,
        "statistiques": stats,
        "scrutins": kept,
    }
    with open(theme_path(theme, "shortlist.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    return result


def load_shortlist(theme):
    path = theme_path(theme, "shortlist.json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


if __name__ == "__main__":
    theme = sys.argv[1] if len(sys.argv) > 1 else "nucleaire"
    r = build_shortlist(theme)
    print(theme, r["statistiques"])
