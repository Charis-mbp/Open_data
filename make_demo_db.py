"""Write data/boussole_demo.db: a small copy of data/boussole.db that is enough to run the demo.

It holds:
- every scrutin found in any theme's shortlist.json, and the vote rows for those scrutins
- the deputes, groupes and mandats tables in full (mandats: scoring needs the mandate periods)
- the amendements those scrutins are about, and their parent amendements (matching reads the exposé)

The app uses boussole.db when it exists, boussole_demo.db otherwise. Run: python make_demo_db.py
"""
import glob
import json
import os
import sqlite3

ROOT = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.join(ROOT, "data", "boussole.db")
DEMO = os.path.join(ROOT, "data", "boussole_demo.db")


def shortlisted_ids():
    ids = set()
    for path in sorted(glob.glob(os.path.join(ROOT, "themes", "*", "shortlist.json"))):
        with open(path, encoding="utf-8") as f:
            ids.update(s["id"] for s in json.load(f)["scrutins"])
    return ids


def main():
    if not os.path.exists(SOURCE):
        raise SystemExit("data/boussole.db est absent : lancez d'abord python load_data.py")
    ids = shortlisted_ids()
    if os.path.exists(DEMO):
        os.remove(DEMO)
    con = sqlite3.connect(DEMO)
    con.execute("ATTACH DATABASE ? AS src", (SOURCE,))
    # same schema as the full database
    for (sql,) in con.execute("SELECT sql FROM src.sqlite_master WHERE type IN ('table', 'index') "
                              "AND sql IS NOT NULL ORDER BY type DESC").fetchall():
        con.execute(sql)
    con.execute("CREATE TEMP TABLE keep (id TEXT PRIMARY KEY)")
    con.executemany("INSERT INTO keep VALUES (?)", [(i,) for i in ids])
    con.execute("INSERT INTO scrutins SELECT * FROM src.scrutins WHERE id IN (SELECT id FROM keep)")
    con.execute("INSERT INTO votes SELECT * FROM src.votes WHERE scrutin_id IN (SELECT id FROM keep)")
    for table in ("deputes", "groupes", "mandats"):
        con.execute(f"INSERT INTO {table} SELECT * FROM src.{table}")
    con.execute("""INSERT INTO amendements SELECT * FROM src.amendements WHERE id IN
                   (SELECT amendement_id FROM scrutins WHERE amendement_id IS NOT NULL)""")
    con.execute("""INSERT OR IGNORE INTO amendements SELECT * FROM src.amendements WHERE id IN
                   (SELECT parent_id FROM amendements WHERE parent_id IS NOT NULL)""")
    con.commit()
    con.execute("DETACH DATABASE src")
    con.execute("VACUUM")
    counts = {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
              for t in ("scrutins", "votes", "deputes", "groupes", "mandats", "amendements")}
    con.close()
    print(", ".join(f"{n} {t}" for t, n in counts.items()))
    print(f"{DEMO} : {os.path.getsize(DEMO) / 1e6:.1f} Mo")


if __name__ == "__main__":
    main()
