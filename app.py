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


AMBIGU_LIBELLE = "Ambigu : « cheval de Troie »"
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


COULEURS_LABEL = {scoring.ALLIE: "●", scoring.A_CONVAINCRE: "●", scoring.OPPOSANT: "●", scoring.INSUFFISANT: "○"}
CLASSE_LABEL = {scoring.ALLIE: "allie", scoring.A_CONVAINCRE: "convaincre", scoring.OPPOSANT: "opposant",
                scoring.INSUFFISANT: "insuffisant"}
COULEURS_HEX = {scoring.ALLIE: styles.P["allie"], scoring.A_CONVAINCRE: styles.P["convaincre"],
                scoring.OPPOSANT: styles.P["opposant"], scoring.INSUFFISANT: "#4A5762"}


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
    points = alt.Chart(d).mark_circle(opacity=.85, stroke=styles.P["encre"], strokeWidth=.5).encode(
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
        strokeDash=[4, 4], color=styles.P["gris"], opacity=.6).encode(x="x:Q")
    graphe = (seuils + points).properties(height=max(260, 34 * len(ordre))).configure(
        background="transparent").configure_view(stroke=None).configure_axis(
        gridColor=styles.P["filet"], domainColor=styles.P["filet"], labelColor=styles.P["craie"],
        titleColor=styles.P["gris"], labelFont="IBM Plex Sans", titleFont="IBM Plex Mono").configure_legend(
        labelColor=styles.P["craie"], titleColor=styles.P["gris"], labelFont="IBM Plex Sans", titleFont="IBM Plex Mono")
    st.altair_chart(graphe, width="stretch")


LIBELLES_CATEGORIE = {"aligné": "aligné", "opposé": "opposé", "abstention": "abstention", "absent": "absent"}


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
    texte = f"Scores calculés sur <b>{acceptes} scrutins validés</b>."
    if non_valides:
        texte += f" {non_valides} propositions du modèle sont <b>non validées</b> et ne comptent pas."
    st.markdown(f'<p class="ligne-info">{texte}</p>', unsafe_allow_html=True)
    return acceptes


def votes_derriere(detail, depute_id):
    """The votes behind one député's score, each linked to the scrutin page."""
    ordre = {c: i for i, c in enumerate(LIBELLES_CATEGORIE)}  # aligné, opposé, abstention, absent
    rows = detail[detail["depute_id"] == depute_id]
    rows = rows.assign(_o=rows["categorie"].map(ordre)).sort_values(["_o", "date"])
    rows = rows.assign(categorie=rows["categorie"].map(LIBELLES_CATEGORIE),
                       ambigu=rows["ambigu"].map(lambda a: "cheval de Troie" if a else ""))
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
    path = matching.theme_path(theme, "validated.json")
    s = scoring.seuils(theme)
    st.markdown(styles.tete_page(
        f"Classement · {label}", "Tous les députés, du plus proche au plus éloigné",
        f"Score = part des votes alignés sur le vote voulu, parmi les votes pour et contre. Allié : "
        f"{s['seuil_allie']} ou plus. Opposant : {s['seuil_opposant']} ou moins. Moins de {s['min_votes']} votes "
        "pour ou contre : données insuffisantes. Abstentions et absences sont affichées mais ne comptent pas."),
        unsafe_allow_html=True)
    if not bandeau_validation(theme) or not os.path.exists(path):
        st.info("Aucun scrutin validé pour ce thème : validez des correspondances sur la page "
                "« Validation des scrutins » pour obtenir des scores.")
        return
    df, _ = scores_theme(theme, (os.path.getmtime(path), os.path.getmtime(scoring.__file__)))

    q = st.text_input("Rechercher un député", placeholder="Nom du député", label_visibility="collapsed")
    f1, f2, f3 = st.columns([2, 2, 1], vertical_alignment="bottom")
    groupes = f1.multiselect("Groupe", sorted(g for g in df["groupe"].unique() if g))
    labels = f2.multiselect("Étiquette", scoring.LABELS)
    anciens = f3.checkbox("Inclure les anciens députés")
    vue = df if anciens else df[df["en_mandat"]]
    if groupes:
        vue = vue[vue["groupe"].isin(groupes)]
    if labels:
        vue = vue[vue["label"].isin(labels)]
    if q.strip():
        vue = vue[vue["nom"].map(normalise).str.contains(normalise(q.strip()), regex=False)]
    visuel_labels(vue)

    st.markdown(styles.coupe("Le nuage", "un point par député · taille selon les votes comptés")
                + styles.titre_bande("Les scores, groupe par groupe",
                                     "Les pointillés marquent les seuils d'opposant et d'allié. Cliquez une "
                                     "étiquette de la légende pour l'isoler."), unsafe_allow_html=True)
    nuage_scores(vue, s)

    st.markdown(styles.coupe("Le tableau", f"{len(vue)} députés · cliquez une ligne pour ouvrir la fiche"),
                unsafe_allow_html=True)
    if vue.empty:
        st.info("Aucun député ne correspond aux filtres.")
        return
    st.session_state["_classement_ids"] = list(vue["depute_id"])
    st.dataframe(
        vue[["nom", "groupe", "circonscription", "score", "label", "note", "alignes", "opposes",
             "abstentions", "absences"]],
        hide_index=True, width="stretch", key="tableau_classement", on_select=ouvrir_depuis_tableau,
        selection_mode="single-row",
        column_config={
            "nom": "Député", "groupe": "Groupe", "circonscription": "Circonscription",
            "score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100, format="%d"),
            "label": "Étiquette", "note": "Note", "alignes": "Alignés", "opposes": "Opposés",
            "abstentions": "Abstentions", "absences": "Absences",
        },
    )


