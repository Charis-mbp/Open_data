"""Position extraction and vote matching, per theme.

Usage: python matching.py <theme>      (e.g. python matching.py nucleaire)
Reads themes/<theme>/position.txt and shortlist.json, writes themes/<theme>/matching.json.
"""
import json
import os
import sqlite3
import sys
from datetime import datetime

from llm import LLMUnavailable, ReponseManuelleAttendue, ask_json, log
from shortlist import DB_PATH, load_shortlist, theme_path

BATCH_SIZE = 20
EXPOSE_MAX = 700         # characters of the exposé sommaire sent to the model
EXPOSE_PARENT_MAX = 400  # for the amendment a sub-amendment modifies

SYSTEM_POSITIONS = """Tu analyses des documents de position d'organisations (associations, fédérations, \
entreprises) pour les comparer aux votes de l'Assemblée nationale. Tu réponds uniquement en JSON valide, \
sans texte autour."""

PROMPT_POSITIONS = """Voici le document de position d'une organisation.

<document>
{text}
</document>

Extrais de 3 à 6 positions que l'organisation défend. Chaque position :
- est une phrase courte en français, formulée comme ce que l'organisation veut \
(ex. « Construire de nouveaux réacteurs EPR2 ») ;
- est assez précise pour qu'on puisse dire si un vote au Parlement va dans son sens ou contre elle ;
- est accompagnée du passage du document qui la justifie, cité mot pour mot.

Réponds avec ce JSON, et rien d'autre :
{{"positions": [{{"position": "...", "passage": "..."}}]}}"""

SYSTEM_MATCHING = """Tu aides une organisation à repérer, parmi des scrutins de l'Assemblée nationale, \
ceux qui touchent à ses positions, et à dire comment elle aurait voulu que les députés votent. \
Tu ne notes pas les députés et tu ne les classes pas. Tu réponds uniquement en JSON valide, sans texte autour."""

PROMPT_MATCHING = """Positions de l'organisation :
{positions}

Scrutins à examiner :
{scrutins}

Pour chaque scrutin, décide s'il porte directement sur l'une des positions. S'il ne touche aucune \
position, ou seulement de loin, ne le mentionne pas. S'il en touche plusieurs, garde la plus directe.

Attention au sens du vote. Beaucoup de scrutins portent sur des amendements, des sous-amendements, \
des motions ou des articles :
- Le vote voulu dépend de ce que fait le texte soumis au vote, pas de son sujet. Voter « pour » un \
amendement qui affaiblit une position, c'est voter contre cette position : l'organisation voudrait alors « contre ».
- Un amendement de suppression d'un article supprime cet article : voter « pour » revient à rejeter l'article.
- Une motion de rejet ou de renvoi en commission vise à écarter le texte entier.
- Pour un amendement, l'exposé sommaire (rédigé par son auteur) et le groupe de l'auteur sont donnés \
quand ils existent. Appuie-toi d'abord sur l'exposé pour savoir ce que fait l'amendement, puis décide si \
l'adopter sert ou dessert la position. L'exposé peut être tronqué (« … »).
- Un sous-amendement modifie l'amendement visé, dont l'exposé est aussi donné : demande-toi si le \
sous-amendement renforce ou affaiblit cet amendement, et dans quel sens cela pousse la position.
- Confiance : élevée (0,8 et plus) quand l'exposé ou le titre rend le sens évident, comme un vote sur \
l'ensemble d'un texte ; nettement plus basse (0,5 ou moins) quand il n'y a pas d'exposé ou qu'il reste \
ambigu, et que tu dois deviner d'après l'auteur ou l'article.

Réponds avec un tableau JSON, et rien d'autre. Un élément par scrutin retenu :
[{{"numero": 2653, "position": "P1", "vote": "pour", "raison": "une phrase en français", "confiance": 0.7}}]
- "numero" : le numéro du scrutin ;
- "position" : l'identifiant de la position (P1, P2…) ;
- "vote" : « pour » ou « contre », le vote que l'organisation aurait voulu ;
- "raison" : une seule phrase en français qui explique le lien et le sens du vote ;
- "confiance" : un nombre entre 0 et 1.
Si aucun scrutin ne correspond, réponds []."""


def read_position_text(theme):
    path = theme_path(theme, "position.txt")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return f.read().strip()


def _validate_positions(data):
    items = data["positions"] if isinstance(data, dict) else data
    if not isinstance(items, list):
        raise ValueError("pas de liste de positions")
    clean = []
    for item in items:
        if isinstance(item, dict) and str(item.get("position", "")).strip():
            clean.append({"position": str(item["position"]).strip(),
                          "passage": str(item.get("passage", "")).strip()})
    if not 3 <= len(clean) <= 6:
        raise ValueError(f"{len(clean)} positions au lieu de 3 à 6")
    return clean


