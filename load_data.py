"""Download the Assemblée nationale open data (17th legislature) and load it into SQLite.

Usage: python load_data.py          (downloads only the missing files)
       python load_data.py --force  (downloads again)
"""
import glob
import json
import os
import sqlite3
import sys
import urllib.request
import zipfile

LEGISLATURE = "17"
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
DB_PATH = os.path.join(DATA, "boussole.db")
BASE = f"https://data.assemblee-nationale.fr/static/openData/repository/{LEGISLATURE}"
SOURCES = {
    # zip name -> (url, folder it is extracted to)
    "Scrutins.json.zip": (f"{BASE}/loi/scrutins/Scrutins.json.zip", "scrutins"),
    # every député, sénateur and minister of the legislature, including former députés
    "AMO20.json.zip": (
        f"{BASE}/amo/deputes_senateurs_ministres_legislature/"
        "AMO20_dep_sen_min_tous_mandats_et_organes.json.zip",
        "amo20",
    ),
}
POSITIONS = {
    "pours": "pour",
    "contres": "contre",
    "abstentions": "abstention",
    "nonVotants": "non-votant",
    "nonVotantsVolontaires": "non-votant",
}


def as_list(x):
    if x is None:
        return []
    return x if isinstance(x, list) else [x]


def download(force=False):
    os.makedirs(DATA, exist_ok=True)
    for name, (url, folder) in SOURCES.items():
        zpath = os.path.join(DATA, name)
        if force or not os.path.exists(zpath):
            print("Téléchargement", url)
            urllib.request.urlretrieve(url, zpath)
        target = os.path.join(DATA, folder)
        if force or not os.path.isdir(target):
            with zipfile.ZipFile(zpath) as z:
                z.extractall(target)


def load_deputes():
    organes = {}
    for f in glob.glob(os.path.join(DATA, "amo20/json/organe/*.json")):
        o = json.load(open(f, encoding="utf-8"))["organe"]
        organes[o["uid"]] = o.get("libelle")

    rows = []
    for f in glob.glob(os.path.join(DATA, "amo20/json/acteur/*.json")):
        a = json.load(open(f, encoding="utf-8"))["acteur"]
        mandats = as_list(a["mandats"]["mandat"])
        assemblee = [
            m for m in mandats
            if m["typeOrgane"] == "ASSEMBLEE" and m.get("legislature") == LEGISLATURE
        ]
        if not assemblee:
            continue  # sénateur or minister only
        ident = a["etatCivil"]["ident"]
        nom = f"{ident['prenom']} {ident['nom']}"

        last = max(assemblee, key=lambda m: m["dateDebut"])
        lieu = (last.get("election") or {}).get("lieu") or {}
        circo = ""
        if lieu.get("departement"):
            num = lieu.get("numCirco") or ""
            circo = f"{lieu['departement']} ({lieu.get('numDepartement', '')})"
            if num:
                circo += f" – {num}e circ." if num != "1" else " – 1re circ."

        # current political group, or the last one if the mandate has ended
        gps = [
            m for m in mandats
            if m["typeOrgane"] == "GP" and m.get("legislature") == LEGISLATURE
        ]
        groupe = ""
        if gps:
            gp = max(gps, key=lambda m: (m.get("dateFin") is None, m["dateDebut"]))
            groupe = organes.get(gp["organes"]["organeRef"], "")
        rows.append((a["uid"]["#text"] if isinstance(a["uid"], dict) else a["uid"], nom, groupe, circo))
    return rows


def load_scrutins():
    scrutins, votes = [], []
    for f in glob.glob(os.path.join(DATA, "scrutins/json/*.json")):
        s = json.load(open(f, encoding="utf-8"))["scrutin"]
        url = f"https://www.assemblee-nationale.fr/dyn/{LEGISLATURE}/scrutins/{s['numero']}"
        scrutins.append((
            s["uid"], s["dateScrutin"], s["titre"],
            (s.get("objet") or {}).get("libelle") or "",
            s["sort"]["code"], url, int(s["numero"]),
        ))
        groupes = as_list(s["ventilationVotes"]["organe"]["groupes"]["groupe"])
        for g in groupes:
            nominatif = g["vote"].get("decompteNominatif") or {}
            for key, position in POSITIONS.items():
                for v in as_list((nominatif.get(key) or {}).get("votant")):
                    votes.append((s["uid"], v["acteurRef"], position))
    return scrutins, votes


def build_db():
    deputes = load_deputes()
    scrutins, votes = load_scrutins()
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    con = sqlite3.connect(DB_PATH)
    con.executescript("""
        CREATE TABLE deputes (id TEXT PRIMARY KEY, nom TEXT, groupe TEXT, circonscription TEXT);
        CREATE TABLE scrutins (id TEXT PRIMARY KEY, date TEXT, titre TEXT, objet TEXT,
                               resultat TEXT, url TEXT, numero INTEGER);
        CREATE TABLE votes (scrutin_id TEXT, depute_id TEXT, position TEXT);
    """)
    con.executemany("INSERT INTO deputes VALUES (?,?,?,?)", deputes)
    con.executemany("INSERT INTO scrutins VALUES (?,?,?,?,?,?,?)", scrutins)
    con.executemany("INSERT INTO votes VALUES (?,?,?)", votes)
    con.executescript("""
        CREATE INDEX idx_votes_scrutin ON votes(scrutin_id);
        CREATE INDEX idx_votes_depute ON votes(depute_id);
    """)
    con.commit()
    con.close()
    print(f"{len(deputes)} députés, {len(scrutins)} scrutins, {len(votes)} votes -> {DB_PATH}")


def check_counts():
    """Compare the counts rebuilt from individual votes with the official totals."""
    con = sqlite3.connect(DB_PATH)
    counts = {}
    for sid, pos, n in con.execute(
        "SELECT scrutin_id, position, COUNT(*) FROM votes GROUP BY scrutin_id, position"
    ):
        counts.setdefault(sid, {})[pos] = n
    unknown = con.execute(
        "SELECT COUNT(DISTINCT depute_id) FROM votes WHERE depute_id NOT IN (SELECT id FROM deputes)"
    ).fetchone()[0]
    con.close()
    bad = 0
    for f in glob.glob(os.path.join(DATA, "scrutins/json/*.json")):
        s = json.load(open(f, encoding="utf-8"))["scrutin"]
        d = s["syntheseVote"]["decompte"]
        c = counts.get(s["uid"], {})
        if (int(d["pour"]), int(d["contre"]), int(d["abstentions"])) != (
            c.get("pour", 0), c.get("contre", 0), c.get("abstention", 0)
        ):
            bad += 1
    print(f"Contrôle : {bad} scrutins dont les décomptes diffèrent du total officiel, "
          f"{unknown} votants absents de la table deputes")


if __name__ == "__main__":
    download(force="--force" in sys.argv)
    build_db()
    check_counts()