def ouvrir_depuis_tableau():
    """Callback of the Classement table: the clicked row opens that député's fiche."""
    lignes = st.session_state["tableau_classement"].selection.rows
    ids = st.session_state.get("_classement_ids", [])
    if lignes and lignes[0] < len(ids):
        ouvrir_fiche(ids[lignes[0]])


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
            lignes.append(("Profession", styles.e(f["profession"])))
        com = f.get("commission")
        if com:
            role = ", ".join(q for q in com["qualites"] if q != "Membre") or "membre"
            lignes.append(("Commission", f"{styles.e(com.get('nom') or com['organe'])} ({styles.e(role.lower())})"))
        if f.get("fonction"):
            lignes.append(("Fonction", styles.e(f["fonction"])))
    if pd.notna(r.get("loyaute")):
        lignes.append(("Loyauté", f"{pct(r['loyaute'])} % de ses votes suivent la position majoritaire du groupe "
                                  f"(médiane du groupe : {pct(r['mediane_groupe'])} %, "
                                  f"{int(r['votes_loyaute'])} votes comptés sur la législature)"))
    else:
        lignes.append(("Loyauté", '<span style="color:var(--gris)">non mesurée</span>'))
    if f and f.get("hatvp"):
        lignes.append(("Intérêts", f'<a href="{styles.e(f["hatvp"])}" target="_blank">déclarations HATVP</a>'))
    st.markdown(styles.encart("Hémicycle", lignes, "Source : Hémicycle (hemicycle.ai), d'après les données "
                              "ouvertes de l'Assemblée nationale (Licence Ouverte). Consulté le 14 novembre 2026."),
                unsafe_allow_html=True)


