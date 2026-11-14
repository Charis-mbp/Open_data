# Boussole parlementaire

Paste an organisation's position paper. The Boussole ranks every député of the Assemblée nationale (17th
legislature) as **allié**, **opposant** or **à convaincre** on a theme, and shows the votes behind each score,
each linked to its page on the Assemblée nationale website. The interface is in French.

Demo theme: nuclear and energy, with the Sfen's note on the PPE (February 2026).

## Method

1. A language model extracts 3 to 6 positions from the paper and proposes which scrutins relate to them, with the vote the organisation would want.
2. A person accepts, flips or rejects each proposal; only validated scrutins count.
3. Score = share of a député's pour/contre votes that go the wanted way (70+ allié, 30 or less opposant, in between à convaincre).

A député is also "à convaincre", with the note "s'écarte de son groupe", when their loyalty to their group
(measured by [Hémicycle](https://hemicycle.ai) over the whole legislature) is at least 5 points below the group
median, and their theme score is at least 10 points above the group average.

## Run it

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/streamlit run app.py
```

Create a `.env` with:

```
LLM_PROVIDER=manuel
LLM_MODEL=claude-code
```

The model's answers for the demo are cached in `themes/nucleaire/`, so the app runs offline with no API key.

## Data

The repository and the deployed build carry `data/boussole_demo.db` (2.5 MB). It holds only the energy
scrutins: the 150 in the nuclear theme's shortlist, their votes, and all députés, groups and mandates.
It is enough to run every page of the demo.

`load_data.py` downloads the Assemblée nationale open data (data.assemblee-nationale.fr) and rebuilds the full
database, `data/boussole.db`, with all 9 895 scrutins of the legislature. The app uses it when it is present.
`make_demo_db.py` then refreshes the demo copy from it.

Sources: Assemblée nationale open data (Licence Ouverte); group loyalty and député fiches from Hémicycle,
cached in `data/hemicycle/`.

## Layout

```
app.py          Streamlit pages
load_data.py    open data -> data/boussole.db
make_demo_db.py data/boussole.db -> data/boussole_demo.db
shortlist.py    keyword and quality filters, per theme
llm.py          the only place that calls a language model
matching.py     position extraction and vote matching
scoring.py      scores and labels, plain code
hemicycle.py    Hémicycle client and cached fiches
themes/<theme>/ everything specific to a theme (keywords, paper, shortlist, validations)
```

Adding a theme takes a new folder in `themes/` with `theme.json`, `keywords.txt` and `position.txt`.
