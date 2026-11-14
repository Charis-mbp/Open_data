import json
import os
import sqlite3
import traceback

import altair as alt
import pandas as pd
import streamlit as st

import hemicycle
import matching
import scoring
import styles
from llm import LLMUnavailable
from shortlist import DB_PATH, DEMO_DB_PATH, build_shortlist, load_shortlist, normalise

ROOT = os.path.dirname(os.path.abspath(__file__))
THEMES_DIR = os.path.join(ROOT, "themes")
METHODE = ("Méthode : un modèle de langage propose les scrutins liés à la position, "
           "une personne les valide, et le score est une simple part des votes alignés.")

st.set_page_config(page_title="Cleon", layout="wide")


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
    df["_recherche"] = (df["titre"] + " " + df["objet"]).map(normalise)
    return df


def page_scrutins():
    st.header("Scrutins")
    df = scrutins_avec_decomptes()
    q = st.text_input("Rechercher dans le titre ou l'objet", placeholder="ex. nucléaire, EPR, électricité")
    if q.strip():
        df = df[df["_recherche"].str.contains(normalise(q.strip()), regex=False)]
    st.caption(f"{len(df)} scrutins")
    if DB_PATH == DEMO_DB_PATH:
        st.caption("Version de démonstration : seuls les scrutins retenus pour les thèmes sont chargés. "
                   "Les 9 895 scrutins de la législature se chargent avec load_data.py.")
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


@st.cache_data
def decompte_par_groupe(scrutin_ids):
    """One row per (scrutin, groupe) with the count of each position."""
    con = sqlite3.connect(DB_PATH)
    marks = ",".join("?" * len(scrutin_ids))
    df = pd.read_sql_query(f"""
        SELECT v.scrutin_id, g.sigle, g.nom AS groupe,
               SUM(v.position = 'pour') AS pour,
               SUM(v.position = 'contre') AS contre,
               SUM(v.position = 'abstention') AS abstention,
               SUM(v.position = 'non-votant') AS non_votant
        FROM votes v JOIN groupes g ON g.id = v.groupe
        WHERE v.scrutin_id IN ({marks})
        GROUP BY v.scrutin_id, g.id
        ORDER BY v.scrutin_id, (pour + contre + abstention) DESC
    """, con, params=list(scrutin_ids))
    con.close()
    return df


def resume_groupes(rows):
    """'RN contre · EPR pour · …': majority position of each group that voted."""
    parts = []
    for r in rows.itertuples():
        counts = {"pour": r.pour, "contre": r.contre, "abst.": r.abstention}
        if sum(counts.values()) == 0:
            continue
        best = max(counts, key=counts.get)
        divise = " (divisé)" if sorted(counts.values())[-2] > 0 else ""
        parts.append(f"{r.sigle} {best}{divise}")
    return " · ".join(parts)


def page_shortlist(theme, label):
    st.header(f"Shortlist : {label}")
    data = load_shortlist(theme)
    if st.button("Recalculer la shortlist") or data is None:
        try:
            data = build_shortlist(theme)
            st.cache_data.clear()
        except FileNotFoundError:
            st.warning("Ce thème n'a pas encore de fichier keywords.txt.")
            return
    stats, regles = data["statistiques"], data["regles"]
    st.caption(
        f"{stats['correspondances']} scrutins contiennent un mot-clé ; "
        f"{stats['moins_de_votants']} écartés (moins de {regles['min_votants']} votants), "
        f"{stats['trop_desequilibres']} écartés (plus de {regles['max_meme_cote']:.0%} des voix exprimées du même côté). "
        f"{stats['retenus']} retenus sur {stats['apres_filtres']}"
        + (f", les {regles['max_scrutins']} aux votes les plus partagés." if stats["apres_filtres"] > stats["retenus"] else ".")
    )
    scrutins = pd.DataFrame(data["scrutins"])
    if scrutins.empty:
        st.info("Aucun scrutin ne correspond aux mots-clés de ce thème.")
        return
    groupes = decompte_par_groupe(tuple(scrutins["id"]))

    q = st.text_input("Filtrer", placeholder="ex. amendement, article 5, hydroélectricité")
    if q.strip():
        scrutins = scrutins[(scrutins["titre"] + " " + scrutins["objet"]).map(normalise)
                            .str.contains(normalise(q.strip()), regex=False)]
    scrutins = scrutins.sort_values(["date", "numero"], ascending=False)
    scrutins["groupes"] = scrutins["id"].map(
        lambda sid: resume_groupes(groupes[groupes["scrutin_id"] == sid]))
    scrutins["mots_cles"] = scrutins["mots_cles"].map(", ".join)
    st.dataframe(
        scrutins[["numero", "date", "titre", "pour", "contre", "abstention", "groupes", "mots_cles", "url"]],
        hide_index=True,
        width="stretch",
        column_config={
            "numero": st.column_config.NumberColumn("N°", format="%d"),
            "date": "Date",
            "titre": st.column_config.TextColumn("Titre", width="large"),
            "pour": "Pour", "contre": "Contre", "abstention": "Abstention",
            "groupes": st.column_config.TextColumn("Vote majoritaire par groupe", width="large"),
            "mots_cles": "Mots-clés",
            "url": st.column_config.LinkColumn("Lien", display_text="Voir sur assemblee-nationale.fr"),
        },
    )

    st.subheader("Détail par groupe politique")
    libelles = {r.id: f"n° {r.numero} ({r.date}) – {r.titre[:140]}" for r in scrutins.itertuples()}
    choix = st.selectbox("Scrutin", list(libelles), format_func=libelles.get)
    if choix:
        r = scrutins.set_index("id").loc[choix]
        st.markdown(f"**n° {r['numero']}**, {r['date']} : {r['titre']}  \n"
                    f"Résultat : {r['resultat']}. [Voir le scrutin sur le site de l'Assemblée]({r['url']})")
        detail = groupes[groupes["scrutin_id"] == choix].drop(columns=["scrutin_id"])
        st.dataframe(detail, hide_index=True, width="stretch", column_config={
            "sigle": "Sigle", "groupe": "Groupe", "pour": "Pour", "contre": "Contre",
            "abstention": "Abstention", "non_votant": "Non-votant",
        })


