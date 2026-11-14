"""Two visual styles for the app, inspired by Sanzo Wada's "A Dictionary of Color Combinations".

Hex values are approximations of Wada's named colours, not exact plates.
Each style sets the page colours, fonts and the colours of the three labels.
"""

STYLES = {
    "Papier et vermillon": {
        "note": "Ivoire, encre, vermillon : Ivory Buff, Black, Scarlet, Cobalt Green, Yellow Ochre.",
        "font_titre": "Shippori Mincho", "font_texte": "Noto Sans",
        "fond": "#F3ECDD", "surface": "#E8DDC7", "texte": "#2A2723", "discret": "#6F6658",
        "accent": "#C8473A", "ligne": "#CDBFA5",
        "allie": "#4E8A6B", "convaincre": "#D29A2E", "opposant": "#A3322B",
    },
    "Vert-de-gris et paon": {
        "note": "Vert-de-gris profond, bleu paon, ocre : Dusky Green, Peacock Blue, Olive Ocher, Etruscan Red.",
        "font_titre": "Space Grotesk", "font_texte": "Inter",
        "fond": "#C4D2BE", "surface": "#AFC2A8", "texte": "#12201A", "discret": "#3B5246",
        "accent": "#0D5A63", "ligne": "#93AA8C",
        "allie": "#2E6A38", "convaincre": "#B07E14", "opposant": "#8A2E22",
        # dark green sidebar with light text
        "sidebar_fond": "#1F3A30", "sidebar_texte": "#E4ECDF",
    },
    "Nuit et cuivre": {
        "note": "Encre de nuit, cuivre, bleu paon : fond sombre, accent chaud, trois étiquettes lumineuses.",
        "font_titre": "Space Grotesk", "font_texte": "Inter",
        "fond": "#0B1116", "surface": "#121B22", "texte": "#E4ECEA", "discret": "#8DA19C",
        "accent": "#E3A15A", "accent2": "#4FB6C2", "ligne": "#22323B",
        "allie": "#3FC488", "convaincre": "#F2B544", "opposant": "#EF5F57",
        "sidebar_fond": "#080D11", "sidebar_texte": "#C9D6D2",
    },
}
DEFAUT = "Nuit et cuivre"  # the style used by the app; the others are kept for reference


