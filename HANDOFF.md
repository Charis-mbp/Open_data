# Handoff: Boussole parlementaire

Recap for a Claude session that picks this project up on another computer. Read `CLAUDE.md` first
(the project rules), then this file, then `NOTES.md` (every choice made so far, task by task).

State on 2026-11-14: build steps 1 to 6 are done and committed, plus Hémicycle loyalty and fiches, a
"Prochain vote" page and a small demo database for deploys. The user dropped `sante` (steps 7 and 8) for today.

## 1. Getting the project on another computer

The repo is on GitHub: `git clone https://github.com/Charis-mbp/Open_data.git`.

| What | In git? | What to do |
|---|---|---|
| `data/boussole_demo.db` (2.5 MB) | yes | enough to run the demo: the 150 shortlisted scrutins and their votes, all députés, groupes, mandats |
| `data/hemicycle/` | yes | cached Hémicycle loyalty (11 groups) and 30 fiches; they cost credits, don't delete |
| `data/boussole.db` (141 MB) and raw files | no | optional: `.venv/bin/python load_data.py` rebuilds all 9 895 scrutins from the open data, then `make_demo_db.py` refreshes the demo copy |
| `.venv/` | no | `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt` |
| `.env` | no (secrets) | the 2 lines below |

The app uses `data/boussole.db` when it exists, `data/boussole_demo.db` otherwise (`shortlist.DB_PATH`).

`.env` must be exactly:
```
LLM_PROVIDER=manuel
LLM_MODEL=claude-code
```
The LLM cache keys include provider and model. With any other values, the cached analysis is not found and
the pipeline asks for new answers.

Run: `.venv/bin/streamlit run app.py`

## 2. What the app does

The user pastes an organisation's position paper. The app ranks every député of the 17th legislature as
allié / opposant / à convaincre on a theme, and shows the votes behind each score.
Method line shown under the title: the model proposes the votes, a person validates them, and the score is a simple share.

Demo theme `nucleaire`: position paper of the **Sfen** on the PPE (Feb 2026), in
`themes/nucleaire/position.txt`.

## 3. Build order status

| Step | Status |
|---|---|
| 1. Data + Scrutins page | done |
| 2. Shortlist per theme | done: 150 scrutins for nucleaire |
| 3. Positions, matching, Validation page | done: 4 positions, 53 proposals, all reviewed (51 accepted incl. 1 inverted, 2 rejected) |
| 4. Scoring + Classement page | done |
| 5. Fiche député + "s'écarte de son groupe" rule | done, rule revised twice (see section 7) |
| 6. Accueil page + demo polish | done; DEMO.md is the 3-minute script, prospectus.html the one-pager |
| 7. Theme `sante` | dropped for today: `themes/sante/` is empty |
| 8. Comparison view across themes | dropped for today |

## 4. Files

```
app.py          Streamlit: Accueil, Prochain vote, Classement, Fiche député, Validation des scrutins, Shortlist, Scrutins
load_data.py    downloads open data (Scrutins, AMO20 députés/organes, Amendements) and builds data/boussole.db
make_demo_db.py writes data/boussole_demo.db from boussole.db (shortlisted scrutins of every theme only)
shortlist.py    keyword (whole word, accent-insensitive) + quality filters -> themes/<t>/shortlist.json; DB_PATH
llm.py          the only model entry point: ask_json(theme, task, system, prompt, validate), disk cache
matching.py     position extraction, matching in batches of 20 with amendment exposés, validated.json helpers
scoring.py      scores and labels, plain pandas; reads the cached Hémicycle loyalty
hemicycle.py    Hémicycle: prediction client (Prochain vote) and reader of the cached fiches
styles.py       the "Vert-de-gris et paon" look
data/hemicycle/ loyaute_<SIGLE>.json, acteurs/<id>.json (fetched through the Hémicycle MCP server, trimmed)
themes/nucleaire/
  theme.json, keywords.txt, position.txt (Sfen), shortlist.json
  llm_manuel/   prompts + hand-written answers (provider "manuel"), kept as provenance
  llm_cache/    validated answers, keyed by hash; this is what makes the demo work offline
  matching.json the 4 positions and 53 proposals
  validated.json  THE USER'S MANUAL REVIEW: never delete or overwrite, only update entry by entry
  validated.backup.json  previous version, written before each save
  hemicycle/    raw Orcet response (404: no prediction for that amendment)
DEMO.md, prospectus.html, README.md
NOTES.md        decisions log; append to it after each task
```