def extract_positions(theme, text):
    """Returns [{"id": "P1", "position": ..., "passage": ...}], or None if the model failed twice."""
    positions = ask_json(theme, "positions", SYSTEM_POSITIONS,
                         PROMPT_POSITIONS.format(text=text), _validate_positions)
    if positions is None:
        return None
    return [{"id": f"P{i}", **p} for i, p in enumerate(positions, 1)]


def _make_match_validator(numeros, position_ids, theme):
    def validate(data):
        if isinstance(data, dict):  # tolerate {"matches": [...]}
            data = next((v for v in data.values() if isinstance(v, list)), None)
        if not isinstance(data, list):
            raise ValueError("la réponse n'est pas un tableau JSON")
        clean, seen = [], set()
        for item in data:
            try:
                numero = int(item["numero"])
                pid = str(item["position"]).strip().upper()
                vote = str(item["vote"]).strip().lower()
                raison = str(item["raison"]).strip()
                confiance = float(item["confiance"])
            except (KeyError, TypeError, ValueError, AttributeError):
                log.warning("%s: élément ignoré, champs invalides : %r", theme, item)
                continue
            if (numero not in numeros or pid not in position_ids or vote not in ("pour", "contre")
                    or not raison or not 0 <= confiance <= 1 or numero in seen):
                log.warning("%s: élément ignoré, valeurs invalides : %r", theme, item)
                continue
            seen.add(numero)
            clean.append({"numero": numero, "position_id": pid, "vote_souhaite": vote,
                          "raison": raison, "confiance": round(confiance, 2)})
        return clean
    return validate


def tronquer(text, limit):
    text = " ".join((text or "").split())
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0] + " …"


def amendements_for(scrutin_ids):
    """{scrutin_id: {"numero", "auteur", "groupe", "expose", "parent": {...} or None}} from the database."""
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    marks = ",".join("?" * len(scrutin_ids))
    rows = con.execute(f"""
        SELECT s.id AS scrutin_id, a.numero, a.auteur, a.groupe, a.expose,
               p.numero AS p_numero, p.auteur AS p_auteur, p.groupe AS p_groupe, p.expose AS p_expose
        FROM scrutins s JOIN amendements a ON a.id = s.amendement_id
        LEFT JOIN amendements p ON p.id = a.parent_id
        WHERE s.id IN ({marks})
    """, list(scrutin_ids)).fetchall()
    con.close()
    out = {}
    for r in rows:
        parent = None
        if r["p_numero"]:
            parent = {"numero": r["p_numero"], "auteur": r["p_auteur"], "groupe": r["p_groupe"],
                      "expose": r["p_expose"]}
        out[r["scrutin_id"]] = {"numero": r["numero"], "auteur": r["auteur"], "groupe": r["groupe"],
                                "expose": r["expose"], "parent": parent}
    return out


def decrire_scrutin(s, amendement):
    lines = [f"- n° {s['numero']} ({s['date']}) : {s['titre']}"]
    if s.get("objet") and s["objet"] != s["titre"]:
        lines.append(f"  Objet : {s['objet']}")
    if amendement:
        groupe = (f" ({amendement['groupe']})"
                  if amendement["groupe"] and amendement["groupe"] not in amendement["auteur"] else "")
        lines.append(f"  Auteur : {amendement['auteur']}{groupe}")
        lines.append("  Exposé sommaire : "
                     + (tronquer(amendement["expose"], EXPOSE_MAX) or "(aucun)"))
        parent = amendement.get("parent")
        if parent:
            pg = f" ({parent['groupe']})" if parent["groupe"] else ""
            lines.append(f"  Amendement visé : n° {parent['numero']} de {parent['auteur']}{pg}. "
                         f"Exposé : {tronquer(parent['expose'], EXPOSE_PARENT_MAX) or '(aucun)'}")
    return "\n".join(lines)


def match_batch(theme, positions, batch, amendements):
    positions_txt = "\n".join(f"{p['id']}. {p['position']}" for p in positions)
    scrutins_txt = "\n".join(decrire_scrutin(s, amendements.get(s["id"])) for s in batch)
    validator = _make_match_validator({s["numero"] for s in batch}, {p["id"] for p in positions}, theme)
    return ask_json(theme, "matching", SYSTEM_MATCHING,
                    PROMPT_MATCHING.format(positions=positions_txt, scrutins=scrutins_txt), validator)