AMBIGU_LIBELLE = "🐴 Ambigu : « cheval de Troie »"
AMBIGU_AIDE = ("Le texte voté et l'intention de son auteur vont dans des sens opposés (par exemple un objectif "
               "climatique défendu dans l'exposé comme une alternative au nucléaire). Le vote compte dans le "
               "score, mais il est signalé partout où il apparaît.")
LIBELLES_STATUT = {"accepte": "✅ accepté", "inverse": "🔁 accepté, vote inversé", "rejete": "❌ rejeté"}


def lancer_analyse(theme):
    barre = st.progress(0.0, text="Extraction des positions…")
    try:
        result = matching.run(theme, progress=lambda d, t: barre.progress(
            d / t, text=f"Analyse des scrutins : lot {d} sur {t}"))
    except LLMUnavailable as e:
        barre.empty()
        st.error(f"Le modèle n'est pas joignable : {e}. Vérifiez le fichier .env et la connexion.")
        return None
    except ValueError as e:
        barre.empty()
        st.error(str(e))
        return None
    barre.empty()
    if result["lots_ignores"]:
        st.warning(f"{len(result['lots_ignores'])} lot(s) de scrutins ignorés après deux réponses "
                   "invalides du modèle (détails dans data/llm.log).")
    return result


def carte_match(theme, m, decision):
    with st.container(border=True):
        st.markdown(f"**[n° {m['numero']}]({m['url']})** ({m['date']}) : {m['titre']}")
        st.markdown(f"Position {m['position_id']} : *{m['position']}*  \n"
                    f"Vote voulu proposé : **{m['vote_souhaite']}** · confiance {m['confiance']:.2f}  \n"
                    f"Raison : {m['raison']}")
        amdt = m.get("amendement")
        if amdt:
            groupe = f" ({amdt['groupe']})" if amdt["groupe"] else ""
            expose = amdt["expose"] or "(pas d'exposé sommaire)"
            st.markdown(f"**Amendement n° {amdt['numero']}**, {amdt['auteur']}{groupe}. Exposé sommaire :")
            st.caption(matching.tronquer(expose, 500))
            parent = amdt.get("parent")
            if len(expose) > 500 or parent:
                with st.expander("Exposé complet" + (" et amendement visé" if parent else "")):
                    st.write(expose)
                    if parent:
                        pg = f" ({parent['groupe']})" if parent["groupe"] else ""
                        st.markdown(f"**Amendement visé : n° {parent['numero']}**, {parent['auteur']}{pg}")
                        st.write(parent["expose"] or "(pas d'exposé sommaire)")
        if decision:
            st.caption(f"Décision :{LIBELLES_STATUT[decision['statut']]}"
                       + (f" (vote retenu : {decision['vote_retenu']})" if decision["vote_retenu"] else ""))
        if decision and decision["statut"] in ("accepte", "inverse"):
            st.checkbox(AMBIGU_LIBELLE, value=bool(decision.get("ambigu")), key=f"amb-{m['numero']}",
                        help=AMBIGU_AIDE, on_change=lambda n=m["numero"]: matching.marquer_ambigu(
                            theme, n, st.session_state[f"amb-{n}"]))
        oppose = matching.OPPOSE[m["vote_souhaite"]]
        c1, c2, c3, _ = st.columns([1, 1.4, 1, 3])
        for col, statut, label in ((c1, "accepte", "Accepter"),
                                   (c2, "inverse", f"Inverser (vouloir « {oppose} »)"),
                                   (c3, "rejete", "Rejeter")):
            col.button(label, key=f"{statut}-{m['numero']}", on_click=matching.save_decision,
                       args=(theme, m, statut), width="stretch",
                       disabled=bool(decision and decision["statut"] == statut))


