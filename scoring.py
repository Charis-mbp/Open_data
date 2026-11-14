"""Scores and labels, computed from a theme's accepted matches only. Plain code, no model.

For each député, over the accepted scrutins held while they were in office:
    aligned  = votes equal to the wanted vote
    opposed  = votes equal to the opposite vote
    score    = 100 × aligned / (aligned + opposed)
Abstentions and absences (non-votant or no vote recorded) are counted and shown, never in the score.
"""
import json
import os
import sqlite3

import pandas as pd

from shortlist import DB_PATH, theme_path

# Thresholds; a theme can override them in theme.json under "scoring".
MIN_VOTES = 5          # fewer aligned + opposed votes: no score
SEUIL_ALLIE = 70       # score >= 70: allié
SEUIL_OPPOSANT = 30    # score <= 30: opposant
ECART_LOYAUTE = 5      # Hémicycle loyalty this many points or more BELOW the group median, and a theme score above
                       # the group average: à convaincre, "s'écarte de son groupe"
SANS_GROUPE = "Non inscrit"  # not a political group: no group average, the rule does not apply
NOTE_ECART = "s'écarte de son groupe"
HEMICYCLE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "hemicycle")

ALLIE = "allié"
OPPOSANT = "opposant"
A_CONVAINCRE = "à convaincre"
INSUFFISANT = "données insuffisantes"
LABELS = [ALLIE, A_CONVAINCRE, OPPOSANT, INSUFFISANT]


