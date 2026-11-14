"""Download the Assemblée nationale open data (17th legislature) and load it into SQLite.

Usage: python load_data.py          (downloads only the missing files)
       python load_data.py --force  (downloads again)
"""
import glob
import html
import json
import os
import re
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
    # every amendment of the legislature (about 360 MB); read inside the zip, never extracted
    "Amendements.json.zip": (f"{BASE}/loi/amendements_div_legis/Amendements.json.zip", None),
}
SEANCE = "PO838901"  # the organe "Assemblée nationale" in séance publique
# "l'amendement n° 345 de M. X …", "le sous-amendement n° 781 …", "l'amendement de suppression n° 622 …"
AMENDEMENT_TITRE = re.compile(r"^(?:l'amendement|le sous-amendement)(?: de suppression)? n° ?(\d+)")
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
        if folder is None:
            continue
        target = os.path.join(DATA, folder)
        if force or not os.path.isdir(target):
            with zipfile.ZipFile(zpath) as z:
                z.extractall(target)


def load_groupes():
    rows = []
    for f in glob.glob(os.path.join(DATA, "amo20/json/organe/*.json")):
        o = json.load(open(f, encoding="utf-8"))["organe"]
        if o.get("codeType") == "GP":
            rows.append((o["uid"], o.get("libelle"), o.get("libelleAbrev")))
    return rows


def load_deputes():
    organes = {}
    for f in glob.glob(os.path.join(DATA, "amo20/json/organe/*.json")):
        o = json.load(open(f, encoding="utf-8"))["organe"]
        organes[o["uid"]] = o.get("libelle")

    rows, periodes = [], []
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
        uid = a["uid"]["#text"] if isinstance(a["uid"], dict) else a["uid"]
        rows.append((uid, nom, groupe, circo))
        periodes += [(uid, m["dateDebut"], m.get("dateFin")) for m in assemblee]
    return rows, periodes


def html_to_text(fragment):
    if not isinstance(fragment, str):
        return ""
    text = re.sub(r"</p>|<br\s*/?>", "\n", fragment)
    text = re.sub(r"<[^>]+>", " ", text)
    for _ in range(3):  # some exposés are escaped twice ("&amp;amp;")
        text = html.unescape(text)
    return "\n".join(re.sub(r"\s+", " ", line).strip() for line in text.split("\n") if line.strip())


def nil(x):
    """The files mark empty fields as {"@xsi:nil": "true"}."""
    return x is None or (isinstance(x, dict) and x.get("@xsi:nil") == "true")


def premier_signataire(libelle):
    """"M. Alfandari, M. Albertini, … et Mme Violland" -> "M. Alfandari et al." """
    premier = re.split(r",| et ", libelle, maxsplit=1)[0].strip()
    return premier + (" et al." if premier != libelle.strip() else "")


def parse_amendement(a, sigles):
    auteur = a["signataires"]["auteur"]
    if auteur.get("typeAuteur") == "Gouvernement":
        groupe = "Gouvernement"
    elif not nil(auteur.get("groupePolitiqueRef")):
        groupe = sigles.get(auteur["groupePolitiqueRef"], "")
    else:
        groupe = auteur.get("typeAuteur", "")  # Rapporteur, Commission…
    parent = a.get("amendementParentRef")
    contenu = a["corps"].get("contenuAuteur") or {}
    return {
        "id": a["uid"], "numero": a["identification"]["numeroLong"],
        "auteur": premier_signataire(html.unescape(a["signataires"].get("libelle") or "")),
        "groupe": groupe,
        "expose": html_to_text(contenu.get("exposeSommaire")),
        "dispositif": html_to_text(contenu.get("dispositif")),
        "sort": a["cycleDeVie"].get("sort") if not nil(a["cycleDeVie"].get("sort")) else "",
        "parent_id": None if nil(parent) else parent,
    }


def sans_accents(text):
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c)).lower()


def auteur_cite(auteur, titre):
    """True if the first signatory's surname (or "Gouvernement") appears in the scrutin title."""
    premier = re.split(r",| et ", auteur)[0].strip()
    nom = re.sub(r"^(M\.|Mme)\s+", "", premier).split(" ")[-1] if premier else ""
    return bool(nom) and sans_accents(nom) in sans_accents(titre)


