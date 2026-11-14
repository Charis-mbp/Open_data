import json
import os
import sqlite3
import unicodedata

import pandas as pd
import streamlit as st

ROOT = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(ROOT, "data", "boussole.db")
THEMES_DIR = os.path.join(ROOT, "themes")
METHODE = ("Méthode : un modèle de langage propose les scrutins liés à la position, "
           "une personne les valide, et le score est une simple part des votes alignés.")

st.set_page_config(page_title="Boussole parlementaire", layout="wide")


def list_themes():
    themes = {}
    for name in sorted(os.listdir(THEMES_DIR)):
        path = os.path.join(THEMES_DIR, name, "theme.json")
        if os.path.exists(path):
            try:
                themes[name] = json.load(open(path, encoding="utf-8")).get("label", name)
            except (OSError, ValueError):
                themes[name] = name
    return themes


def sans_accents(text):
    text = unicodedata.normalize("NFKD", str(text))
    return "".join(c for c in text if not unicodedata.combining(c)).lower()


@st.cache_data
def scrutins_avec_decomptes():
    con = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("""
        SELECT s.id, s.numero, s.date, s.titre, s.objet, s.resultat, s.url,
               SUM(v.position = 'pour') AS pour,
               SUM(v.position = 'contre') AS contre,
               SUM(v.position = 'abstention') AS abstention
        FROM scrutins s LEFT JOIN votes v ON v.scrutin_id = s.id
        GROUP BY s.id
        ORDER BY s.date DESC, s.numero DESC
    """, con)
    con.close()
    df["_recherche"] = (df["titre"] + " " + df["objet"]).map(sans_accents)
    return df


def page_scrutins():
    st.header("Scrutins")
    df = scrutins_avec_decomptes()
    q = st.text_input("Rechercher dans le titre ou l'objet", placeholder="ex. nucléaire, EPR, électricité")
    if q.strip():
        df = df[df["_recherche"].str.contains(sans_accents(q.strip()), regex=False)]
    st.caption(f"{len(df)} scrutins")
    st.dataframe(
        df[["numero", "date", "titre", "resultat", "pour", "contre", "abstention", "url"]],
        hide_index=True,
        width="stretch",
        column_config={
            "numero": st.column_config.NumberColumn("N°", format="%d"),
            "date": "Date",
            "titre": st.column_config.TextColumn("Titre", width="large"),
            "resultat": "Résultat",
            "pour": "Pour",
            "contre": "Contre",
            "abstention": "Abstention",
            "url": st.column_config.LinkColumn("Lien", display_text="Voir sur assemblee-nationale.fr"),
        },
    )


def main():
    st.title("Boussole parlementaire")
    st.caption(METHODE)

    themes = list_themes()
    if not themes:
        st.error("Aucun thème trouvé dans le dossier themes/.")
        return
    st.session_state["theme"] = st.sidebar.selectbox(
        "Thème", list(themes), format_func=lambda k: themes[k]
    )
    page = st.sidebar.radio("Pages", ["Scrutins"])

    if not os.path.exists(DB_PATH):
        st.warning("Les données ne sont pas encore chargées. Lancez : python load_data.py")
        return
    try:
        if page == "Scrutins":
            page_scrutins()
    except Exception:
        st.error("Une erreur est survenue lors de l'affichage de cette page.")


main()