def page_validation(theme, label):
    st.header(f"Validation des scrutins : {label}")
    data = matching.load_matching(theme)
    if data is None:
        st.info("Le modèle n'a pas encore analysé ce thème. L'analyse lit position.txt, en extrait "
                "les positions, puis examine les scrutins de la shortlist par lots de 20.")
        if st.button("Lancer l'analyse par le modèle", type="primary"):
            data = lancer_analyse(theme)
        if data is None:
            return

    decisions = matching.load_validated(theme)
    with st.expander(f"Positions extraites du document ({len(data['positions'])})"):
        for p in data["positions"]:
            st.markdown(f"**{p['id']}. {p['position']}**  \n> {p['passage']}")
        if st.button("Relancer l'analyse (les réponses déjà obtenues sont reprises du cache)"):
            data = lancer_analyse(theme) or data

    matches = data["matches"]
    acceptes = sum(1 for m in matches if decisions.get(str(m["numero"]), {}).get("statut") in ("accepte", "inverse"))
    rejetes = sum(1 for m in matches if decisions.get(str(m["numero"]), {}).get("statut") == "rejete")
    a_traiter = len(matches) - acceptes - rejetes
    c1, c2, c3 = st.columns(3)
    c1.metric("Acceptés", acceptes)
    c2.metric("Rejetés", rejetes)
    c3.metric("Non validés", a_traiter)
    st.caption(f"{len(matches)} correspondances proposées par le modèle sur "
               f"{len(load_shortlist(theme)['scrutins'])} scrutins de la shortlist. "
               "Seuls les scrutins acceptés comptent dans les scores.")

    f1, f2 = st.columns(2)
    vue = f1.radio("Afficher", ["Non validés", "Acceptés", "Rejetés", "Tous"], horizontal=True)
    pos_ids = ["Toutes"] + [p["id"] for p in data["positions"]]
    pos_libelles = {p["id"]: f"{p['id']}. {p['position']}" for p in data["positions"]}
    filtre_pos = f2.selectbox("Position", pos_ids, format_func=lambda k: pos_libelles.get(k, k))

    def garder(m):
        statut = decisions.get(str(m["numero"]), {}).get("statut")
        if filtre_pos != "Toutes" and m["position_id"] != filtre_pos:
            return False
        return {"Non validés": statut is None, "Acceptés": statut in ("accepte", "inverse"),
                "Rejetés": statut == "rejete", "Tous": True}[vue]

    shown = [m for m in matches if garder(m)]  # already sorted, highest confidence first
    if not shown:
        st.info("Aucune correspondance dans cette vue.")
    for m in shown:
        carte_match(theme, m, decisions.get(str(m["numero"])))


COULEURS_LABEL = {scoring.ALLIE: "🟢", scoring.A_CONVAINCRE: "🟠", scoring.OPPOSANT: "🔴",
                  scoring.INSUFFISANT: "⚪"}
CLASSE_LABEL = {scoring.ALLIE: "allie", scoring.A_CONVAINCRE: "convaincre", scoring.OPPOSANT: "opposant",
                scoring.INSUFFISANT: "insuffisant"}
COULEURS_HEX = {scoring.ALLIE: "#3FC488", scoring.A_CONVAINCRE: "#F2B544", scoring.OPPOSANT: "#EF5F57",
                scoring.INSUFFISANT: "#5C6F6A"}


def visuel_labels(vue):
    """Animated counters and stacked bar of the labels, for a set of députés."""
    items = [(int((vue["label"] == lab).sum()), lab, CLASSE_LABEL[lab]) for lab in scoring.LABELS]
    st.markdown(styles.compteurs(items) + styles.repartition(items), unsafe_allow_html=True)