def load_amendements(scrutins, sigles):
    """Find the amendment voted in each scrutin, joined on (séance, numéro).

    Returns (amendement rows, {scrutin_id: amendement_id}). Parents of sub-amendments are included.
    """
    wanted, titres = {}, {}
    for sid, _, titre, _, _, _, _, seance_ref in scrutins:
        m = AMENDEMENT_TITRE.match(titre)
        if m and seance_ref:
            wanted[(seance_ref, m.group(1))] = sid
            titres[sid] = titre
    zpath = os.path.join(DATA, "Amendements.json.zip")
    found, candidates = {}, {}
    with zipfile.ZipFile(zpath) as z:
        names = {n.rsplit("/", 1)[-1][:-5]: n for n in z.namelist() if n.endswith(".json")}
        for uid, name in names.items():
            if SEANCE not in uid:  # committee amendments are never voted by scrutin public
                continue
            a = json.loads(z.read(name))["amendement"]
            seance = a.get("seanceDiscussionRef")
            numero = re.match(r"\d+", a["identification"]["numeroLong"] or "")
            if nil(seance) or not numero:
                continue
            sid = wanted.get((seance, numero.group(0)))
            if sid:
                candidates.setdefault(sid, []).append(parse_amendement(a, sigles))
        # Two texts debated in the same séance can both have an amendment n° 14:
        # keep the one whose author is named in the scrutin title.
        links = {}
        for sid, cands in candidates.items():
            best = next((c for c in cands if auteur_cite(c["auteur"], titres[sid])), cands[0])
            found[best["id"]] = best
            links[sid] = best["id"]
        # parents of sub-amendments, read directly by file name
        for parent in {r["parent_id"] for r in found.values() if r["parent_id"]} - set(found):
            if parent in names:
                found[parent] = parse_amendement(json.loads(z.read(names[parent]))["amendement"], sigles)
    print(f"Amendements : {len(links)} scrutins reliés sur {len(wanted)} scrutins d'amendement")
    return list(found.values()), links


def load_scrutins():
    scrutins, votes = [], []
    for f in glob.glob(os.path.join(DATA, "scrutins/json/*.json")):
        s = json.load(open(f, encoding="utf-8"))["scrutin"]
        url = f"https://www.assemblee-nationale.fr/dyn/{LEGISLATURE}/scrutins/{s['numero']}"
        scrutins.append((
            s["uid"], s["dateScrutin"], s["titre"],
            (s.get("objet") or {}).get("libelle") or "",
            s["sort"]["code"], url, int(s["numero"]), s.get("seanceRef"),
        ))
        groupes = as_list(s["ventilationVotes"]["organe"]["groupes"]["groupe"])
        for g in groupes:
            nominatif = g["vote"].get("decompteNominatif") or {}
            for key, position in POSITIONS.items():
                for v in as_list((nominatif.get(key) or {}).get("votant")):
                    votes.append((s["uid"], v["acteurRef"], position, g["organeRef"]))
    return scrutins, votes


def build_db():
    deputes, periodes = load_deputes()
    scrutins, votes = load_scrutins()
    groupes = load_groupes()
    amendements, links = load_amendements(scrutins, {g[0]: g[2] for g in groupes})
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    con = sqlite3.connect(DB_PATH)
    con.executescript("""
        CREATE TABLE deputes (id TEXT PRIMARY KEY, nom TEXT, groupe TEXT, circonscription TEXT);
        CREATE TABLE scrutins (id TEXT PRIMARY KEY, date TEXT, titre TEXT, objet TEXT,
                               resultat TEXT, url TEXT, numero INTEGER,
                               seance_ref TEXT, amendement_id TEXT);
        -- only the amendments voted in a scrutin, and the parents of voted sub-amendments
        CREATE TABLE amendements (id TEXT PRIMARY KEY, numero TEXT, auteur TEXT, groupe TEXT,
                                  expose TEXT, dispositif TEXT, sort TEXT, parent_id TEXT);
        -- groupe: political group of the député at the time of the vote
        CREATE TABLE votes (scrutin_id TEXT, depute_id TEXT, position TEXT, groupe TEXT);
        CREATE TABLE groupes (id TEXT PRIMARY KEY, nom TEXT, sigle TEXT);
        -- periods in office during the legislature; fin is NULL while the mandate runs
        CREATE TABLE mandats (depute_id TEXT, debut TEXT, fin TEXT);
    """)
    con.executemany("INSERT INTO deputes VALUES (?,?,?,?)", deputes)
    con.executemany("INSERT INTO mandats VALUES (?,?,?)", periodes)
    con.executemany("INSERT INTO scrutins VALUES (?,?,?,?,?,?,?,?,?)",
                    [s + (links.get(s[0]),) for s in scrutins])
    con.executemany("INSERT INTO amendements VALUES (:id,:numero,:auteur,:groupe,:expose,"
                    ":dispositif,:sort,:parent_id)", amendements)
    con.executemany("INSERT INTO votes VALUES (?,?,?,?)", votes)
    con.executemany("INSERT INTO groupes VALUES (?,?,?)", groupes)
    # A few scrutins (14) carry an invalid group reference ("PO0") in the source files.
    # For those votes, fall back on the député's current (or last) group.
    con.execute("""
        UPDATE votes SET groupe = (
            SELECT g.id FROM deputes d JOIN groupes g ON g.nom = d.groupe
            WHERE d.id = votes.depute_id LIMIT 1)
        WHERE groupe NOT IN (SELECT id FROM groupes)
    """)
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
