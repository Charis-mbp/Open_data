"""Cleon's look: "Encre et cuivre". Dark ink surfaces, hairline rules, copper reserved for the wordmark and the
main action, three label colours. Headings in Bricolage Grotesque, text in IBM Plex Sans, figures in IBM Plex Mono.

Everything visual lives here: the CSS, and small HTML builders the pages call (header, section cuts, hemicycle,
counters). No theme name and no data access in this file.
"""
import html
import math

P = {
    "encre": "#0A0E12", "encre2": "#0E1318", "ardoise": "#121920", "filet": "#1F2831", "filet2": "#2A3540",
    "craie": "#E8ECEE", "gris": "#87939C", "cuivre": "#D9965A", "cuivre_clair": "#E4A66D",
    "allie": "#4BC18C", "convaincre": "#E6B04B", "opposant": "#DE675D", "vide": "#27313B",
}
FONTS = ("https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,700;12..96,800"
         "&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap")


def css():
    return f"""
<style>
@import url('{FONTS}');
:root {{
  --encre: {P['encre']}; --encre2: {P['encre2']}; --ardoise: {P['ardoise']}; --filet: {P['filet']}; --filet2: {P['filet2']};
  --craie: {P['craie']}; --gris: {P['gris']}; --cuivre: {P['cuivre']}; --cuivre-clair: {P['cuivre_clair']};
  --allie: {P['allie']}; --convaincre: {P['convaincre']}; --opposant: {P['opposant']}; --vide: {P['vide']};
  --f-titre: 'Bricolage Grotesque', 'Helvetica Neue', Arial, sans-serif;
  --f-texte: 'IBM Plex Sans', system-ui, sans-serif;
  --f-data: 'IBM Plex Mono', ui-monospace, Menlo, monospace;
  /* names kept for the pages not yet redesigned */
  --fond: var(--encre); --surface: var(--ardoise); --texte: var(--craie); --discret: var(--gris);
  --accent: var(--cuivre); --accent2: var(--cuivre); --ligne: var(--filet); --titre: var(--f-titre);
}}
@keyframes poser {{ from {{ opacity: 0; transform: scale(.4); }} to {{ opacity: 1; transform: none; }} }}
@keyframes pousser {{ from {{ transform: scaleX(0); }} }}

.stApp, [data-testid="stAppViewContainer"] {{ background: var(--encre); color: var(--craie); }}
[data-testid="stHeader"] {{ background: transparent; }}
[data-testid="stMainBlockContainer"] {{ padding-top: 2.2rem; max-width: 1240px; }}
/* text font on text elements only: spans and divs also hold Streamlit's icon font */
.stApp, .stApp p, .stApp li, .stApp label, .stApp input, .stApp textarea, .stApp button {{ font-family: var(--f-texte); }}
.stApp h1, .stApp h2, .stApp h3, .stApp h4 {{ font-family: var(--f-titre); color: var(--craie); letter-spacing: -.025em; text-wrap: balance; }}
.stApp p, .stApp li, .stApp label {{ color: var(--craie); }}
[data-testid="stCaptionContainer"], .stApp small {{ color: var(--gris) !important; }}
.stApp a {{ color: var(--craie); text-decoration: underline; text-decoration-color: var(--filet2); text-underline-offset: 3px; }}
.stApp a:hover {{ text-decoration-color: var(--cuivre); }}

/* sidebar: a quiet rail, the current page marked by a copper rule */
[data-testid="stSidebar"] {{ background: #080B0E; border-right: 1px solid var(--filet); }}
[data-testid="stSidebar"] label, [data-testid="stSidebar"] p {{ color: var(--gris); }}
[data-testid="stSidebar"] [role="radiogroup"] {{ gap: 0; }}
[data-testid="stSidebar"] [role="radiogroup"] > label {{ padding: .5rem .2rem .5rem .8rem; width: 100%; border-left: 2px solid transparent; }}
[data-testid="stSidebar"] [role="radiogroup"] > label > div:first-child {{ display: none; }}
[data-testid="stSidebar"] [role="radiogroup"] > label:hover p {{ color: var(--craie); }}
[data-testid="stSidebar"] [role="radiogroup"] > label:has(input:checked) {{ border-left-color: var(--cuivre); }}
[data-testid="stSidebar"] [role="radiogroup"] > label:has(input:checked) p {{ color: var(--craie); font-weight: 500; }}
.marque-rail {{ font: 800 1.6rem/1 var(--f-titre); letter-spacing: -.03em; color: var(--craie); display: flex; align-items: baseline; gap: 2px; margin: .2rem 0 1.4rem .8rem; }}
.marque-rail i, .marque i {{ width: .3em; height: .3em; border-radius: 50%; background: var(--cuivre); display: inline-block; }}

/* surfaces: flat, one hairline, small radius */
[data-testid="stMetric"] {{ background: transparent; border-top: 1px solid var(--filet2); border-radius: 0; padding: .8rem 0; }}
[data-testid="stMetricValue"] {{ color: var(--craie); font-family: var(--f-data); font-weight: 500; }}
[data-testid="stMetricLabel"] p {{ color: var(--gris); }}
[data-testid="stVerticalBlockBorderWrapper"], .stForm {{ border-color: var(--filet) !important; background: var(--ardoise); border-radius: 6px !important; }}
[data-testid="stExpander"] details {{ background: transparent; border-color: var(--filet); border-radius: 6px; }}
[data-testid="stDataFrame"] {{ border-top: 1px solid var(--filet2); }}
[data-testid="stAlert"] {{ border-radius: 4px; }}

/* buttons: plain by default, copper for the one primary action */
.stButton button, .stFormSubmitButton button {{ background: transparent; color: var(--craie); border: 1px solid var(--filet2); border-radius: 4px; transition: border-color .15s, color .15s; }}
.stButton button:hover, .stFormSubmitButton button:hover {{ border-color: var(--craie); color: var(--craie); }}
.stButton button[kind="primary"], .stFormSubmitButton button[kind="primaryFormSubmit"] {{ background: var(--cuivre); color: #1B1007; border: 0; font-weight: 600; }}
.stButton button[kind="primary"]:hover, .stFormSubmitButton button[kind="primaryFormSubmit"]:hover {{ background: var(--cuivre-clair); color: #1B1007; }}
[data-baseweb="select"] > div, .stTextInput input, .stTextArea textarea {{ background: var(--encre) !important; border-color: var(--filet2) !important; color: var(--craie) !important; }}
.stTextArea textarea {{ font-size: .9rem; line-height: 1.6; color: #B9C3C9 !important; }}
[data-baseweb="tag"] {{ background: var(--filet2) !important; }}
.stTabs [data-baseweb="tab-highlight"] {{ background: var(--cuivre); }}

/* shared bits */
.etiq {{ font: 500 .75rem/1.3 var(--f-data); letter-spacing: .08em; text-transform: uppercase; color: var(--gris); }}
.data {{ font-family: var(--f-data); font-variant-numeric: tabular-nums; }}
.allie {{ --c: var(--allie); }} .convaincre {{ --c: var(--convaincre); }} .opposant {{ --c: var(--opposant); }}
.insuffisant, .vide {{ --c: var(--vide); }}

/* page header: wordmark, method line */
.entete-page {{ display: flex; justify-content: space-between; align-items: baseline; gap: .6rem 2rem; flex-wrap: wrap;
  padding-bottom: .9rem; border-bottom: 1px solid var(--filet); margin-bottom: 1.6rem; }}
.marque {{ font: 800 1.5rem/1 var(--f-titre); letter-spacing: -.03em; display: flex; align-items: baseline; gap: 2px; }}
.entete-page .methode {{ color: var(--gris); font: 400 .78rem/1.4 var(--f-data); max-width: 70ch; }}

/* section cut: a ruled strip with the section's name and one fact */
.coupe {{ display: flex; justify-content: space-between; align-items: center; gap: .5rem 1rem; flex-wrap: wrap;
  border-top: 1px solid var(--filet2); padding: .8rem 0 0; margin: 3rem 0 1.4rem; }}
.coupe .nom {{ display: flex; gap: .6rem; align-items: center; font: 500 .75rem/1 var(--f-data); letter-spacing: .1em; text-transform: uppercase; color: var(--craie); }}
.coupe .nom::before {{ content: ""; width: 18px; height: 2px; background: var(--cuivre); }}
.coupe .fait {{ color: var(--gris); font: 400 .75rem/1.3 var(--f-data); }}
.titre-bande {{ margin: 0 0 .4rem; font: 700 clamp(1.6rem, 3vw, 2.2rem)/1.1 var(--f-titre); letter-spacing: -.025em; max-width: 26ch; }}
.sous {{ margin: 0 0 1.4rem; color: var(--gris); max-width: 64ch; }}

/* hero */
.hero-g {{ display: grid; gap: 1.2rem; }}
.hero-g h1 {{ margin: 0; padding: 0; font: 700 clamp(2.2rem, 4.6vw, 3.5rem)/1.02 var(--f-titre); letter-spacing: -.035em; max-width: 14ch; }}
.chapo {{ margin: 0; color: var(--gris); font-size: 1.1rem; max-width: 46ch; }}
.chapo b {{ color: var(--craie); font-weight: 500; }}
.etapes3 {{ list-style: none; margin: 0 !important; padding: 0 !important; display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); border-top: 1px solid var(--filet); }}
.etapes3 li {{ padding: .75rem .9rem 0 0; display: grid; gap: .25rem; font-size: .86rem; color: var(--gris); margin: 0; }}
.etapes3 li + li {{ padding-left: .9rem; border-left: 1px solid var(--filet); }}
.etapes3 b {{ font: 500 .75rem/1 var(--f-data); color: var(--craie); letter-spacing: .04em; }}
.doc-tete {{ display: flex; justify-content: space-between; gap: .5rem 1rem; flex-wrap: wrap; align-items: baseline; }}
.doc-tete b {{ font-weight: 600; }}

/* hemicycle */
.hemi-bloc {{ display: grid; gap: .9rem; }}
.hemi-bloc .titre {{ display: flex; justify-content: space-between; align-items: baseline; gap: 1rem; flex-wrap: wrap; }}
svg.hemi {{ width: 100%; height: auto; display: block; }}
svg.hemi circle {{ animation: poser .5s cubic-bezier(.2,.8,.2,1) both; transform-box: fill-box; transform-origin: center; }}
svg.hemi circle:hover {{ stroke: var(--craie); stroke-width: 1.5; }}
.hemi-bloc .legende {{ border-top: 1px solid var(--filet); padding-top: .6rem; color: var(--gris); font-size: .85rem; }}
.repart {{ display: flex; height: 8px; border-radius: 2px; overflow: hidden; gap: 2px; }}
.repart i {{ display: block; background: var(--c); }}
.decompte {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: .8rem; }}
.decompte div {{ display: grid; gap: .1rem; }}
.decompte b {{ font: 500 1.5rem/1 var(--f-data); font-variant-numeric: tabular-nums; color: var(--craie); }}
.decompte span {{ font-size: .8rem; color: var(--gris); display: flex; gap: .4rem; align-items: center; }}
.decompte span::before {{ content: ""; width: 8px; height: 8px; border-radius: 50%; background: var(--c); flex: none; }}

/* positions */
.positions {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); border-top: 1px solid var(--filet); }}
.position {{ padding: 1.2rem 1.4rem 1.3rem 0; display: grid; gap: .6rem; align-content: start; border-bottom: 1px solid var(--filet); min-width: 0; }}
.position:nth-child(even) {{ padding-left: 1.4rem; border-left: 1px solid var(--filet); }}
.position .tete {{ display: flex; justify-content: space-between; gap: 1rem; align-items: baseline; }}
.position .id {{ font: 500 .75rem/1 var(--f-data); color: var(--cuivre); letter-spacing: .06em; }}
.position h3 {{ margin: 0; padding: 0; font: 600 1.08rem/1.4 var(--f-texte); letter-spacing: 0; }}
.position blockquote {{ margin: 0; color: var(--gris); font-size: .88rem; border-left: 2px solid var(--filet2); padding-left: .8rem; }}

/* group chart, drawn to scale: thresholds at 30 and 70 */
.groupes {{ display: grid; gap: .5rem; }}
.ligne-g {{ display: grid; grid-template-columns: minmax(0, 16rem) minmax(0, 1fr) 3rem; gap: .9rem; align-items: center; }}
.ligne-g .nom-g {{ display: flex; gap: .5rem; align-items: baseline; min-width: 0; }}
.ligne-g .nom-g span:last-child {{ color: var(--gris); font-size: .8rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.piste {{ position: relative; height: 22px; background: var(--ardoise); border-radius: 2px; }}
.piste i {{ position: absolute; inset: 0 auto 0 0; background: var(--c); border-radius: 2px; transform-origin: left; animation: pousser .8s cubic-bezier(.2,.8,.2,1) both; }}
.piste::before, .piste::after {{ content: ""; position: absolute; top: -4px; bottom: -4px; width: 1px; background: var(--filet2); z-index: 1; }}
.piste::before {{ left: 30%; }} .piste::after {{ left: 70%; }}
.ligne-g .val {{ font: 500 .95rem var(--f-data); text-align: right; }}
.axe {{ display: grid; grid-template-columns: minmax(0, 16rem) minmax(0, 1fr) 3rem; gap: .9rem; }}
.axe div {{ position: relative; height: 1.2em; font: 400 .75rem var(--f-data); color: var(--gris); }}
.axe span {{ position: absolute; transform: translateX(-50%); }}

/* the three lists: column heads, names as ruled rows */
.tete-liste {{ display: flex; align-items: center; gap: .6rem; border-top: 1px solid var(--filet2); padding-top: 1rem; margin-bottom: .3rem; }}
.tete-liste::before {{ content: ""; width: 10px; height: 10px; border-radius: 50%; background: var(--c); }}
.tete-liste b {{ font: 700 1.12rem/1.2 var(--f-titre); flex: 1; }}
.tete-liste span {{ font: 500 .9rem var(--f-data); color: var(--gris); }}
[class*="st-key-liste-"] [data-testid="stVerticalBlock"] {{ gap: 0; }}
[class*="st-key-liste-"] button {{ justify-content: flex-start; text-align: left; border: 0; border-bottom: 1px solid var(--filet); border-radius: 0; padding: .55rem 0; min-height: 0; }}
[class*="st-key-liste-"] button p {{ font-size: .92rem; }}
[class*="st-key-liste-"] button:hover {{ border-bottom-color: var(--c); }}
[class*="st-key-liste-"] button:hover p {{ color: var(--c); }}
.st-key-liste-allie {{ --c: var(--allie); }} .st-key-liste-convaincre {{ --c: var(--convaincre); }} .st-key-liste-opposant {{ --c: var(--opposant); }}

/* entry-point cards */
.porte {{ display: grid; gap: .8rem; }}
.porte h3 {{ margin: 0; padding: 0; font: 700 1.5rem/1.1 var(--f-titre); }}
.chiffres {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: .6rem; border-top: 1px solid var(--filet); padding-top: .7rem; }}
.chiffres div {{ display: grid; gap: .1rem; }}
.chiffres b {{ font: 500 1.35rem/1 var(--f-data); }}
.chiffres span {{ font-size: .78rem; color: var(--gris); }}
.pastilles {{ display: flex; gap: .4rem; flex-wrap: wrap; }}
.pastille {{ display: inline-flex; align-items: center; font: 500 .8rem/1 var(--f-texte); padding: .3rem .55rem; border-radius: 3px;
  background: color-mix(in srgb, var(--c) 16%, transparent); color: var(--c); border: 1px solid color-mix(in srgb, var(--c) 40%, transparent); }}
.pastille.insuffisant, .pastille.neutre {{ --c: var(--gris); }}

/* method, four steps */
.etapes4 {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); border-top: 1px solid var(--filet); }}
.etapes4 div {{ padding: 1.1rem 1.1rem 0 0; display: grid; gap: .35rem; align-content: start; }}
.etapes4 div + div {{ padding-left: 1.1rem; border-left: 1px solid var(--filet); }}
.etapes4 b {{ font: 500 .75rem/1 var(--f-data); color: var(--cuivre); letter-spacing: .06em; }}
.etapes4 h3 {{ margin: 0; padding: 0; font: 700 1.1rem var(--f-titre); }}
.etapes4 p {{ margin: 0; color: var(--gris); font-size: .88rem; }}

/* helpers still used by other pages, flattened */
.compteurs {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); border-top: 1px solid var(--filet2); margin: .4rem 0 .8rem; }}
.compteur {{ padding: .8rem 1rem .6rem 0; }}
.compteur + .compteur {{ padding-left: 1rem; border-left: 1px solid var(--filet); }}
.compteur .val {{ font: 500 1.8rem/1 var(--f-data); color: var(--c); }}
.compteur .lib {{ color: var(--gris); font-size: .82rem; margin-top: .2rem; }}
.compteur.neutre {{ --c: var(--gris); }}
.repartition {{ margin: .4rem 0 1.2rem; }}
.repartition .barre {{ display: flex; height: 8px; border-radius: 2px; overflow: hidden; gap: 2px; }}
.repartition .barre span {{ height: 100%; }}
.repartition .legende {{ display: flex; flex-wrap: wrap; gap: 1rem; margin-top: .5rem; font-size: .82rem; color: var(--gris); }}
.repartition .legende i {{ display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: .35rem; background: var(--c); }}
.jauge {{ --c: var(--cuivre); width: 140px; aspect-ratio: 1; border-radius: 50%; display: grid; place-items: center;
  background: conic-gradient(var(--c) calc(var(--p) * 1%), var(--filet) 0); position: relative; }}
.jauge::before {{ content: ""; position: absolute; inset: 10px; border-radius: 50%; background: var(--encre); }}
.jauge .centre {{ position: relative; text-align: center; }}
.jauge .centre b {{ display: block; font: 500 2.2rem/1 var(--f-data); color: var(--craie); }}
.jauge .centre small {{ color: var(--gris); font-size: .78rem; }}
.entete {{ display: flex; align-items: center; gap: .6rem; border-top: 1px solid var(--filet2); padding-top: .8rem; margin-bottom: .4rem; }}
.entete::before {{ content: ""; width: 10px; height: 10px; border-radius: 50%; background: var(--c); }}
.entete b {{ font: 700 1.1rem var(--f-titre); }}
.entete span {{ color: var(--gris); font-size: .88rem; }}

/* page heads (all pages but Accueil) */
.tete-page {{ display: grid; gap: .5rem; padding-bottom: .4rem; }}
.tete-page h1 {{ margin: 0; padding: 0; font: 700 clamp(2rem, 4.4vw, 3.3rem)/1.02 var(--f-titre); letter-spacing: -.035em; max-width: 22ch; }}
.tete-page p {{ margin: 0; color: var(--gris); max-width: 68ch; }}
.ligne-info {{ color: var(--gris); font: 400 .8rem/1.4 var(--f-data); margin: .2rem 0 1rem; }}
.ligne-info b {{ color: var(--craie); font-weight: 500; }}

/* fiche */
.metriques {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); border-top: 1px solid var(--filet2); border-bottom: 1px solid var(--filet2); }}
.metriques div {{ padding: 1rem 1rem 1rem 0; display: grid; gap: .3rem; align-content: start; }}
.metriques div + div {{ padding-left: 1rem; border-left: 1px solid var(--filet); }}
.metriques span {{ color: var(--gris); font-size: .8rem; }}
.metriques b {{ font: 500 clamp(1.6rem, 3vw, 2.2rem)/1 var(--f-data); color: var(--c, var(--craie)); }}
.encart {{ border: 1px solid var(--filet2); border-radius: 6px; padding: 1rem 1.1rem; display: grid; gap: .6rem; font-size: .9rem; background: var(--ardoise); }}
.encart dl {{ margin: 0; display: grid; grid-template-columns: auto minmax(0, 1fr); gap: .4rem .9rem; }}
.encart dt {{ color: var(--gris); }}
.encart dd {{ margin: 0; }}
.encart .src {{ color: var(--gris); font-size: .76rem; border-top: 1px solid var(--filet); padding-top: .55rem; }}
.alerte {{ border-left: 3px solid var(--convaincre); padding: .7rem .9rem; background: color-mix(in srgb, var(--convaincre) 8%, transparent); font-size: .9rem; margin-top: 1rem; }}
.fiche-sous {{ color: var(--gris); margin: .3rem 0 .8rem; }}
@media (max-width: 520px) {{ .metriques {{ grid-template-columns: minmax(0, 1fr); }} .metriques div + div {{ padding-left: 0; border-left: 0; border-top: 1px solid var(--filet); }} }}

@media (max-width: 880px) {{
  .positions {{ grid-template-columns: minmax(0, 1fr); }}
  .position:nth-child(even) {{ padding-left: 0; border-left: 0; }}
  .etapes4 {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
  .etapes4 div:nth-child(3) {{ padding-left: 0; border-left: 0; }}
  .ligne-g, .axe {{ grid-template-columns: minmax(0, 6rem) minmax(0, 1fr) 2.4rem; }}
  .ligne-g .nom-g span:last-child {{ display: none; }}
}}
@media (max-width: 520px) {{
  .etapes3, .etapes4 {{ grid-template-columns: minmax(0, 1fr); }}
  .etapes3 li + li, .etapes4 div + div {{ padding-left: 0; border-left: 0; }}
  .decompte {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
}}
@media (prefers-reduced-motion: reduce) {{ svg.hemi circle, .piste i {{ animation: none; }} }}
</style>
"""