def page_fiche(theme, label):
    path = matching.theme_path(theme, "validated.json")
    if not os.path.exists(path):
        st.markdown(styles.tete_page("Fiche député", "Fiche député"), unsafe_allow_html=True)
        st.info("Aucun scrutin validé pour ce thème : la fiche ne peut pas encore montrer de score.")
        return
    df, detail = scores_theme(theme, (os.path.getmtime(path), os.path.getmtime(scoring.__file__)))
    df = df.sort_values("nom")
    noms = {r.depute_id: f"{r.nom} ({r.groupe})" + ("" if r.en_mandat else ", ancien député")
            for r in df.itertuples()}
    ids = list(noms)
    courant = st.session_state.get("fiche_depute")
    tete, choix_col = st.columns([3, 1.2], vertical_alignment="bottom")
    choix = choix_col.selectbox("Autre député", ids, index=ids.index(courant) if courant in ids else 0,
                                format_func=noms.get)
    st.session_state["fiche_depute"] = choix
    r = df.set_index("depute_id").loc[choix]
    classe = CLASSE_LABEL[r["label"]]
    tete.markdown(
        styles.tete_page(f"Fiche député · {r['groupe'] or 'sans groupe'}", r["nom"])
        + f'<p class="fiche-sous">{styles.e(r["circonscription"])}' + ("" if r["en_mandat"] else " · ne siège plus")
        + f' · <a href="https://www.assemblee-nationale.fr/dyn/deputes/{choix}" target="_blank">page sur le site '
          "de l'Assemblée</a></p>"
        + f'<div class="pastilles"><span class="pastille {classe}">{styles.e(r["label"])}</span>'
        + (f'<span class="pastille neutre">{styles.e(r["note"])}</span>' if r["note"] else "") + "</div>",
        unsafe_allow_html=True)

    st.markdown(styles.coupe(f"Thème · {label}", "scrutins validés tenus pendant son mandat"), unsafe_allow_html=True)
    gauche, droite = st.columns([1.35, 1], gap="large")
    with gauche:
        st.markdown(styles.metriques([
            ("Score sur le thème", "–" if pd.isna(r["score"]) else int(r["score"]), classe),
            ("Moyenne de son groupe", "–" if pd.isna(r["moyenne_groupe"]) else int(r["moyenne_groupe"]), ""),
            ("Votes alignés / opposés", f"{r['alignes']} / {r['opposes']}", ""),
        ]) + f'<p class="fiche-sous" style="margin-top:.8rem">{r["alignes"]} votes alignés et {r["opposes"]} '
             f"opposés font le score ; {r['abstentions']} abstentions et {r['absences']} absences sont affichées, "
             "non comptées.</p>"
           + (f'<div class="alerte"><b>S\'écarte de son groupe.</b> Sur toute la législature, il suit la position '
              f"majoritaire de son groupe dans {pct(r['loyaute'])} % de ses votes, contre {pct(r['mediane_groupe'])} % "
              f"pour le député médian du groupe (source : Hémicycle). Sur ce thème, son score dépasse de "
              f"{int(r['score'] - r['moyenne_groupe'])} points la moyenne du groupe. Classé « à convaincre », quel "
              "que soit le score.</div>" if r["note"] else ""),
           unsafe_allow_html=True)
        bandeau_validation(theme)
    with droite:
        encart_hemicycle(choix, r)

    n = int((detail["depute_id"] == choix).sum()) if not detail.empty else 0
    st.markdown(styles.coupe("Les votes derrière le score", f"{n} scrutins · chaque ligne renvoie au site de "
                             "l'Assemblée"), unsafe_allow_html=True)
    votes_derriere(detail, choix)


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


@st.cache_data
def sigles():
    """{group name: short name} from the database, e.g. "Rassemblement National" -> "RN"."""
    con = sqlite3.connect(DB_PATH)
    out = dict(con.execute("SELECT nom, sigle FROM groupes").fetchall())
    con.close()
    return out


# left-to-right seating of the groups in the hemicycle; unknown groups go between the last listed and NI
ORDRE_GROUPES = ["LFI-NFP", "GDR", "ECOS", "SOC", "LIOT", "DEM", "EPR", "HOR", "DR", "UDR", "RN", "NI"]


def trier_liste(actuels, lab):
    liste = actuels[actuels["label"] == lab]
    if lab == scoring.A_CONVAINCRE:  # most favourable compared with their own group first: the best leads
        return liste.assign(_e=(liste["score"] - liste["moyenne_groupe"]).fillna(0)).sort_values(
            ["_e", "exprimes"], ascending=False)
    return liste.sort_values(["score", "exprimes"], ascending=[lab != scoring.ALLIE, False])