def nuage_scores(vue, s):
    """One dot per député: score by group, coloured by label."""
    d = vue[vue["score"].notna()][["nom", "groupe", "score", "label", "exprimes"]].copy()
    if d.empty:
        return
    d["groupe"] = d["groupe"].fillna("Sans groupe")
    ordre = d.groupby("groupe")["score"].mean().sort_values(ascending=False).index.tolist()
    labs = [l for l in scoring.LABELS if l != scoring.INSUFFISANT]
    survol = alt.selection_point(fields=["label"], bind="legend")
    points = alt.Chart(d).mark_circle(opacity=.85, stroke="#0B1116", strokeWidth=.5).encode(
        x=alt.X("score:Q", title="Score", scale=alt.Scale(domain=[0, 100])),
        y=alt.Y("groupe:N", title=None, sort=ordre),
        yOffset=alt.YOffset("jitter:Q"),
        size=alt.Size("exprimes:Q", title="Votes comptés", scale=alt.Scale(range=[20, 160]), legend=None),
        color=alt.Color("label:N", title="Étiquette",
                        scale=alt.Scale(domain=labs, range=[COULEURS_HEX[l] for l in labs]),
                        legend=alt.Legend(orient="top")),
        opacity=alt.condition(survol, alt.value(.9), alt.value(.12)),
        tooltip=[alt.Tooltip("nom:N", title="Député"), alt.Tooltip("groupe:N", title="Groupe"),
                 alt.Tooltip("score:Q", title="Score", format=".0f"), alt.Tooltip("label:N", title="Étiquette"),
                 alt.Tooltip("exprimes:Q", title="Votes comptés")],
    ).transform_calculate(jitter="random()").add_params(survol)
    seuils = alt.Chart(pd.DataFrame({"x": [s["seuil_opposant"], s["seuil_allie"]]})).mark_rule(
        strokeDash=[4, 4], color="#8DA19C", opacity=.6).encode(x="x:Q")
    graphe = (seuils + points).properties(height=max(260, 34 * len(ordre))).configure(
        background="transparent").configure_view(stroke=None).configure_axis(
        gridColor="#22323B", domainColor="#22323B", labelColor="#C9D6D2", titleColor="#8DA19C",
        labelFont="Inter", titleFont="Inter").configure_legend(labelColor="#C9D6D2", titleColor="#8DA19C")
    st.altair_chart(graphe, width="stretch")


LIBELLES_CATEGORIE = {"aligné": "✅ aligné", "opposé": "❌ opposé", "abstention": "➖ abstention",
                      "absent": "· absent"}


@st.cache_data
def scores_theme(theme, version):
    """Cached per theme. `version` must change whenever the result can change: it holds the mtimes of
    validated.json and scoring.py (Streamlit ignores parameters starting with "_" in the cache key)."""
    return scoring.scores(theme), scoring.detail_votes(theme)


def bandeau_validation(theme):
    """How many scrutins the scores rest on, and how many proposals are still "non validés"."""
    data = matching.load_matching(theme)
    decisions = matching.load_validated(theme)
    acceptes = sum(1 for d in decisions.values() if d["statut"] in ("accepte", "inverse"))
    non_valides = 0 if data is None else sum(1 for m in data["matches"] if str(m["numero"]) not in decisions)
    texte = f"Scores calculés sur **{acceptes} scrutins validés**."
    if non_valides:
        texte += f" {non_valides} propositions du modèle sont **non validées** et ne comptent pas."
    st.markdown(texte)
    return acceptes


def votes_derriere(detail, depute_id):
    """The votes behind one député's score, each linked to the scrutin page."""
    ordre = {c: i for i, c in enumerate(LIBELLES_CATEGORIE)}  # aligné, opposé, abstention, absent
    rows = detail[detail["depute_id"] == depute_id]
    rows = rows.assign(_o=rows["categorie"].map(ordre)).sort_values(["_o", "date"])
    rows = rows.assign(categorie=rows["categorie"].map(LIBELLES_CATEGORIE),
                       ambigu=rows["ambigu"].map(lambda a: "🐴 cheval de Troie" if a else ""))
    st.dataframe(
        rows[["categorie", "numero", "date", "titre", "ambigu", "position_id", "vote_retenu", "vote", "raison",
              "url"]],
        hide_index=True, width="stretch",
        column_config={
            "categorie": "Compte comme", "numero": st.column_config.NumberColumn("N°", format="%d"),
            "date": "Date", "titre": st.column_config.TextColumn("Scrutin", width=420),
            "position_id": "Position", "vote_retenu": "Vote voulu", "vote": "Son vote",
            "raison": st.column_config.TextColumn("Raison", width=420),
            "ambigu": st.column_config.TextColumn("Signal", help=AMBIGU_AIDE),
            "url": st.column_config.LinkColumn("Lien", display_text="Voir le scrutin"),
        },
    )