def e(s):
    return html.escape(str(s if s is not None else ""))


def marque_rail():
    return '<div class="marque-rail">Cleon<i aria-hidden="true"></i></div>'


def entete_page(methode):
    return (f'<div class="entete-page"><div class="marque">Cleon<i aria-hidden="true"></i></div>'
            f'<div class="methode">{e(methode)}</div></div>')


def coupe(nom, fait=""):
    return f'<div class="coupe"><span class="nom">{e(nom)}</span><span class="fait">{e(fait)}</span></div>'


def titre_bande(titre, sous=""):
    return f'<h2 class="titre-bande">{e(titre)}</h2>' + (f'<p class="sous">{e(sous)}</p>' if sous else "")


def hemicycle_svg(sieges):
    """sieges: list of (group, label class, tooltip), already ordered left to right and, inside each group,
    from the highest score to the lowest. Seats are laid on 11 concentric rows; ordering them by angle turns
    each group into a wedge. Inside a wedge the best scores sit on the inner rows."""
    n_tot = len(sieges)
    if not n_tot:
        return ""
    cx, cy, r_ext, r_int, rangs = 300, 300, 286, 112, 11
    rayons = [r_int + (r_ext - r_int) * i / (rangs - 1) for i in range(rangs)]
    total = sum(rayons)
    pts, reste = [], n_tot
    for i, r in enumerate(rayons):
        n = reste if i == rangs - 1 else round(n_tot * r / total)
        reste -= n
        for k in range(n):
            a = math.pi * (1 - (k + .5) / n)
            pts.append((a, i, cx + r * math.cos(a), cy - r * math.sin(a)))
    pts.sort(key=lambda p: (-p[0], p[1]))
    groupes = []
    for g, *_ in sieges:
        if not groupes or groupes[-1][0] != g:
            groupes.append([g, 0])
        groupes[-1][1] += 1
    cercles, i = [], 0
    for g, n in groupes:
        tranche = sorted(pts[i:i + n], key=lambda p: (p[1], -p[0]))
        for (a, rang, x, y), (_, classe, info) in zip(tranche, sieges[i:i + n]):
            delai = int(rang * 28 + (1 - a / math.pi) * 220)
            cercles.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5.6" fill="var(--{classe})" '
                           f'style="animation-delay:{delai}ms"><title>{e(info)}</title></circle>')
        i += n
    return (f'<svg class="hemi" viewBox="0 0 600 318" role="img" aria-label="Hémicycle de {n_tot} députés en '
            f'exercice, colorés selon leur étiquette">{"".join(cercles)}</svg>')