def page_accueil(theme, label):
    texte_demo = matching.read_position_text(theme) or ""
    data = matching.load_matching(theme)
    path = matching.theme_path(theme, "validated.json")
    df = None
    if data is not None and os.path.exists(path):
        df, _ = scores_theme(theme, (os.path.getmtime(path), os.path.getmtime(scoring.__file__)))
    actuels = df[df["en_mandat"]].copy() if df is not None else None
    acceptes = scoring.scrutins_acceptes(theme)

    # ---- hero: the question, the document, the hemicycle
    gauche, droite = st.columns([1, 1.08], gap="large")
    with gauche:
        st.markdown(
            f'<div class="hero-g"><span class="etiq">Assemblée nationale · 17e législature · Thème {styles.e(label.lower())}</span>'
            '<h1>Qui, dans l\'hémicycle, vote comme vous&nbsp;?</h1>'
            '<p class="chapo">Collez la note de position d\'une organisation. Cleon classe les <b>577 députés</b> en '
            'alliés, opposants et à convaincre, et montre pour chaque score les votes qui le justifient.</p>'
            '<ol class="etapes3"><li><b>1 · Propose</b>Un modèle relie la note aux scrutins.</li>'
            '<li><b>2 · Valide</b>Une personne accepte ou rejette chaque lien.</li>'
            '<li><b>3 · Calcule</b>Le score est la part des votes alignés.</li></ol></div>',
            unsafe_allow_html=True)
        with st.form("document"):
            premiere = texte_demo.strip().splitlines()[0] if texte_demo.strip() else "Document de position"
            infos = (f"{len(data['positions'])} positions extraites · {len(acceptes)} scrutins validés"
                     if data is not None else "pas encore analysé")
            st.markdown(f'<div class="doc-tete"><b>{styles.e(premiere)}</b><span class="etiq">{infos}</span></div>',
                        unsafe_allow_html=True)
            texte = st.text_area("Document de position", value=texte_demo, height=170, label_visibility="collapsed")
            envoye = st.form_submit_button("Analyser le document", type="primary")
        if envoye and texte.strip() != texte_demo.strip():
            st.info("Ce document n'a pas encore été analysé. L'analyse d'un nouveau document passe par le modèle "
                    "de langage puis par une validation humaine : elle se lance depuis la page « Validation des "
                    "scrutins ». Les résultats affichés sont ceux du document de démonstration.")
    with droite:
        if actuels is None:
            st.info("Le document de ce thème n'a pas encore été analysé ou validé : rendez-vous sur la page "
                    "« Validation des scrutins ».")
        else:
            sig = sigles()
            actuels["sigle"] = actuels["groupe"].map(sig).fillna("NI")
            rang = {g: i for i, g in enumerate(ORDRE_GROUPES)}
            actuels["_r"] = actuels["sigle"].map(lambda g: rang.get(g, len(ORDRE_GROUPES) - 1.5))
            assis = actuels.assign(_s=actuels["score"].fillna(-1)).sort_values(["_r", "_s"], ascending=[True, False])
            sieges = [(r.sigle, CLASSE_LABEL[r.label] if r.label != scoring.INSUFFISANT else "vide",
                       f"{r.nom} ({r.sigle}) · " + (f"{int(r.score)}" if pd.notna(r.score) else "pas de score"))
                      for r in assis.itertuples()]
            n = {lab: int((actuels["label"] == lab).sum()) for lab in scoring.LABELS}
            ordre = [(scoring.ALLIE, "alliés", "allie"), (scoring.A_CONVAINCRE, "à convaincre", "convaincre"),
                     (scoring.OPPOSANT, "opposants", "opposant"), (scoring.INSUFFISANT, "trop peu de votes", "vide")]
            barre = "".join(f'<i class="{c}" style="flex:{n[l]}"></i>' for l, _, c in ordre)
            chiffres = "".join(f'<div class="{c}"><b>{n[l]}</b><span>{t}</span></div>' for l, t, c in ordre)
            st.markdown(
                '<div class="hemi-bloc"><div class="titre"><span class="etiq">L\'hémicycle vu depuis la note</span>'
                '<span class="etiq">survolez un siège</span></div>'
                + styles.hemicycle_svg(sieges)
                + f'<div class="legende">{len(actuels)} députés en exercice. Chaque point est un siège ; les groupes sont '
                  'placés de gauche à droite, chaque député coloré selon ses votes sur le thème.</div>'
                + f'<div class="repart">{barre}</div><div class="decompte">{chiffres}</div></div>',
                unsafe_allow_html=True)

    if data is None or actuels is None:
        return

    # ---- the positions
    par_position = acceptes["position_id"].value_counts().to_dict() if not acceptes.empty else {}
    cartes = "".join(
        f'<div class="position"><div class="tete"><span class="id">{styles.e(p["id"])}</span>'
        f'<span class="etiq">{par_position.get(p["id"], 0)} scrutins validés</span></div>'
        f'<h3>{styles.e(p["position"])}</h3>'
        + (f'<blockquote>« {styles.e(p["passage"][:228] + ("…" if len(p["passage"]) > 228 else ""))} »</blockquote>'
           if p.get("passage") else "") + '</div>'
        for p in data["positions"])
    st.markdown(styles.coupe("Les positions", f"extraites de la note · {len(data['positions'])} positions")
                + styles.titre_bande("Ce que demande la note",
                                     "Le modèle a tiré ces positions du document, chacune appuyée sur un passage "
                                     "du texte. Ce sont elles que Cleon cherche dans les votes.")
                + f'<div class="positions">{cartes}</div>', unsafe_allow_html=True)

    # ---- group averages, to scale
    avec = actuels[actuels["score"].notna() & (actuels["sigle"] != "NI")]
    moy = avec.groupby("sigle")["score"].mean().round().astype(int).sort_values(ascending=False)
    taille = actuels.groupby("sigle").size()
    noms = actuels.drop_duplicates("sigle").set_index("sigle")["groupe"]
    s_ = scoring.seuils(theme)
    classe = lambda v: "allie" if v >= s_["seuil_allie"] else "opposant" if v <= s_["seuil_opposant"] else "convaincre"
    lignes = "".join(
        f'<div class="ligne-g {classe(v)}"><div class="nom-g"><span class="data">{styles.e(g)}</span>'
        f'<span>{styles.e(noms.get(g, g))} · {int(taille.get(g, 0))}</span></div>'
        f'<div class="piste"><i style="width:{v}%;animation-delay:{i * 50}ms"></i></div><span class="val">{v}</span></div>'
        for i, (g, v) in enumerate(moy.items()))
    axe = ('<div class="axe"><div></div><div><span style="left:0;transform:none">0</span>'
           f'<span style="left:{s_["seuil_opposant"]}%">{s_["seuil_opposant"]}</span>'
           f'<span style="left:{s_["seuil_allie"]}%">{s_["seuil_allie"]}</span>'
           '<span style="left:100%;transform:translateX(-100%)">100</span></div><div></div></div>')
    st.markdown(styles.coupe("Les groupes", "score moyen des membres qui ont un score")
                + styles.titre_bande("L'hémicycle, groupe par groupe",
                                     f"Traits verticaux : {s_['seuil_opposant']} et {s_['seuil_allie']}, "
                                     "les seuils d'opposant et d'allié.")
                + f'<div class="groupes">{lignes}{axe}</div>', unsafe_allow_html=True)

    # ---- the three lists
    st.markdown(styles.coupe("Les trois listes", "députés en exercice · cliquez un nom pour sa fiche")
                + styles.titre_bande("Alliés, à convaincre, opposants",
                                     f"Les dix premiers de chaque liste. {n[scoring.INSUFFISANT]} députés ont moins de "
                                     f"{s_['min_votes']} votes pour ou contre sur ces scrutins : Cleon ne leur "
                                     "invente pas de score."), unsafe_allow_html=True)
    colonnes = st.columns(3, gap="large")
    for col, lab in zip(colonnes, [scoring.ALLIE, scoring.A_CONVAINCRE, scoring.OPPOSANT]):
        liste = trier_liste(actuels, lab)
        titre = "À convaincre" if lab == scoring.A_CONVAINCRE else f"{lab.capitalize()}s"
        col.markdown(f'<div class="tete-liste {CLASSE_LABEL[lab]}"><b>{titre}</b><span>{len(liste)}</span></div>',
                     unsafe_allow_html=True)
        boite = col.container(key=f"liste-{CLASSE_LABEL[lab]}")
        for r in liste.head(10).itertuples():
            note = " · s'écarte" if r.note else ""
            boite.button(f"{r.nom} — {r.sigle} · {int(r.score)}{note}", key=f"acc-{r.depute_id}",
                         on_click=ouvrir_fiche, args=(r.depute_id,), width="stretch")

    # ---- entry points
    portes = actuels[actuels["note"] != ""].sort_values("exprimes", ascending=False)
    if not portes.empty:
        st.markdown(styles.coupe("Les portes d'entrée", f"{len(portes)} députés s'écartent de leur groupe")
                    + styles.titre_bande("Plus proches de vous que leur groupe",
                                         f"Score au moins {s_['ecart_groupe']} points au-dessus de la moyenne du "
                                         f"groupe, et loyauté au groupe au moins {s_['ecart_loyaute']} points sous la "
                                         "médiane (mesure Hémicycle, toute la législature)."),
                    unsafe_allow_html=True)
        for col, r in zip(st.columns(2, gap="large"), portes.head(2).itertuples()):
            f = hemicycle.fiche(r.depute_id)
            com = f"{f['commission']['nom']}" if f and f.get("commission") and f["commission"].get("nom") else ""
            with col.container(border=True):
                st.markdown(
                    '<div class="porte"><div class="pastilles"><span class="pastille convaincre">à convaincre</span>'
                    '<span class="pastille neutre">s\'écarte de son groupe</span></div>'
                    f'<h3>{styles.e(r.nom)}</h3><span class="etiq">{styles.e(r.groupe)} · {styles.e(r.circonscription)}</span>'
                    + (f'<span style="color:var(--gris);font-size:.88rem">{styles.e(com)}</span>' if com else "")
                    + f'<div class="chiffres"><div><b>{int(r.score)}</b><span>son score (groupe {int(r.moyenne_groupe)})</span></div>'
                      f'<div><b>{int(r.alignes)} / {int(r.opposes)}</b><span>votes alignés / opposés</span></div>'
                      f'<div><b>{pct(r.loyaute)} %</b><span>loyauté (médiane {pct(r.mediane_groupe)} %)</span></div></div></div>',
                    unsafe_allow_html=True)
                st.button("Ouvrir la fiche", key=f"porte-{r.depute_id}", on_click=ouvrir_fiche, args=(r.depute_id,))

    # ---- method
    st.markdown(styles.coupe("La méthode", "le modèle propose, l'humain décide")
                + styles.titre_bande("Comment Cleon arrive à un score")
                + '<div class="etapes4">'
                  '<div><b>1</b><h3>Les positions</h3><p>Un modèle de langage extrait 3 à 6 positions de la note, chacune appuyée sur une citation.</p></div>'
                  '<div><b>2</b><h3>Les scrutins</h3><p>Parmi les 9 895 scrutins de la législature, Cleon garde ceux du thème qui sont vraiment disputés. Le modèle lit l\'exposé de chaque amendement et propose le vote voulu.</p></div>'
                  '<div><b>3</b><h3>La validation</h3><p>Une personne accepte, inverse ou rejette chaque proposition. Seuls les scrutins validés comptent.</p></div>'
                  f'<div><b>4</b><h3>Le score</h3><p>Part des votes pour ou contre dans le sens voulu. {s_["seuil_allie"]} ou plus : allié. {s_["seuil_opposant"]} ou moins : opposant. Abstentions et absences sont montrées, jamais comptées.</p></div>'
                  '</div>', unsafe_allow_html=True)
    with st.expander("Côté technique"):
        st.markdown(COMMENT_TECHNIQUE)


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
    st.markdown(styles.css(), unsafe_allow_html=True)
    st.sidebar.markdown(styles.marque_rail(), unsafe_allow_html=True)
    st.markdown(styles.entete_page(METHODE), unsafe_allow_html=True)

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