def page_classement(theme, label):
    st.header(f"Classement : {label}")
    if not bandeau_validation(theme):
        st.info("Aucun scrutin validé pour ce thème : validez des correspondances sur la page "
                "« Validation des scrutins » pour obtenir des scores.")
        return
    path = matching.theme_path(theme, "validated.json")
    df, detail = scores_theme(theme, (os.path.getmtime(path), os.path.getmtime(scoring.__file__)))
    s = scoring.seuils(theme)
    st.caption(f"Score = part des votes alignés sur le vote voulu, parmi les votes pour et contre. "
               f"Allié : {s['seuil_allie']} ou plus. Opposant : {s['seuil_opposant']} ou moins. "
               f"Moins de {s['min_votes']} votes pour ou contre : données insuffisantes. "
               "Abstentions et absences sont affichées mais ne comptent pas.")

    f1, f2, f3 = st.columns([2, 2, 1])
    groupes = f1.multiselect("Groupe", sorted(g for g in df["groupe"].unique() if g))
    labels = f2.multiselect("Étiquette", scoring.LABELS)
    anciens = f3.checkbox("Inclure les anciens députés")
    q = st.text_input("Rechercher un député", placeholder="nom")
    vue = df if anciens else df[df["en_mandat"]]
    if groupes:
        vue = vue[vue["groupe"].isin(groupes)]
    if labels:
        vue = vue[vue["label"].isin(labels)]
    if q.strip():
        vue = vue[vue["nom"].map(normalise).str.contains(normalise(q.strip()), regex=False)]

    visuel_labels(vue)
    with st.expander("Nuage des scores par groupe", expanded=True):
        st.caption("Un point par député, taille selon le nombre de votes comptés. Les pointillés marquent les "
                   "seuils opposant et allié. Cliquez une étiquette de la légende pour l'isoler.")
        nuage_scores(vue, s)

    table = vue.assign(etiquette=vue["label"].map(lambda l: f"{COULEURS_LABEL[l]} {l}"))
    st.dataframe(
        table[["nom", "groupe", "circonscription", "score", "etiquette", "note", "alignes", "opposes",
               "abstentions", "absences"]],
        hide_index=True, width="stretch",
        column_config={
            "nom": "Député", "groupe": "Groupe", "circonscription": "Circonscription",
            "score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100, format="%d"),
            "etiquette": "Étiquette", "note": "Note", "alignes": "Alignés", "opposes": "Opposés",
            "abstentions": "Abstentions", "absences": "Absences",
        },
    )

    st.subheader("Votes derrière un score")
    if vue.empty:
        st.info("Aucun député ne correspond aux filtres.")
        return
    noms = {r.depute_id: f"{r.nom} ({r.groupe}) : "
            + (f"{int(r.score)}" if pd.notna(r.score) else "pas de score") for r in vue.itertuples()}
    choix = st.selectbox("Député", list(noms), format_func=noms.get)
    r = vue.set_index("depute_id").loc[choix]
    st.markdown(f"{COULEURS_LABEL[r['label']]} **{r['label']}**"
                + (f" ({r['note']})" if r["note"] else "")
                + f" · {r['alignes']} alignés, {r['opposes']} opposés, {r['abstentions']} abstentions, "
                f"{r['absences']} absences")
    st.button("Ouvrir la fiche du député", on_click=ouvrir_fiche, args=(choix,))
    votes_derriere(detail, choix)


def ouvrir_fiche(depute_id):
    st.session_state["fiche_depute"] = depute_id
    st.session_state["page"] = "Fiche député"


def pct(x):
    """0.8945 -> "89,5" (French decimal comma)."""
    return f"{100 * x:.1f}".replace(".", ",")


def encart_hemicycle(depute_id, r):
    """Fiche data and loyalty from Hémicycle, read from the local cache, with the source credited."""
    f = hemicycle.fiche(depute_id)
    lignes = []
    if f:
        if f.get("profession"):
            lignes.append(f"**Profession** : {f['profession']}")
        com = f.get("commission")
        if com:
            role = ", ".join(q for q in com["qualites"] if q != "Membre") or "Membre"
            lignes.append(f"**Commission** : {com.get('nom') or com['organe']} ({role.lower()})")
        if f.get("fonction"):
            lignes.append(f"**Fonction** : {f['fonction']}")
        if f.get("hatvp"):
            lignes.append(f"[Déclarations d'intérêts (HATVP)]({f['hatvp']})")
    if pd.notna(r.get("loyaute")):
        lignes.append(f"**Loyauté envers son groupe** : {pct(r['loyaute'])} % de ses votes suivent la "
                      f"position majoritaire du groupe (médiane du groupe : {pct(r['mediane_groupe'])} %, "
                      f"{int(r['votes_loyaute'])} votes comptés sur la législature)")
    if not lignes:
        return
    with st.container(border=True):
        st.markdown("  \n".join(lignes))
        st.caption("Source : Hémicycle (hemicycle.ai), d'après les données ouvertes de l'Assemblée nationale "
                   "(Licence Ouverte). Données consultées le 14 novembre 2026.")