def compteurs(items):
    """items: list of (value, label, css class)."""
    cases = "".join(f'<div class="compteur {c}"><div class="val">{int(v)}</div><div class="lib">{e(lib)}</div></div>'
                    for v, lib, c in items)
    return f'<div class="compteurs">{cases}</div>'


def repartition(items):
    """items: list of (count, label, css class). A stacked bar with its legend."""
    total = sum(v for v, _, _ in items) or 1
    parts = "".join(f'<span class="{c}" style="width:{100 * v / total:.2f}%;background:var(--c)" '
                    f'title="{e(lib)} : {v}"></span>' for v, lib, c in items if v)
    leg = "".join(f'<span class="{c}"><i></i>{e(lib)} · {v}</span>' for v, lib, c in items)
    return f'<div class="repartition"><div class="barre">{parts}</div><div class="legende">{leg}</div></div>'


def jauge(score, classe):
    """Ring that fills up to the score. score None: empty ring with a dash."""
    p = 0 if score is None else int(score)
    texte = "–" if score is None else str(p)
    couleur = "gris" if classe == "insuffisant" else classe
    return (f'<div class="jauge" style="--p:{p};--c:var(--{couleur})">'
            f'<div class="centre"><b>{texte}</b><small>sur 100</small></div></div>')


def entete(classe, titre, n):
    return f'<div class="entete {classe}"><b>{e(titre)}</b><span>{e(n)}</span></div>'


def tete_page(etiquette, titre, texte=""):
    """Page head shared by every page: a small mono label, a big title, one paragraph."""
    return (f'<div class="tete-page"><span class="etiq">{e(etiquette)}</span><h1>{e(titre)}</h1>'
            + (f'<p>{texte}</p>' if texte else "") + '</div>')


def encart(titre, lignes, source):
    """Bordered side box: a label, term/definition rows (already escaped HTML), a source line."""
    dl = "".join(f"<dt>{e(t)}</dt><dd>{d}</dd>" for t, d in lignes)
    return (f'<aside class="encart"><span class="etiq">{e(titre)}</span><dl>{dl}</dl>'
            f'<span class="src">{e(source)}</span></aside>')


def metriques(items):
    """items: list of (label, value HTML, css class or ""). A ruled row of big mono figures."""
    cases = "".join(f'<div class="{c}"><span>{e(lib)}</span><b>{v}</b></div>' for lib, v, c in items)
    return f'<div class="metriques">{cases}</div>'