def css(nom):
    s = STYLES.get(nom, STYLES[DEFAUT])
    fonts = "|".join(sorted({f.replace(" ", "+") + ":wght@400;500;600;700"
                             for f in (s["font_titre"], s["font_texte"])}))
    return f"""
<style>
@import url('https://fonts.googleapis.com/css2?family={fonts}&display=swap');
:root {{
  --fond: {s['fond']}; --surface: {s['surface']}; --texte: {s['texte']}; --discret: {s['discret']};
  --accent: {s['accent']}; --accent2: {s.get('accent2', s['accent'])}; --ligne: {s['ligne']};
  --allie: {s['allie']}; --convaincre: {s['convaincre']}; --opposant: {s['opposant']};
  --titre: '{s['font_titre']}', sans-serif;
}}
@property --n {{ syntax: '<integer>'; initial-value: 0; inherits: false; }}
@property --p {{ syntax: '<number>'; initial-value: 0; inherits: false; }}
@keyframes monter {{ from {{ opacity: 0; transform: translateY(14px); }} to {{ opacity: 1; transform: none; }} }}
@keyframes fondu {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}
@keyframes reflet {{ 0% {{ background-position: 0% 50%; }} 100% {{ background-position: 200% 50%; }} }}
@keyframes derive {{ 0%, 100% {{ transform: translate(0, 0) scale(1); }} 50% {{ transform: translate(4%, 3%) scale(1.08); }} }}
@keyframes aiguille {{ 0% {{ transform: rotate(-70deg); }} 55% {{ transform: rotate(28deg); }}
  75% {{ transform: rotate(8deg); }} 100% {{ transform: rotate(16deg); }} }}
@keyframes oscille {{ 0%, 100% {{ transform: rotate(16deg); }} 50% {{ transform: rotate(10deg); }} }}
@keyframes compter {{ from {{ --n: 0; }} }}
@keyframes remplir {{ from {{ --p: 0; }} }}
@keyframes pousser {{ from {{ transform: scaleX(0); }} to {{ transform: scaleX(1); }} }}
@keyframes pouls {{ 0%, 100% {{ box-shadow: 0 0 0 0 color-mix(in srgb, var(--c) 55%, transparent); }}
  50% {{ box-shadow: 0 0 0 6px transparent; }} }}

.stApp, [data-testid="stAppViewContainer"] {{ background: var(--fond); color: var(--texte); }}
[data-testid="stHeader"] {{ background: transparent; }}
/* two slow-drifting glows behind the page */
[data-testid="stAppViewContainer"]::before {{
  content: ""; position: fixed; inset: -20%; z-index: 0; pointer-events: none;
  background:
    radial-gradient(40% 35% at 20% 15%, color-mix(in srgb, var(--accent2) 16%, transparent), transparent 70%),
    radial-gradient(35% 30% at 85% 80%, color-mix(in srgb, var(--accent) 12%, transparent), transparent 70%);
  animation: derive 24s ease-in-out infinite;
}}
[data-testid="stMain"] {{ position: relative; z-index: 1; }}

/* text font on text elements only: spans and divs also hold Streamlit's icon font ("arrow_down") */
.stApp, .stApp p, .stApp li, .stApp label, .stApp input, .stApp textarea, .stApp button {{
  font-family: '{s['font_texte']}', sans-serif;
}}
.stApp h1, .stApp h2, .stApp h3, .stApp h4 {{
  font-family: var(--titre); color: var(--texte); letter-spacing: -0.02em;
}}
.stApp h2 {{ position: relative; padding-bottom: .4rem; }}
.stApp h2::after {{
  content: ""; position: absolute; left: 0; bottom: 0; width: 64px; height: 3px; border-radius: 3px;
  background: linear-gradient(90deg, var(--accent), var(--accent2)); transform-origin: left;
  animation: pousser .7s cubic-bezier(.2,.8,.2,1) both .1s;
}}
.stApp p, .stApp li, .stApp label {{ color: var(--texte); }}
[data-testid="stCaptionContainer"], .stApp small {{ color: var(--discret) !important; }}

/* every block of the page slides in, one after the other */
[data-testid="stMainBlockContainer"] [data-testid="stVerticalBlock"] > div {{
  animation: monter .55s cubic-bezier(.2,.8,.2,1) both;
}}
[data-testid="stMainBlockContainer"] [data-testid="stVerticalBlock"] > div:nth-child(2) {{ animation-delay: .05s; }}
[data-testid="stMainBlockContainer"] [data-testid="stVerticalBlock"] > div:nth-child(3) {{ animation-delay: .1s; }}
[data-testid="stMainBlockContainer"] [data-testid="stVerticalBlock"] > div:nth-child(4) {{ animation-delay: .15s; }}
[data-testid="stMainBlockContainer"] [data-testid="stVerticalBlock"] > div:nth-child(5) {{ animation-delay: .2s; }}
[data-testid="stMainBlockContainer"] [data-testid="stVerticalBlock"] > div:nth-child(n+6) {{ animation-delay: .25s; }}

/* sidebar: dark rail, pages as pills */
[data-testid="stSidebar"] {{ background: {s.get('sidebar_fond', s['surface'])}; border-right: 1px solid var(--ligne); }}
[data-testid="stSidebar"] label, [data-testid="stSidebar"] p {{ color: {s.get('sidebar_texte', s['texte'])}; }}
[data-testid="stSidebar"] [role="radiogroup"] {{ gap: .2rem; }}
[data-testid="stSidebar"] [role="radiogroup"] > label {{
  padding: .45rem .7rem; border-radius: 10px; width: 100%; border: 1px solid transparent;
  transition: background .2s, border-color .2s, transform .2s;
}}
[data-testid="stSidebar"] [role="radiogroup"] > label:hover {{
  background: color-mix(in srgb, var(--accent2) 10%, transparent); transform: translateX(3px);
}}
[data-testid="stSidebar"] [role="radiogroup"] > label:has(input:checked) {{
  background: color-mix(in srgb, var(--accent) 14%, transparent);
  border-color: color-mix(in srgb, var(--accent) 45%, transparent);
}}
[data-testid="stSidebar"] [role="radiogroup"] > label:has(input:checked) p {{ color: var(--accent); font-weight: 600; }}

/* cards */
[data-testid="stMetric"] {{
  background: linear-gradient(160deg, color-mix(in srgb, var(--surface) 92%, white 8%), var(--surface));
  border: 1px solid var(--ligne); border-radius: 14px; padding: .9rem 1.1rem;
  transition: transform .25s, box-shadow .25s, border-color .25s;
}}
[data-testid="stMetric"]:hover {{
  transform: translateY(-3px); border-color: color-mix(in srgb, var(--accent) 50%, transparent);
  box-shadow: 0 10px 30px -12px color-mix(in srgb, var(--accent) 45%, transparent);
}}
[data-testid="stMetricValue"] {{ color: var(--texte); font-family: var(--titre); }}
[data-testid="stVerticalBlockBorderWrapper"], .stForm {{
  border-color: var(--ligne) !important; background: var(--surface); border-radius: 14px !important;
}}
[data-testid="stExpander"] details {{ background: var(--surface); border-color: var(--ligne); border-radius: 14px; }}
[data-testid="stDataFrame"] {{ border: 1px solid var(--ligne); border-radius: 12px; overflow: hidden; }}
[data-testid="stAlert"] {{ border-radius: 12px; }}

/* buttons */
.stButton button, .stDownloadButton button, .stFormSubmitButton button {{
  background: var(--surface); color: var(--texte); border: 1px solid var(--ligne); border-radius: 10px;
  transition: transform .2s, border-color .2s, box-shadow .2s, background .2s;
}}
.stButton button:hover, .stFormSubmitButton button:hover {{
  border-color: var(--accent); color: var(--accent); transform: translateY(-2px);
  box-shadow: 0 8px 22px -10px color-mix(in srgb, var(--accent) 60%, transparent);
}}
.stButton button[kind="primary"], .stFormSubmitButton button[kind="primaryFormSubmit"] {{
  background: linear-gradient(120deg, var(--accent), color-mix(in srgb, var(--accent) 70%, var(--opposant)));
  color: var(--fond); border: none; font-weight: 600;
}}
.stButton button[kind="primary"]:hover, .stFormSubmitButton button[kind="primaryFormSubmit"]:hover {{ color: var(--fond); }}
.stApp a {{ color: var(--accent2); text-decoration: none; border-bottom: 1px solid transparent; transition: border-color .2s; }}
.stApp a:hover {{ border-bottom-color: var(--accent2); }}
[data-baseweb="select"] > div, .stTextInput input, .stTextArea textarea {{
  background: var(--fond) !important; border-color: var(--ligne) !important; color: var(--texte) !important;
}}
[data-baseweb="tag"] {{ background: var(--accent) !important; }}
.stTabs [data-baseweb="tab-highlight"] {{ background: var(--accent); }}

/* the three Accueil columns: a coloured edge on each name */
[class*="st-key-liste-"] button {{ justify-content: flex-start; text-align: left; border-left: 3px solid var(--c); }}
[class*="st-key-liste-"] button:hover {{ border-color: var(--c); color: var(--c);
  box-shadow: 0 8px 22px -10px var(--c); }}
.st-key-liste-allie {{ --c: var(--allie); }}
.st-key-liste-convaincre {{ --c: var(--convaincre); }}
.st-key-liste-opposant {{ --c: var(--opposant); }}

/* label pills */
.pastille {{ display: inline-block; padding: .15rem .7rem; border-radius: 999px; color: var(--fond);
  font-weight: 600; font-size: .9rem; background: var(--c); animation: pouls 2.4s ease-in-out infinite; }}
.pastille.allie {{ --c: var(--allie); }}
.pastille.convaincre {{ --c: var(--convaincre); }}
.pastille.opposant {{ --c: var(--opposant); }}
.pastille.insuffisant {{ --c: var(--discret); animation: none; }}

/* hero with compass */
.hero {{ display: flex; align-items: center; gap: 1.1rem; margin: .2rem 0 .3rem; }}
.hero svg {{ width: 64px; height: 64px; flex: none; filter: drop-shadow(0 0 14px color-mix(in srgb, var(--accent) 40%, transparent)); }}
.hero .aig {{ transform-origin: 32px 32px; animation: aiguille 1.6s cubic-bezier(.3,1.4,.4,1) both,
  oscille 5s ease-in-out 1.6s infinite; }}
.hero .cad {{ transform-origin: 32px 32px; animation: fondu 1s both; }}
.hero h1 {{
  margin: 0; padding: 0; font-size: 2.4rem; line-height: 1.05; border: none;
  background: linear-gradient(90deg, var(--texte), var(--accent), var(--accent2), var(--texte));
  background-size: 200% auto; -webkit-background-clip: text; background-clip: text; color: transparent !important;
  animation: reflet 9s linear infinite;
}}
.hero .methode {{ color: var(--discret); font-size: .88rem; margin-top: .35rem; }}

/* animated counters */
.compteurs {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: .8rem; margin: .6rem 0 1rem; }}
.compteur {{ background: var(--surface); border: 1px solid var(--ligne); border-radius: 14px; padding: .9rem 1.1rem;
  position: relative; overflow: hidden; animation: monter .6s cubic-bezier(.2,.8,.2,1) both;
  transition: transform .25s, box-shadow .25s; }}
.compteur:hover {{ transform: translateY(-3px); box-shadow: 0 12px 30px -14px var(--c); }}
.compteur::before {{ content: ""; position: absolute; inset: 0 auto 0 0; width: 4px; background: var(--c); }}
.compteur .val {{ font-family: var(--titre); font-size: 2.1rem; font-weight: 700; color: var(--c);
  counter-reset: n var(--n); animation: compter 1.6s cubic-bezier(.2,.8,.2,1) both; }}
.compteur .val::after {{ content: counter(n); }}
.compteur .lib {{ color: var(--discret); font-size: .85rem; }}

/* stacked bar of labels */
.repartition {{ margin: .4rem 0 1.2rem; }}
.repartition .barre {{ display: flex; height: 16px; border-radius: 999px; overflow: hidden; background: var(--ligne);
  transform-origin: left; animation: pousser 1.1s cubic-bezier(.2,.8,.2,1) both .2s; }}
.repartition .barre span {{ height: 100%; transition: filter .2s; }}
.repartition .barre span:hover {{ filter: brightness(1.25); }}
.repartition .legende {{ display: flex; flex-wrap: wrap; gap: 1rem; margin-top: .5rem; font-size: .85rem; color: var(--discret); }}
.repartition .legende i {{ display: inline-block; width: 10px; height: 10px; border-radius: 3px; margin-right: .35rem; background: var(--c); }}

/* score ring */
.jauge {{ --c: var(--accent); width: 150px; aspect-ratio: 1; border-radius: 50%; display: grid; place-items: center;
  background: conic-gradient(var(--c) calc(var(--p) * 1%), var(--ligne) 0);
  animation: remplir 1.4s cubic-bezier(.2,.8,.2,1) both; position: relative;
  filter: drop-shadow(0 0 18px color-mix(in srgb, var(--c) 35%, transparent)); }}
.jauge::before {{ content: ""; position: absolute; inset: 12px; border-radius: 50%; background: var(--fond); }}
.jauge .centre {{ position: relative; text-align: center; font-family: var(--titre); }}
.jauge .centre b {{ display: block; font-size: 2.4rem; line-height: 1; color: var(--texte); }}
.jauge .centre small {{ color: var(--discret); font-size: .8rem; }}

/* column headers on Accueil */
.entete {{ display: flex; align-items: baseline; gap: .5rem; padding: .7rem 1rem; margin-bottom: .5rem;
  border-radius: 12px; background: linear-gradient(120deg, color-mix(in srgb, var(--c) 22%, transparent), transparent);
  border: 1px solid color-mix(in srgb, var(--c) 35%, transparent); }}
.entete b {{ font-family: var(--titre); font-size: 1.15rem; color: var(--c); }}
.entete span {{ color: var(--discret); font-size: .9rem; }}
.entete.allie, .compteur.allie, .repartition .allie {{ --c: var(--allie); }}
.entete.convaincre, .compteur.convaincre, .repartition .convaincre {{ --c: var(--convaincre); }}
.entete.opposant, .compteur.opposant, .repartition .opposant {{ --c: var(--opposant); }}
.compteur.neutre, .repartition .insuffisant {{ --c: var(--discret); }}
.compteur.accent {{ --c: var(--accent2); }}

@media (prefers-reduced-motion: reduce) {{
  *, *::before, *::after {{ animation-duration: .01s !important; animation-iteration-count: 1 !important; }}
}}
</style>
"""