def page_fiche(theme, label):
    st.header("Fiche député")
    path = matching.theme_path(theme, "validated.json")
    if not os.path.exists(path):
        st.info("Aucun scrutin validé pour ce thème : la fiche ne peut pas encore montrer de score.")
        return
    df, detail = scores_theme(theme, (os.path.getmtime(path), os.path.getmtime(scoring.__file__)))
    df = df.sort_values("nom")
    noms = {r.depute_id: f"{r.nom} ({r.groupe})" + ("" if r.en_mandat else ", ancien député")
            for r in df.itertuples()}
    ids = list(noms)
    courant = st.session_state.get("fiche_depute")
    choix = st.selectbox("Député", ids, index=ids.index(courant) if courant in ids else 0,
                         format_func=noms.get)
    st.session_state["fiche_depute"] = choix
    r = df.set_index("depute_id").loc[choix]

    st.subheader(r["nom"])
    classe = CLASSE_LABEL[r["label"]]
    st.markdown(f'<span class="pastille {classe}">{r["label"]}</span>'
                + (f' <span class="pastille insuffisant">{r["note"]}</span>' if r["note"] else ""),
                unsafe_allow_html=True)
    st.markdown(f"{r['groupe'] or 'Sans groupe'} · {r['circonscription']}"
                + ("" if r["en_mandat"] else " · ne siège plus")
                + f"  \n[Page du député sur le site de l'Assemblée nationale]"
                f"(https://www.assemblee-nationale.fr/dyn/deputes/{choix})")
    encart_hemicycle(choix, r)

    st.markdown(f"#### Thème : {label}")
    c0, c1, c2, c3 = st.columns([1.1, 1, 1, 1], vertical_alignment="center")
    c0.markdown(styles.jauge(None if pd.isna(r["score"]) else r["score"], classe), unsafe_allow_html=True)
    c1.metric("Score", "–" if pd.isna(r["score"]) else f"{int(r['score'])} / 100")
    c2.metric("Étiquette", f"{COULEURS_LABEL[r['label']]} {r['label']}")
    c3.metric("Moyenne de son groupe",
              "–" if pd.isna(r["moyenne_groupe"]) else f"{int(r['moyenne_groupe'])} / 100")
    if r["note"]:
        st.warning(f"**{r['note'].capitalize()}** : sur l'ensemble de la législature, il suit la position "
                   f"majoritaire de son groupe dans {pct(r['loyaute'])} % de ses votes, contre "
                   f"{pct(r['mediane_groupe'])} % pour le député médian du groupe (source : Hémicycle). "
                   f"Sur ce thème, son score ({int(r['score'])}) dépasse de {int(r['score'] - r['moyenne_groupe'])} points "
                   f"la moyenne de son groupe ({int(r['moyenne_groupe'])}). Classé « à convaincre », quel que soit le score.")
    st.markdown(f"Sur les scrutins validés de ce thème tenus pendant son mandat : **{r['alignes']}** votes "
                f"alignés et **{r['opposes']}** opposés (ce sont eux qui font le score), "
                f"{r['abstentions']} abstentions et {r['absences']} absences (affichées, non comptées).")
    bandeau_validation(theme)

    st.markdown("#### Les votes derrière le score")
    votes_derriere(detail, choix)


PITCH = ("**Collez le document de position d'une organisation : Cleon classe les 577 députés en "
         "alliés, opposants et à convaincre, et montre pour chaque score les votes qui le justifient.**")

COMMENT_UTILISATEUR = """
1. **Le document de position.** L'organisation colle sa note. Un modèle de langage en extrait 3 à 6 positions,
   chacune appuyée sur une citation du texte.
2. **Les scrutins.** Parmi les 9 895 scrutins publics de la législature, Cleon garde ceux du thème
   (mots-clés, assez de votants, vote assez disputé), puis le modèle propose ceux qui touchent une position
   et le vote que l'organisation aurait voulu, pour ou contre. Pour un amendement, il lit son exposé sommaire.
3. **La validation.** Une personne accepte, inverse ou rejette chaque proposition. Seuls les scrutins validés
   comptent : le modèle propose, l'humain décide.
4. **Le score.** Pour chaque député : part de ses votes pour ou contre qui vont dans le sens voulu.
   70 ou plus : allié. 30 ou moins : opposant. Entre les deux : à convaincre. Un député qui suit nettement
   moins souvent son groupe que ses collègues (loyauté mesurée par Hémicycle sur toute la législature, 5 points
   sous la médiane du groupe) et qui, sur ce thème, a un score d'au moins 10 points au-dessus de la moyenne de son
   groupe, est aussi « à convaincre » :
   il s'écarte de son groupe, c'est une porte d'entrée.
   Moins de 5 votes pour ou contre : données insuffisantes. Abstentions et absences sont montrées, jamais comptées.
5. **La preuve.** Chaque score renvoie à la liste de ses votes, et chaque vote à sa page sur le site de
   l'Assemblée nationale.
"""

COMMENT_TECHNIQUE = """
- **Données** : open data de l'Assemblée nationale, 17e législature. 9 895 scrutins, 1,46 million de votes
  nominatifs, 655 députés avec leurs périodes de mandat, 148 034 amendements. Base SQLite, recalculée par
  `load_data.py`, avec contrôle des décomptes contre les totaux officiels.
- **Shortlist** : mots-clés du thème (mot entier, sans accents), puis au moins 50 votants et pas plus de 90 %
  des voix d'un côté. On garde au plus 150 scrutins, les plus disputés.
- **Modèle de langage** : un seul point d'entrée (`llm.py`). Il fait deux choses seulement : extraire les
  positions, proposer les correspondances par lots de 20 (titre, auteur, groupe, exposé sommaire de
  l'amendement et de l'amendement visé). Réponses en JSON, validées, mises en cache sur disque : la démo
  tourne sans connexion. Le modèle ne produit jamais de score ni de classement.
- **Score** : code simple (`scoring.py`, pandas), seuils en constantes.
- **Thèmes** : un thème = un dossier (mots-clés, document, validations). Aucun nom de thème dans le code.
- **Interface** : Streamlit, en français.
"""