## 5. Database (data/boussole.db)

- `deputes(id, nom, groupe, circonscription)`: 655 rows. Group = current, or last for former députés.
- `mandats(depute_id, debut, fin)`: periods in office (fin NULL = ongoing; 574 députés in office now).
- `groupes(id, nom, sigle)`
- `scrutins(id, date, titre, objet, resultat, url, numero, seance_ref, amendement_id)`: 9 895 rows
- `votes(scrutin_id, depute_id, position, groupe)`: position in pour/contre/abstention/non-votant.
  `groupe` = group id **at the time of the vote**.
- `amendements(id, numero, auteur, groupe, expose, dispositif, sort, parent_id)`: only the amendments voted
  in a scrutin, plus the parents of voted sub-amendments. Scrutin↔amendment join on (séance, number), with
  the author named in the title used to break ties. 147/147 linked in the nucleaire shortlist.

Counts rebuilt from individual votes match the official totals for all 9 895 scrutins (checked by load_data.py).

## 6. The model, without API credits

The user has **no Anthropic API credits**. `llm.py` has a provider `manuel`. When an answer is missing, it
writes the exact prompt to `themes/<t>/llm_manuel/<hash>.prompt.txt` and raises `ReponseManuelleAttendue`.
The Claude Code session reads the prompt, writes the raw JSON answer to `<hash>.reponse.txt`, and the next
run of `.venv/bin/python matching.py <theme>` validates and caches it. In manual mode, `matching.run()`
exports **all** missing batch prompts in one go before stopping.
The `anthropic` provider is still there (claude-opus-5-5, server-side refusal fallback on) if a key appears.
Consequence: analysing a **new** paper pasted on the Accueil page (step 6) needs either a key or one manual
round in Claude Code. Plan the demo around the already-analysed Sfen paper.

How the nucleaire answers were judged (keep the same standard for `sante`): match only when adopting the
text clearly helps or hurts a position in the paper; judge the direction from the exposé, not the subject
(a "pour" on an amendment that weakens a position = wanted vote "contre"); skip topics the paper takes no
stand on (here: hydroelectricity bill, wind/solar moratorium, tariffs, EDF status).

## 7. Current results (nucleaire)

574 current députés: 125 allié, 109 opposant, 65 à convaincre, 275 données insuffisantes (median député cast
only 6 pour/contre votes on the 51 scrutins: few attend séance votes on amendments).
Group averages: DR 89, UDR 86, RN 86, HOR 73, LIOT 69, DEM 51, EPR 48, GDR 47, SOC 24, LFI 6, ECOS 6.
EPR at 48 is explained by the majority voting down pro-nuclear RN/DR amendments. Worth a sentence in the demo.

"S'écarte de son groupe" (scoring.py, decided 2026-11-14): Hémicycle loyalty at least 5 points below the group
median (`ECART_LOYAUTE`) **and** theme score at least 10 points above the group average (`ECART_GROUPE`).
Label "à convaincre" whatever the score. Two députés today: Romain Daubié (DEM, 61 vs 51, loyalty 88 % vs 95 %;
the demo's example) and Danielle Brulebois (EPR, 60 vs 48, but only 5 votes).

Points the user may still revisit on the Validation page: n° 2547/2548 (ECOS renewables-only target, accepted
though borderline) and n° 2433 (LFI fossil-exit amendment, inverted to "contre", which contradicts P3).

## 8. Hémicycle

MCP server `hemicycle` (credits: 1 per read, 5 per aggregate, 50 per Orcet prediction). Calls made so far:
`loyaute_deputes` per group (55 credits), `lire_acteur` for the 30 Accueil députés (30), one Orcet call (404,
free). Run aggregate calls one at a time: in parallel they fail with 422/429. Orcet's prediction is an
aggregate (mean probability of voting pour), not per député. Details in NOTES.md, tasks 11–12.

## 9. Working with the user

- Follow CLAUDE.md: do only the task asked, then give a few lines on how to check it and stop. Commit after each task.
  Note choices in NOTES.md. Never delete or overwrite `validated.json`.
- The user is often away while you work. Don't ask what the code or data can answer.
- All UI text in French. No error traces on screen (app.py prints them to the terminal only).
- Testing pattern that worked: `streamlit.testing.v1.AppTest` against app.py. For anything that writes
  model answers or decisions, use a scratch copy of the theme folder, never the real one.