BOUSSOLE_SVG = """<svg viewBox="0 0 64 64" aria-hidden="true">
<g class="cad"><circle cx="32" cy="32" r="29" fill="none" stroke="var(--ligne)" stroke-width="2"/>
<circle cx="32" cy="32" r="23" fill="none" stroke="var(--accent2)" stroke-opacity=".35" stroke-dasharray="2 4"/>
<text x="32" y="10.5" text-anchor="middle" font-size="6" fill="var(--discret)" font-family="sans-serif">N</text></g>
<g class="aig"><polygon points="32,8 36,32 28,32" fill="var(--accent)"/><polygon points="32,56 36,32 28,32" fill="var(--discret)"/>
<circle cx="32" cy="32" r="3" fill="var(--texte)"/></g></svg>"""


def hero(titre, methode):
    return (f'<div class="hero">{BOUSSOLE_SVG}<div><h1>{titre}</h1>'
            f'<div class="methode">{methode}</div></div></div>')


def compteurs(items):
    """items: list of (value, label, css class). Numbers count up from 0."""
    cases = "".join(f'<div class="compteur {c}" style="--n:{int(v)};animation-delay:{i * .08:.2f}s">'
                    f'<div class="val" style="--n:{int(v)}"></div><div class="lib">{lib}</div></div>'
                    for i, (v, lib, c) in enumerate(items))
    return f'<div class="compteurs">{cases}</div>'