def page_accueil(theme, label):
    st.markdown(PITCH)
    texte_demo = matching.read_position_text(theme) or ""
    data = matching.load_matching(theme)

    st.subheader(f"Thème : {label}")
    with st.form("document"):
        texte = st.text_area("Document de position", value=texte_demo, height=220)
        envoye = st.form_submit_button("Analyser le document", type="primary")
    if envoye and texte.strip() != texte_demo.strip():
        st.info("Ce document n'a pas encore été analysé. L'analyse d'un nouveau document passe par le modèle "
                "de langage puis par une validation humaine : elle se lance depuis la page « Validation des "
                "scrutins ». Les résultats ci-dessous sont ceux du document de démonstration.")

    if data is None:
        st.info("Le document de ce thème n'a pas encore été analysé : rendez-vous sur la page "
                "« Validation des scrutins ».")
        return
    with st.expander(f"Positions extraites du document ({len(data['positions'])})", expanded=True):
        for p in data["positions"]:
            st.markdown(f"**{p['id']}.** {p['position']}")

    path = matching.theme_path(theme, "validated.json")
    if not os.path.exists(path):
        st.info("Aucune correspondance n'a encore été validée : les listes apparaîtront après la validation.")
        return
    df, _ = scores_theme(theme, (os.path.getmtime(path), os.path.getmtime(scoring.__file__)))
    bandeau_validation(theme)
    actuels = df[df["en_mandat"]]
    visuel_labels(actuels)
    colonnes = st.columns(3)
    for col, lab, asc in zip(colonnes, [scoring.ALLIE, scoring.A_CONVAINCRE, scoring.OPPOSANT],
                             [False, False, True]):
        liste = actuels[actuels["label"] == lab]
        if lab == scoring.A_CONVAINCRE:  # most favourable compared with their own group first: the best leads
            liste = liste.assign(_e=(liste["score"] - liste["moyenne_groupe"]).fillna(0)).sort_values(
                ["_e", "exprimes"], ascending=False)
        else:  # strongest scores first, then the most votes behind them
            liste = liste.sort_values(["score", "exprimes"], ascending=[asc, False])
        titre = "À convaincre" if lab == scoring.A_CONVAINCRE else f"{lab.capitalize()}s"
        col.markdown(styles.entete(CLASSE_LABEL[lab], titre, f"{len(liste)} députés"), unsafe_allow_html=True)
        boite = col.container(key=f"liste-{CLASSE_LABEL[lab]}")
        for r in liste.head(10).itertuples():
            note = " · s'écarte de son groupe" if r.note else ""
            boite.button(f"{r.nom} · {int(r.score)} · {r.groupe}{note}", key=f"acc-{r.depute_id}",
                       on_click=ouvrir_fiche, args=(r.depute_id,), width="stretch")
    st.caption(f"Dix premiers de chaque liste, députés en exercice. "
               f"{(actuels['label'] == scoring.INSUFFISANT).sum()} députés n'ont pas assez de votes sur ces "
               "scrutins pour être classés. La liste complète est sur la page « Classement ».")

    st.markdown("### Comment ça marche")
    t1, t2 = st.tabs(["Pour l'utilisateur", "Côté technique"])
    t1.markdown(COMMENT_UTILISATEUR)
    t2.markdown(COMMENT_TECHNIQUE)


def prevision(theme, cfg):
    """(DataFrame of current députés with vote_predit, source label, message or None). Never raises."""
    oppose = {"pour": "contre", "contre": "pour"}[cfg["vote_voulu"]]
    message = None
    preds = None
    if not hemicycle.configure():
        message = "Prédictions Hémicycle non configurées (adresse de l'API absente du fichier .env)."
    elif not cfg.get("ref_hemicycle"):
        message = "Aucun scrutin Hémicycle n'est associé à ce prochain vote (theme.json, « ref_hemicycle »)."
    else:
        try:
            preds = hemicycle.predictions(theme, cfg["ref_hemicycle"])
        except Exception:
            traceback.print_exc()
            preds = None
        if not preds:
            message = "L'API Hémicycle est injoignable ou n'a rien renvoyé."
    if preds:
        df = scoring.scores(theme)
        df = df[df["en_mandat"]].copy()
        p = pd.DataFrame(preds)
        par_id = dict(zip(p["depute_id"], p["vote"]))
        par_nom = {normalise(n): v for n, v in zip(p["nom"], p["vote"]) if n}
        df["vote_predit"] = [par_id.get(i) or par_nom.get(normalise(n)) for i, n in zip(df["depute_id"], df["nom"])]
        df = df[df["vote_predit"].notna()]
        if not df.empty:
            return df, "Hémicycle", None, oppose
        message = "Les prédictions Hémicycle ne correspondent à aucun député connu."
    return scoring.simulation(theme, cfg["vote_voulu"]), "simulation", message, oppose