def run(theme, text=None, progress=None, avec_amendements=True, fichier="matching.json"):
    """Extract positions and match every shortlisted scrutin. Writes and returns matching.json.

    `progress(done, total)` is called after each batch. Raises LLMUnavailable if the model
    is needed and cannot be reached, or ValueError with a French message for missing inputs.
    """
    text = text if text is not None else read_position_text(theme)
    if not text:
        raise ValueError("Ce thème n'a pas de document de position (position.txt).")
    shortlist = load_shortlist(theme)
    if not shortlist:
        raise ValueError("La shortlist de ce thème n'a pas encore été calculée.")

    positions = extract_positions(theme, text)
    if positions is None:
        raise ValueError("Le modèle n'a pas pu extraire les positions (deux réponses invalides).")
    by_id = {p["id"]: p for p in positions}
    scrutins = shortlist["scrutins"]
    by_numero = {s["numero"]: s for s in scrutins}
    amendements = amendements_for([s["id"] for s in scrutins]) if avec_amendements else {}

    matches, skipped, attendus = [], [], 0
    batches = [scrutins[i:i + BATCH_SIZE] for i in range(0, len(scrutins), BATCH_SIZE)]
    for i, batch in enumerate(batches):
        try:
            result = match_batch(theme, positions, batch, amendements)
        except ReponseManuelleAttendue:
            attendus += 1  # write every missing prompt before stopping
            continue
        if result is None:
            skipped.append([s["numero"] for s in batch])
        else:
            for m in result:
                s = by_numero[m["numero"]]
                matches.append({
                    "scrutin_id": s["id"], "numero": s["numero"], "date": s["date"],
                    "titre": s["titre"], "url": s["url"],
                    "position_id": m["position_id"], "position": by_id[m["position_id"]]["position"],
                    "vote_souhaite": m["vote_souhaite"], "raison": m["raison"],
                    "confiance": m["confiance"],
                    "amendement": amendements.get(s["id"]),
                })
        if progress:
            progress(i + 1, len(batches))

    if attendus:
        raise ReponseManuelleAttendue(f"{attendus} lot(s) attendent une réponse dans "
                                      f"themes/{theme}/llm_manuel/")
    matches.sort(key=lambda m: (-m["confiance"], m["numero"]))
    result = {
        "theme": theme,
        "genere_le": datetime.now().isoformat(timespec="seconds"),
        "positions": positions,
        "matches": matches,
        "lots_ignores": skipped,  # scrutin numbers of batches the model failed twice on
        "avec_amendements": avec_amendements,
    }
    with open(theme_path(theme, fichier), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    return result


def load_matching(theme):
    path = theme_path(theme, "matching.json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


STATUTS = ("accepte", "inverse", "rejete")
OPPOSE = {"pour": "contre", "contre": "pour"}


def load_validated(theme):
    """{numero (str): decision}. Holds the manual review: never deleted, only updated entry by entry."""
    path = theme_path(theme, "validated.json")
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f).get("decisions", {})


def save_decision(theme, match, statut):
    """Record one decision (accepte, inverse or rejete) for a proposed match.

    Merges into the existing validated.json; a copy of the previous file is kept in
    validated.backup.json before each write.
    """
    if statut not in STATUTS:
        raise ValueError(statut)
    path = theme_path(theme, "validated.json")
    decisions = load_validated(theme)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as src, \
                open(theme_path(theme, "validated.backup.json"), "w", encoding="utf-8") as dst:
            dst.write(src.read())
    decisions[str(match["numero"])] = {
        "scrutin_id": match["scrutin_id"], "numero": match["numero"], "titre": match["titre"],
        "url": match["url"], "position_id": match["position_id"], "position": match["position"],
        "vote_propose": match["vote_souhaite"],
        # the vote used for scoring; None when rejected
        "vote_retenu": {"accepte": match["vote_souhaite"], "inverse": OPPOSE[match["vote_souhaite"]],
                        "rejete": None}[statut],
        "statut": statut, "raison": match["raison"], "confiance": match["confiance"],
        "decide_le": datetime.now().isoformat(timespec="seconds"),
    }
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"theme": theme, "decisions": decisions}, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    theme = args[0] if args else "nucleaire"
    try:
        runs = [run(theme, progress=lambda d, t: print(f"lot {d}/{t}"))]
        if "--comparer" in sys.argv:
            # same analysis on titles only, written to matching_titres.json, for comparison
            runs.append(run(theme, progress=lambda d, t: print(f"titres seuls, lot {d}/{t}"),
                            avec_amendements=False, fichier="matching_titres.json"))
    except (LLMUnavailable, ValueError) as e:
        sys.exit(f"Erreur : {e}")
    for r in runs:
        conf = [m["confiance"] for m in r["matches"]]
        moyenne = sum(conf) / len(conf) if conf else 0
        print(f"{'avec amendements' if r['avec_amendements'] else 'titres seuls'} : "
              f"{len(r['positions'])} positions, {len(r['matches'])} correspondances, "
              f"confiance moyenne {moyenne:.2f}, {len(r['lots_ignores'])} lots ignorés")
