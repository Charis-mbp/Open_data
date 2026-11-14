# Boussole parlementaire

One-day hackathon prototype. A user pastes an organisation's position paper. The app ranks every député of the Assemblée nationale as allié, opposant or à convaincre on a theme, and shows the votes behind each score.

The demo runs locally on my laptop today. There is no login, no deployment and no test suite. Favour the simplest thing that works.

## How to work with me

- Do only the task in my message. When it is done, tell me in a few lines how to check it, then stop and wait.
- I am away from the laptop while you work. Do not ask questions you can answer by reading the code or the data. If you are blocked, pick the simplest option, note the choice in NOTES.md, and carry on.
- Look at the real structure of a data file before writing code that reads it.
- Commit after each completed task with a short message.
- Never delete or overwrite a `validated.json` file. Those hold my manual review and cannot be regenerated.
- If a change would take more than 40 minutes, stop and propose a smaller version.

## Stack

- Python, Streamlit, pandas, SQLite.
- A few flat files, no framework beyond Streamlit, no ORM.
- Run with `streamlit run app.py`.
- Secrets in `.env`, never committed.

## Themes

The app supports several themes. Everything specific to a theme lives in its own folder, and no theme name is hard-coded in the Python files.

There are two themes today:

- `nucleaire`: built first, end to end.
- `sante`: added second, through the same pipeline, with no new code.

When my message names a theme, work on that one. When it names none, work on `nucleaire`. When a prompt mentions "the keywords" or "position.txt", it means the files of the active theme.

```
themes/
  nucleaire/
    theme.json        label shown in the interface, plus thresholds if overridden
    keywords.txt      one keyword per line, in French
    position.txt      the position paper used for the demo
    shortlist.json    scrutins kept after the keyword and quality filters
    matching.json     the model's proposed matches (cache)
    validated.json    my accepted, flipped and rejected matches
  sante/
    (same files)
```

A theme selector in the sidebar switches the whole app between themes. Adding a third theme must need only a new folder with `theme.json`, `keywords.txt` and `position.txt`.

## Files

```
app.py          Streamlit pages and navigation
load_data.py    downloads and parses the open data into SQLite
shortlist.py    keyword and quality filters, per theme
llm.py          the only place that calls a language model
matching.py     position extraction and vote matching, per theme
scoring.py      scores and labels, plain code only
data/           raw files and boussole.db
themes/         one folder per theme
NOTES.md        choices you made while I was away
```

## Data

Source: Assemblée nationale open data for the current legislature, from data.assemblee-nationale.fr. Raw files go in `data/`.

SQLite tables, shared by all themes:

- `deputes`: id, nom, groupe, circonscription
- `scrutins`: id, date, titre, objet, resultat, url
- `votes`: scrutin_id, depute_id, position (pour, contre, abstention, non-votant)

`url` is the page of the scrutin on the Assemblée nationale website.

## Shortlist rules

A scrutin enters a theme's shortlist if its titre or objet matches a keyword of that theme. Then drop:

- scrutins where fewer than 50 députés cast a vote
- scrutins where more than 90% of expressed votes are on the same side

Aim for 50 to 150 scrutins per theme. If a theme has more than 150, keep the 150 with the most even split of pour and contre.

## The language model

- It does two jobs only: extract 3 to 6 positions from a position paper, and propose which shortlisted scrutins relate to them.
- For each proposed match it returns: the position, the vote the organisation would want (pour or contre), a one-sentence reason in French, and a confidence from 0 to 1.
- It never produces a score, a label or a ranking.
- Every call goes through one function in `llm.py`. The provider and model name come from `.env`, so they can be swapped in one place.
- Ask for JSON and validate it before use. On invalid JSON, retry once, then skip that item and log it.
- Cache every result to disk, keyed by theme and by a hash of the input. The demo must work with no connection.

## Scoring

Computed in `scoring.py` from a theme's accepted matches only.

For each député:

- aligned = votes equal to the wanted vote
- opposed = votes equal to the opposite vote
- score = 100 × aligned / (aligned + opposed)
- abstentions and absences are counted and displayed, and are not in the score
- fewer than 5 aligned plus opposed votes: no score, label "données insuffisantes"

Labels:

- allié: score of 70 or more
- opposant: score of 30 or less
- à convaincre: score between 30 and 70
- à convaincre, with the note "s'écarte de son groupe": score 20 points or more above the average of their group, whatever the score (decided 2026-11-14: a député less favourable than their group is no lead)

Thresholds are constants at the top of `scoring.py`.

## Interface

- All text in French.
- Sidebar: theme selector, then the pages.
- Pages: Accueil (paste a paper, see the three lists), Classement, Fiche député, Validation des scrutins, Scrutins.
- Every score links to the votes behind it, and every vote links to its page on the Assemblée nationale website.
- A line under the title states the method: the model proposes the votes, a person validates them, the score is a simple share.
- Results that I have not validated are marked "non validés".
- No error traces on screen. Show a short message in French instead.

## Build order

1. Load the data and the Scrutins page.
2. Shortlist for the active theme.
3. Position extraction, matching and the Validation page.
4. Scoring and the Classement page.
5. Fiche député with the evidence and the "s'écarte de son groupe" rule.
6. Accueil page and demo polish.
7. Second theme: run steps 2 and 3 for `sante`. No new code should be needed. If some is, the theme handling has a bug to fix.
8. Only if time is left: a comparison view showing, for each député, their label on both themes side by side.