def seuils(theme):
    s = {"min_votes": MIN_VOTES, "seuil_allie": SEUIL_ALLIE, "seuil_opposant": SEUIL_OPPOSANT,
         "ecart_loyaute": ECART_LOYAUTE}
    path = theme_path(theme, "theme.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            s.update(json.load(f).get("scoring", {}))
    return s


def scrutins_acceptes(theme):
    """Accepted (or flipped) matches from validated.json, as a DataFrame."""
    path = theme_path(theme, "validated.json")
    if not os.path.exists(path):
        return pd.DataFrame()
    with open(path, encoding="utf-8") as f:
        decisions = json.load(f).get("decisions", {}).values()
    rows = [d for d in decisions if d["statut"] in ("accepte", "inverse") and d.get("vote_retenu")]
    df = pd.DataFrame(rows)
    if not df.empty:
        df["ambigu"] = df.get("ambigu", pd.Series(False, index=df.index)).fillna(False).astype(bool)
    return df


def detail_votes(theme):
    """One row per (député in office, accepted scrutin): how they voted and how it counts."""
    acc = scrutins_acceptes(theme)
    if acc.empty:
        return pd.DataFrame()
    con = sqlite3.connect(DB_PATH)
    marks = ",".join("?" * len(acc))
    ids = list(acc["scrutin_id"])
    scrutins = pd.read_sql_query(f"SELECT id AS scrutin_id, date FROM scrutins WHERE id IN ({marks})",
                                 con, params=ids)
    votes = pd.read_sql_query(f"SELECT scrutin_id, depute_id, position AS vote FROM votes "
                              f"WHERE scrutin_id IN ({marks})", con, params=ids)
    mandats = pd.read_sql_query("SELECT m.depute_id, m.debut, m.fin, d.nom, d.groupe "
                                "FROM mandats m JOIN deputes d ON d.id = m.depute_id", con)
    con.close()
    # every député in office on the date of each scrutin (joins done in pandas: SQLite planned them badly)
    df = scrutins.merge(mandats, how="cross")
    df = df[(df["debut"] <= df["date"]) & (df["fin"].isna() | (df["fin"] >= df["date"]))]
    df = df.drop_duplicates(["scrutin_id", "depute_id"])  # overlapping mandate periods
    df = df.merge(votes, on=["scrutin_id", "depute_id"], how="left")
    df["vote"] = df["vote"].fillna("absent")
    df = df[["scrutin_id", "date", "depute_id", "nom", "groupe", "vote"]]
    df = df.merge(acc[["scrutin_id", "numero", "titre", "url", "position_id", "position", "vote_retenu",
                       "raison", "ambigu"]],
                  on="scrutin_id")
    oppose = {"pour": "contre", "contre": "pour"}

    def categorie(r):
        if r.vote == r.vote_retenu:
            return "aligné"
        if r.vote == oppose[r.vote_retenu]:
            return "opposé"
        if r.vote == "abstention":
            return "abstention"
        return "absent"  # non-votant, or no vote recorded

    df["categorie"] = [categorie(r) for r in df.itertuples()]
    return df


def loyautes():
    """Hémicycle loyalty per député, from the cached loyaute_deputes responses (one file per group, all votes of
    the legislature, not theme-specific). Columns: depute_id, loyaute, mediane_groupe, votes_loyaute, ecarts.
    A député listed under several groups keeps the entry of their current group, else the one with most votes.
    Députés not listed (the most loyal of a large group, or under 20 votes) are absent: no loyalty, no flag."""
    rows = []
    if os.path.isdir(HEMICYCLE_DIR):
        for name in sorted(os.listdir(HEMICYCLE_DIR)):
            if not (name.startswith("loyaute_") and name.endswith(".json")):
                continue
            try:
                with open(os.path.join(HEMICYCLE_DIR, name), encoding="utf-8") as f:
                    data = json.load(f)
            except (OSError, ValueError):
                continue
            sigle = data["perimetre"]["groupe"]
            for d in data.get("deputes_moins_loyaux", []):
                rows.append({"depute_id": d["acteur"], "sigle": sigle, "loyaute": d["loyaute"],
                             "mediane_groupe": data["mediane_loyaute"], "votes_loyaute": d["votes"],
                             "ecarts": d["ecarts"]})
    cols = ["depute_id", "loyaute", "mediane_groupe", "votes_loyaute", "ecarts"]
    if not rows:
        return pd.DataFrame(columns=cols)
    df = pd.DataFrame(rows)
    con = sqlite3.connect(DB_PATH)
    actuel = dict(con.execute("SELECT d.id, g.sigle FROM deputes d JOIN groupes g ON g.nom = d.groupe").fetchall())
    con.close()
    df["_actuel"] = df["sigle"] == df["depute_id"].map(actuel)
    df = df.sort_values(["_actuel", "votes_loyaute"], ascending=False).drop_duplicates("depute_id")
    return df[cols]


def label(score, nb_exprimes, s):
    if nb_exprimes < s["min_votes"] or score is None:
        return INSUFFISANT
    if score >= s["seuil_allie"]:
        return ALLIE
    if score <= s["seuil_opposant"]:
        return OPPOSANT
    return A_CONVAINCRE


def scores(theme):
    """One row per député: counts, score and label. Includes former députés (en_mandat False)."""
    s = seuils(theme)
    detail = detail_votes(theme)
    con = sqlite3.connect(DB_PATH)
    deputes = pd.read_sql_query("""
        SELECT d.id AS depute_id, d.nom, d.groupe, d.circonscription,
               MAX(m.fin IS NULL) AS en_mandat
        FROM deputes d JOIN mandats m ON m.depute_id = d.id
        GROUP BY d.id
    """, con)
    con.close()
    deputes["en_mandat"] = deputes["en_mandat"].astype(bool)
    cols = ["aligné", "opposé", "abstention", "absent"]
    if detail.empty:
        counts = pd.DataFrame(0, index=deputes["depute_id"], columns=cols)
    else:
        counts = (detail.groupby(["depute_id", "categorie"]).size().unstack(fill_value=0)
                  .reindex(columns=cols, fill_value=0))
    df = deputes.merge(counts, left_on="depute_id", right_index=True, how="left")
    df[cols] = df[cols].fillna(0).astype(int)
    df = df.rename(columns={"aligné": "alignes", "opposé": "opposes", "abstention": "abstentions",
                            "absent": "absences"})
    df["exprimes"] = df["alignes"] + df["opposes"]
    df["score"] = [round(100 * a / e) if e else None for a, e in zip(df["alignes"], df["exprimes"])]
    df["label"] = [label(sc, e, s) for sc, e in zip(df["score"], df["exprimes"])]
    df.loc[df["exprimes"] < s["min_votes"], "score"] = None

    # Group average over current members who have a score; the rule applies to anyone with a score.
    moyennes = (df[df["en_mandat"] & df["score"].notna() & (df["groupe"] != SANS_GROUPE)]
                .groupby("groupe")["score"].mean())
    df["moyenne_groupe"] = df["groupe"].map(moyennes).round()
    # "S'écarte de son groupe": Hémicycle loyalty (all votes of the legislature) at least ecart_loyaute points
    # below their group's median. Kept only for députés MORE favourable than their group on this theme (user
    # decision of 2026-11-14): one less favourable than their own group is no lead, so they keep their label.
    df = df.merge(loyautes(), on="depute_id", how="left")
    df["ecart_loyaute"] = (100 * (df["mediane_groupe"] - df["loyaute"])).round(1)
    df["note"] = ""
    hors_ligne = (df["score"].notna() & df["moyenne_groupe"].notna() & (df["score"] > df["moyenne_groupe"])
                  & (df["ecart_loyaute"] >= s["ecart_loyaute"]) & (df["groupe"] != SANS_GROUPE))
    df.loc[hors_ligne, "label"] = A_CONVAINCRE
    df.loc[hors_ligne, "note"] = NOTE_ECART
    return df.sort_values(["score", "nom"], ascending=[False, True], na_position="last")


if __name__ == "__main__":
    import sys
    theme = sys.argv[1] if len(sys.argv) > 1 else "nucleaire"
    df = scores(theme)
    actuels = df[df["en_mandat"]]
    print(actuels["label"].value_counts().to_string())
    print(actuels.groupby("groupe")["score"].mean().round().sort_values(ascending=False).to_string())


# ---- Upcoming vote: reasons and fallback simulation (plain code, no model) ----

SEUIL_A_RENCONTRER = 40   # past score from which a député predicted against us is worth meeting
SEUIL_PRESENCE = 0.2      # below this share of votes cast on the theme's scrutins: simulated "absent"


def raison(r):
    """One French sentence explaining a député's label, from their scores."""
    if pd.isna(r["score"]):
        return f"Pas assez de votes ({r['exprimes']} pour ou contre) pour un score."
    txt = f"Score {int(r['score'])} sur {r['exprimes']} votes"
    if pd.notna(r.get("moyenne_groupe")):
        txt += f", groupe à {int(r['moyenne_groupe'])}"
    txt += f" : {r['label']}"
    if r.get("note"):
        txt += f", {r['note']}"
    return txt + "."


def simulation(theme, vote_voulu):
    """Fallback when Hémicycle gives nothing: predicted vote per current député from their past behaviour.
    Rarely present on the theme's scrutins -> absent; score >= 50 -> the wanted vote, else the opposite;
    no score -> follows their group's average the same way."""
    df = scores(theme)
    df = df[df["en_mandat"]].copy()
    oppose = {"pour": "contre", "contre": "pour"}[vote_voulu]
    total = df["exprimes"] + df["abstentions"] + df["absences"]
    presence = (df["exprimes"] + df["abstentions"]) / total.where(total > 0)
    base = df["score"].fillna(df["moyenne_groupe"])
    df["vote_predit"] = [
        "absent" if (pd.isna(p) or p < SEUIL_PRESENCE) else
        (vote_voulu if (pd.notna(b) and b >= 50) else oppose)
        for p, b in zip(presence, base)]
    return df