def repartition(items):
    """items: list of (count, label, css class). A stacked bar that grows from the left."""
    total = sum(v for v, _, _ in items) or 1
    parts = "".join(f'<span class="{c}" style="width:{100 * v / total:.2f}%;background:var(--c)" '
                    f'title="{lib} : {v}"></span>' for v, lib, c in items if v)
    leg = "".join(f'<span class="{c}"><i></i>{lib} · {v}</span>' for v, lib, c in items)
    return f'<div class="repartition"><div class="barre">{parts}</div><div class="legende">{leg}</div></div>'


def jauge(score, classe):
    """Ring that fills up to the score. score None: empty ring with a dash."""
    p = 0 if score is None else int(score)
    texte = "–" if score is None else str(p)
    return (f'<div class="jauge" style="--p:{p};--c:var(--{classe if classe != "insuffisant" else "discret"})">'
            f'<div class="centre"><b>{texte}</b><small>sur 100</small></div></div>')


def entete(classe, titre, n):
    return f'<div class="entete {classe}"><b>{titre}</b><span>{n}</span></div>'


def nuancier(nom):
    """Small HTML swatch strip shown under the style selector."""
    s = STYLES[nom]
    cles = ["fond", "surface", "texte", "accent", "allie", "convaincre", "opposant"]
    cases = "".join(f'<span title="{k}" style="display:inline-block;width:22px;height:22px;'
                    f'background:{s[k]};border:1px solid #0002;margin-right:3px;border-radius:4px"></span>'
                    for k in cles)
    return f'<div>{cases}</div><div style="font-size:.75rem;opacity:.8;margin-top:.3rem">{s["note"]}</div>'
