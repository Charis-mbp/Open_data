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
}
DEFAUT = "Vert-de-gris et paon"  # the style used by the app; the other one is kept for reference


def css(nom):
    s = STYLES.get(nom, STYLES[DEFAUT])
    fonts = "|".join(sorted({f.replace(" ", "+") + ":wght@400;600;700"
                             for f in (s["font_titre"], s["font_texte"])}))
    return f"""
<style>
@import url('https://fonts.googleapis.com/css2?family={fonts}&display=swap');
:root {{
  --fond: {s['fond']}; --surface: {s['surface']}; --texte: {s['texte']}; --discret: {s['discret']};
  --accent: {s['accent']}; --ligne: {s['ligne']};
  --allie: {s['allie']}; --convaincre: {s['convaincre']}; --opposant: {s['opposant']};
}}
.stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {{
  background: var(--fond); color: var(--texte);
}}
/* text font on text elements only: spans and divs also hold Streamlit's icon font ("arrow_down") */
.stApp, .stApp p, .stApp li, .stApp label, .stApp input, .stApp textarea, .stApp button {{
  font-family: '{s['font_texte']}', sans-serif;
}}
.stApp h1, .stApp h2, .stApp h3, .stApp h4 {{
  font-family: '{s['font_titre']}', serif; color: var(--texte); letter-spacing: -0.01em;
}}
.stApp h1 {{ border-bottom: 3px solid var(--accent); padding-bottom: .3rem; }}
.stApp p, .stApp li, .stApp label {{ color: var(--texte); }}
[data-testid="stCaptionContainer"], .stApp small {{ color: var(--discret) !important; }}
[data-testid="stSidebar"] {{ background: {s.get('sidebar_fond', s['surface'])}; border-right: 1px solid var(--ligne); }}
[data-testid="stSidebar"] label, [data-testid="stSidebar"] p {{ color: {s.get('sidebar_texte', s['texte'])}; }}
[data-testid="stSidebar"] [data-baseweb="select"] * {{ color: var(--texte); }}
[data-testid="stMetric"] {{
  background: var(--surface); border: 1px solid var(--ligne); border-radius: 10px;
  padding: .7rem 1rem; border-top: 4px solid var(--accent);
}}
[data-testid="stMetricValue"] {{ color: var(--texte); font-family: '{s['font_titre']}', serif; }}
[data-testid="stVerticalBlockBorderWrapper"] {{ border-color: var(--ligne) !important; background: var(--surface); }}
.stButton button, .stDownloadButton button {{
  background: var(--fond); color: var(--accent); border: 1px solid var(--accent); border-radius: 8px;
}}
.stButton button:hover {{ background: var(--accent); color: var(--fond); }}
.stButton button[kind="primary"] {{ background: var(--accent); color: var(--fond); }}
.stApp a {{ color: var(--accent); }}
[data-baseweb="select"] > div, .stTextInput input {{
  background: var(--fond) !important; border-color: var(--ligne) !important; color: var(--texte) !important;
}}
[data-baseweb="tag"] {{ background: var(--accent) !important; }}
[data-testid="stExpander"] details {{ background: var(--surface); border-color: var(--ligne); }}
.pastille {{ display: inline-block; padding: .1rem .6rem; border-radius: 999px; color: #fff;
  font-weight: 600; font-size: .9rem; }}
.pastille.allie {{ background: var(--allie); }}
.pastille.convaincre {{ background: var(--convaincre); }}
.pastille.opposant {{ background: var(--opposant); }}
.pastille.insuffisant {{ background: var(--discret); }}
</style>
"""


def nuancier(nom):
    """Small HTML swatch strip shown under the style selector."""
    s = STYLES[nom]
    cles = ["fond", "surface", "texte", "accent", "allie", "convaincre", "opposant"]
    cases = "".join(f'<span title="{k}" style="display:inline-block;width:22px;height:22px;'
                    f'background:{s[k]};border:1px solid #0002;margin-right:3px;border-radius:4px"></span>'
                    for k in cles)
    return f'<div>{cases}</div><div style="font-size:.75rem;opacity:.8;margin-top:.3rem">{s["note"]}</div>'