def page_prochain_vote(theme, label):
    st.header(f"Prochain vote : {label}")
    path = matching.theme_path(theme, "theme.json")
    cfg = json.load(open(path, encoding="utf-8")).get("prochain_vote") if os.path.exists(path) else None
    if not cfg:
        st.info("Aucun prochain vote n'est renseigné pour ce thème (theme.json, « prochain_vote »).")
        return
    if not os.path.exists(matching.theme_path(theme, "validated.json")):
        st.info("Validez d'abord des scrutins : la page s'appuie sur les scores passés.")
        return
    df, source, message, oppose = prevision(theme, cfg)
    st.markdown(f"**{cfg['titre']}**  \nDate : {cfg.get('date', 'à confirmer')} · vote voulu par "
                f"l'organisation : **{cfg['vote_voulu']}**")
    if source == "simulation":
        st.warning((message + " " if message else "") + "Affichage d'une **simulation** à partir des votes passés : "
                   "un député qui vote rarement sur ces scrutins est compté absent, les autres votent dans le sens "
                   "de leur score (ou de celui de leur groupe).")
    else:
        st.caption("Prédictions par député fournies par Hémicycle.")

    totaux = df["vote_predit"].value_counts()
    cols = st.columns(4)
    for col, v in zip(cols, ["pour", "contre", "abstention", "absent"]):
        col.metric(f"{v.capitalize()} ({'prévu' if source == 'Hémicycle' else 'simulé'})", int(totaux.get(v, 0)))

    df = df.assign(raison=[scoring.raison(r) for _, r in df.iterrows()])
    colonnes = {"nom": "Député", "groupe": "Groupe",
                "score": st.column_config.ProgressColumn("Score passé", min_value=0, max_value=100, format="%d"),
                "vote_predit": "Vote prévu", "raison": st.column_config.TextColumn("Raison", width="large")}

    st.subheader("À rencontrer")
    st.caption(f"Prévus « {oppose} » alors que leur score passé est d'au moins {scoring.SEUIL_A_RENCONTRER} : "
               "ils ont déjà voté avec vous.")
    rencontrer = df[(df["vote_predit"] == oppose) & (df["score"] >= scoring.SEUIL_A_RENCONTRER)]
    rencontrer = rencontrer.sort_values("score", ascending=False)
    if rencontrer.empty:
        st.info("Aucun député dans ce cas.")
    else:
        st.dataframe(rencontrer[list(colonnes)], hide_index=True, width="stretch", column_config=colonnes)

    st.subheader("Alliés à mobiliser")
    st.caption("Alliés dont on prévoit l'abstention ou l'absence : chaque voix compte.")
    mobiliser = df[(df["label"] == scoring.ALLIE) & df["vote_predit"].isin(["abstention", "absent"])]
    mobiliser = mobiliser.sort_values(["score", "exprimes"], ascending=False)
    if mobiliser.empty:
        st.info("Aucun allié dans ce cas.")
    else:
        st.dataframe(mobiliser[list(colonnes)], hide_index=True, width="stretch", column_config=colonnes)

    choix = pd.concat([rencontrer, mobiliser])
    if not choix.empty:
        noms = {r.depute_id: f"{r.nom} ({r.groupe})" for r in choix.itertuples()}
        qui = st.selectbox("Ouvrir la fiche de", list(noms), format_func=noms.get)
        st.button("Ouvrir la fiche du député", key="pv-fiche", on_click=ouvrir_fiche, args=(qui,))


def main():
    st.markdown(styles.css(styles.DEFAUT), unsafe_allow_html=True)
    st.markdown(styles.hero("Cleon", METHODE), unsafe_allow_html=True)

    themes = list_themes()
    if not themes:
        st.error("Aucun thème trouvé dans le dossier themes/.")
        return
    theme = st.sidebar.selectbox("Thème", list(themes), format_func=lambda k: themes[k])
    st.session_state["theme"] = theme
    page = st.sidebar.radio("Pages", ["Accueil", "Prochain vote", "Classement", "Fiche député", "Validation des scrutins",
                                      "Shortlist", "Scrutins"], key="page")

    if not os.path.exists(DB_PATH):
        st.warning("Les données ne sont pas encore chargées. Lancez : python load_data.py")
        return
    try:
        if page == "Accueil":
            page_accueil(theme, themes[theme])
        elif page == "Prochain vote":
            page_prochain_vote(theme, themes[theme])
        elif page == "Classement":
            page_classement(theme, themes[theme])
        elif page == "Fiche député":
            page_fiche(theme, themes[theme])
        elif page == "Validation des scrutins":
            page_validation(theme, themes[theme])
        elif page == "Shortlist":
            page_shortlist(theme, themes[theme])
        elif page == "Scrutins":
            page_scrutins()
    except Exception:
        traceback.print_exc()  # in the terminal only, never on screen
        st.error("Une erreur est survenue lors de l'affichage de cette page.")


main()
