# Handoff: Boussole parlementaire

Recap for a Claude session that picks this project up on another computer. Read `CLAUDE.md` first
(the project rules), then this file, then `NOTES.md` (every choice made so far, task by task).

State on 2026-11-14: build steps 1 to 5 are done and committed. Next is step 6 (Accueil, light version) and UI polish.

## 1. Moving the project to the other computer

There is **no git remote**. Copy the repo with a bundle (it keeps the full history):

```bash
# on this computer
git bundle create boussole.bundle --all
# on the other computer
git clone boussole.bundle Hack_Data_open
```

Things that are **not in git** and must be redone or copied:

| What | Why it is not in git | What to do |
|---|---|---|
| `.venv/` | local | `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt` |
| `.env` | secrets rule | create it with exactly the 2 lines below |
| `data/` | gitignored, about 530 MB | either copy `data/boussole.db` (141 MB, enough to run the app), or run `.venv/bin/python load_data.py`, which downloads about 380 MB and builds the database in about 30 s after download |

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
| 3. Positions, matching, Validation page | done: 4 positions, 53 proposals, user reviewed all of them (51 accepted incl. 1 inverted, 2 rejected) |
| 4. Scoring + Classement page | done |
| 5. Fiche député + "s'écarte de son groupe" rule | done: 17 current députés flagged |
| 6. Accueil page + demo polish | **next**: light version (Sfen paper already analysed, no live analysis without API credits) |
| 7. Theme `sante` through the same pipeline | todo: `themes/sante/` is empty (needs theme.json, keywords.txt, position.txt from the user) |
| 8. Comparison view across themes | only if time |

## 4. Files

```
app.py        Streamlit: sidebar theme selector + pages Classement, Validation des scrutins, Shortlist, Scrutins
load_data.py  downloads open data (Scrutins, AMO20 députés/organes, Amendements) and builds data/boussole.db
shortlist.py  keyword (whole word, accent-insensitive) + quality filters -> themes/<t>/shortlist.json
llm.py        the only model entry point: ask_json(theme, task, system, prompt, validate), disk cache
matching.py   position extraction, matching in batches of 20 with amendment exposés, validated.json helpers
scoring.py    scores and labels, plain pandas
themes/nucleaire/
  theme.json, keywords.txt, position.txt (Sfen), shortlist.json
  llm_manuel/   prompts + hand-written answers (provider "manuel"), kept as provenance
  llm_cache/    validated answers, keyed by hash; this is what makes the demo work offline
  matching.json the 4 positions and 53 proposals
  validated.json  THE USER'S MANUAL REVIEW: never delete or overwrite, only update entry by entry
  validated.backup.json  previous version, written before each save
NOTES.md      decisions log; append to it after each task
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

Points the user may still revisit on the Validation page: n° 2547/2548 (ECOS renewables-only target, accepted
though borderline) and n° 2433 (LFI fossil-exit amendment, inverted to "contre", which contradicts P3).

## 8. Next task: step 5, Fiche député

Per CLAUDE.md:
- page "Fiche député": identity, group, circonscription, score + label per theme, and the evidence: every
  accepted scrutin with the wanted vote, their vote, how it counted, the reason, a link to the AN page.
  The Classement page already has a "Votes derrière un score" table (`votes_derriere()` in app.py) to reuse.
- rule in `scoring.py`: score 20 points or more away from the average of their group → label "à convaincre"
  with the note "s'écarte de son groupe", whatever the score. Group = `deputes.groupe` (current group);
  average over the group members who have a score. Put the 20 as a constant at the top of scoring.py.
- every score links to its votes; every vote links to the AN website.

## 9. Working with the user

- Follow CLAUDE.md: do only the task asked, then give a few lines on how to check it and stop. Commit after each task.
  Note choices in NOTES.md. Never delete or overwrite `validated.json`.
- The user is often away while you work. Don't ask what the code or data can answer.
- All UI text in French. No error traces on screen (app.py prints them to the terminal only).
- Testing pattern that worked: `streamlit.testing.v1.AppTest` against app.py. For anything that writes
  model answers or decisions, use a scratch copy of the theme folder, never the real one.
