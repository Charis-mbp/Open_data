# Notes

Choices made while you were away.

## Setup (task 1)

- There was an empty `theme/` folder. CLAUDE.md says `themes/`, so I renamed it. `themes/sante/` is still empty.
- Python deps go in a project venv, `.venv/` (gitignored), listed in `requirements.txt`.
  Run with `.venv/bin/streamlit run app.py`.
- Legislature: the 17th. No 18th repository exists on data.assemblee-nationale.fr.
- Députés come from **AMO20** (every député of the legislature, including former ones), not AMO10
  (active députés only). With AMO10, 79 députés who voted had no name. The `deputes` table has 655 rows.
- `groupe` = current political group, or the last one for a former député. A député's group at the time
  of each vote is not stored yet.
- Vote mapping: `nonVotants` and `nonVotantsVolontaires` both become `non-votant`.
  Députés absent from a scrutin get no row in `votes`.
- I added a `numero` column to `scrutins`, used for sorting and display.
- `load_data.py` checks the pour/contre/abstention counts rebuilt from individual votes against the
  official totals in each file: all 9 895 scrutins match. Scrutin n° 2653 also matches the website
  (142 pour, 377 contre, 47 abstention).

## "Gremillet" never appears in the data

No scrutin titre or objet contains "Gremillet", and neither does any raw file. The bill appears as
"proposition de loi portant programmation nationale énergie et climat pour les années 2025 à 2035"
(206 scrutins), plus one scrutin on the whole bill worded "programmation nationale **pour l'énergie et le climat**"
(n° 2653).
Effect on step 2: the keywords `Gremillet` and `programmation énergétique` match nothing. Adding
`programmation nationale énergie` and `énergie et le climat` to `keywords.txt` would catch them. I have not
changed the keywords, since you chose them.

## Shortlist (task 2)

- `keywords.txt` had been edited (programmation nationale, transition énergétique, éolien, …) when I
  started. I used your version as is, and it is included in this commit.
- Keyword matching is **whole word**, case and accent insensitive, on titre + objet. Substring matching would
  let `EPR` match "reprise" or "représentant". Side effect: `nucléaire` does not match "nucléaires",
  which keeps out the bill on victims of nuclear tests. Plurals need their own line in `keywords.txt`.
- "Cast a vote" = pour + contre + abstention. "Expressed votes" = pour + contre.
- "Most even split" = smallest |pour − contre| / (pour + contre), stored as `ecart` in shortlist.json.
- Thresholds are constants at the top of `shortlist.py`. A theme can override them in theme.json with
  `"shortlist": {"min_votants": 50, "max_meme_cote": 0.9, "max_scrutins": 150}`.
- Result for nucleaire: 249 match a keyword, 5 have under 50 votants, 28 are over 90% one-sided, 216 remain,
  and the 150 most even are kept. All come from two bills: the PPE bill (programmation nationale énergie
  et climat) and the hydroelectricity bill. Scrutin 2653 is in the list.
- `votes` has a new `groupe` column: the député's group **at the time of the vote**, taken from the scrutin
  file. There is also a new `groupes` table (id, nom, sigle). In 14 non-energy scrutins the source gives an
  invalid group "PO0". For those, I use the député's current group instead.
- The page's error handler now prints the traceback in the terminal. The screen still shows only the French message.

## Matching and validation (task 3)

- **No `.env` and no `position.txt` existed.** I could not call the model, so nothing has been generated
  yet. To run it: `cp .env.example .env`, add the key, then either click "Lancer l'analyse par le modèle"
  on the Validation page or run `.venv/bin/python matching.py nucleaire`. Allow a few minutes: 1 extraction
  call plus 8 batches of 20.
- **`themes/nucleaire/position.txt` is a FICTIONAL example I wrote** ("Association Énergie Claire": EPR2,
  no moratorium on wind, hydroelectricity, consumer prices, programming law). Its first line says
  it is an example. Replace it with the real paper before running the analysis. A new text gets a new
  hash, so it triggers fresh calls.
- Provider: only `anthropic` is implemented in `llm.py` (`_call`). Another provider means adding one branch there.
  Default model: `claude-opus-5-5`, effort `medium`. Server-side refusal fallback is on
  (`fallbacks="default"`): if the model declines a request, the API retries it on another model within the
  same call. Remove the two lines in `_call_anthropic` if you don't want that.
- Cache: `themes/<theme>/llm_cache/<hash>.json`, one file per call. The hash covers provider, model, prompt
  and input. It is committed, so the demo works offline. Changing the model in `.env` means new calls.
  Invalid answers are never cached. Log: `data/llm.log`.
- One match per scrutin at most: the model keeps the most direct position. This keeps the score simple
  (one wanted vote per scrutin).
- `validated.json` is keyed by scrutin numero. Each decision is `accepte`, `inverse` or `rejete`, and
  `vote_retenu` holds the vote used for scoring (null if rejected). Every save merges into the existing file
  (never replaces it), writes through a temp file, and first copies the previous version to
  `validated.backup.json`. A decision can be changed later from the "Acceptés" / "Rejetés" views.
- I tested the whole pipeline and the page with a stubbed model, in a scratch copy of the theme. Nothing
  fake was written to `themes/nucleaire`.
- **Known limit:** most shortlisted scrutins are amendments, and their titles only say
  "l'amendement n° 345 de M. X à l'article 5". The model cannot know what the amendment does, so it must
  guess from the author and give low confidence. Better version (about 30 min): download the amendments
  dataset and add each amendment's "exposé sommaire" to the prompt. Not done.

## Amendments (task 4)

- Source: `loi/amendements_div_legis/Amendements.json.zip` (363 MB, 148 034 amendments). `load_data.py` reads
  it inside the zip, without extracting it. Loading takes about 30 s.
- Link scrutin → amendment: number taken from the title ("l'amendement n° 345…", "le sous-amendement n° 781…",
  "l'amendement de suppression n° 622…"), joined on (scrutin `seanceRef`, amendment `seanceDiscussionRef`,
  number). When two texts debated in the same séance share a number, I keep the amendment whose first
  signatory is named in the title. Result: 6 445 of 8 456 amendment scrutins linked across the legislature,
  and **all 147 amendment scrutins of the nucleaire shortlist** (the other 3 are votes on an article or on the
  whole text). 0.5% of links name a different author than the title, mostly titles citing a co-signatory.
- New: table `amendements` (id, numero, auteur = first signatory + "et al.", groupe = sigle or "Gouvernement",
  expose, dispositif, sort, parent_id) and columns `scrutins.seance_ref` and `scrutins.amendement_id`.
  Only amendments voted in a scrutin, plus the parents of voted sub-amendments, are stored.
- Prompt: each amendment gets its author, the author's group and its exposé truncated to 700 characters.
  For a sub-amendment, the amendment it modifies also gets author, group and exposé (400 characters).
  The rule that a "pour" on an amendment working against a position is a vote against it is kept.
  Constants `EXPOSE_MAX` and `EXPOSE_PARENT_MAX` are at the top of `matching.py`. A batch of 20 is about 22 000 characters.
- Cache: there was nothing to clear, because the analysis had never run (no `.env`). The prompt changed
  anyway, so any earlier cache would have been bypassed.
- Comparison: `.venv/bin/python matching.py nucleaire --comparer` runs the analysis with the amendments
  and again on titles only (written to `matching_titres.json`, the Validation page ignores it), then prints
  the average confidence of each. Not run: no API key.
- **`requirements.txt` holds the Sfen position paper**, pasted in place of the dependency list.
  `themes/nucleaire/position.txt` still holds my fictional example. I did not move the text: that is for you
  to do. The dependency list is in the last commit (`git checkout requirements.txt` restores it).

## Analysis without API credits (task 5)

- You have no API credits, so the model calls were answered by Claude (Opus 5.5) inside this Claude Code
  session, through a new provider `LLM_PROVIDER=manuel` in `llm.py`. `.env` holds `LLM_PROVIDER=manuel` and
  `LLM_MODEL=claude-code`, no secrets. For each missing answer, `llm.py` writes the exact prompt to
  `themes/<theme>/llm_manuel/<hash>.prompt.txt`. The answer goes in `<hash>.reponse.txt`, and the next run
  validates and caches it like any other answer. Prompts and answers are committed as a record.
- `themes/nucleaire/position.txt` now holds the real Sfen paper (you moved it from requirements.txt).
  Positions extracted: P1 relaunch nuclear (EPR2, small innovative reactors, recycling), P2 extend existing
  reactors / no closures, P3 reduce fossil fuels by electrifying, P4 vote a programming law based on the
  Grémillet bill.
- Result: 53 proposed matches out of 150 scrutins, average confidence 0.66, 0 batches skipped. P1: 35,
  P2: 9, P3: 7, P4: 2. No match on the hydroelectricity bill and none on the wind/solar moratorium
  amendments, because the Sfen paper takes no position on them. You can disagree on the Validation page.
- **Titles-only comparison not done**: in manual mode it would mean answering 8 more batches by hand.
  Note that the same Claude answered with the exposés in view, so a titles-only run by the same judge would
  not be blind anyway.
- Switching back to the API later: set `LLM_PROVIDER=anthropic` and the key in `.env`. The cache keys
  include the provider, so the API would recompute everything instead of reusing the manual answers.

## Scoring and Classement (task 6, build step 4)

- `scoring.py`: plain pandas, about 1 s. Thresholds are constants at the top (`MIN_VOTES=5`, `SEUIL_ALLIE=70`,
  `SEUIL_OPPOSANT=30`). A theme can override them in theme.json with `"scoring": {...}`.
- Only `accepte` / `inverse` decisions with a `vote_retenu` count.
- **Absence = in office on the date of the scrutin, but non-votant or no vote recorded.** For this I added a
  `mandats` table (depute_id, debut, fin) from AMO20. Some députés have two periods. Former députés are not
  counted absent after they left. Abstentions and absences are shown, never in the score.
- The "s'écarte de son groupe" rule is **not implemented yet**: it belongs to build step 5 (Fiche député).
- Classement page: label counts, filters (group, label, name, include former députés), score bar, and below it
  "Votes derrière un score", which lists every accepted scrutin for the chosen député with how it counted
  and a link to the scrutin. Results are cached per theme and refresh when validated.json changes.
- Result for nucleaire (574 current députés, 51 scrutins): 125 allié, 109 opposant, 65 à convaincre,
  **275 données insuffisantes**. Most séance votes on amendments are attended by few députés: the median
  député cast 6 pour/contre votes on these 51 scrutins.
- Group averages: DR 89, UDR 86, RN 86, HOR 73, LIOT 69, DEM 51, EPR 48, GDR 47, SOC 24, LFI 6, ECOS 6.
  EPR (pro-nuclear government camp) is only 48 because many accepted scrutins are pro-nuclear amendments
  from RN/DR that the majority voted down for tactical reasons. That is what the votes say, but it is worth
  explaining in the demo.
- Performance note: the SQL join of mandats × votes took 100 s in SQLite (bad plan). The join is done in pandas.

## Fiche député and "s'écarte de son groupe" (task 7, build step 5)

- Rule in `scoring.py` (`ECART_GROUPE = 20`, overridable in theme.json `scoring.ecart_groupe`): group average =
  mean score of the group's **current** members who have a score. A député with a score 20+ points away from
  it gets "à convaincre" with the note "s'écarte de son groupe", whatever the score. Group = `deputes.groupe`
  (current group). "Non inscrit" is not a group, so the rule doesn't apply to them.
- nucleaire: 17 current députés flagged (e.g. EPR members at 71–78 vs EPR average 48, RN members at 57–62 vs 86).
  Labels now: 121 allié, 101 opposant, 77 à convaincre, 275 données insuffisantes.
- Fiche député page: identity, link to the député's page on assemblee-nationale.fr, score, label, group
  average, the warning when the rule applies, counts, and every accepted scrutin with wanted vote, their vote,
  how it counted, the reason and the scrutin link. Opened from Classement with "Ouvrir la fiche du député"
  (sets `st.session_state["page"]`), or directly from the sidebar.
- Classement table has a new "Note" column.

## Four visual styles (task 8)

- `styles.py`: 4 light styles (later cut to the 2 the user preferred: "Papier et vermillon" and "Vert-de-gris et paon") inspired by Sanzo Wada's *A Dictionary of Color Combinations* (hex values are
  approximations from his named colours, not exact plates): "Papier et vermillon", "Bleu de Prusse",
  "Rose camée et sienne", "Vert-de-gris et paon". Each sets background, surfaces, text, accent, fonts
  (Google Fonts) and the three label colours. "Apparence" selector at the top of the sidebar, with a swatch strip.
- `.streamlit/config.toml` sets a light base theme: data tables are drawn by Streamlit, not by CSS, so they follow
  this config, not the chosen style. That is why all four styles are light.
- Label pills (`.pastille`) on the Fiche député. Tables still use emoji circles: their cells can't take CSS.
- "Scrutin" and "Raison" columns widened to 420 px.
- Final choice: "Vert-de-gris et paon", made darker (deep sage background, dark green sidebar). It is now the
  only look (`styles.DEFAUT`), with no selector. `.streamlit/config.toml` tints the tables pale green to match.
  "Papier et vermillon" stays in styles.py for reference.

## Accueil page (task 9, build step 6)

- First page of the app: pitch line, the theme's position paper in a text area with "Analyser le document",
  the extracted positions, the "validés / non validés" banner, the three lists (top 10 current députés each,
  every name opens their Fiche), and a "Comment ça marche" section with two tabs: user side and technical side.
- **Pasting a different paper does not run an analysis** on this page. It shows a message pointing to the
  Validation page. Reason: no API credits (manual provider), and `matching.run()` would overwrite the theme's
  matching.json, which validated.json refers to. Live analysis of a new paper would need a key, plus results
  stored per document. Not done.
- Ordering of the lists: alliés by score then number of votes; opposants by lowest score; à convaincre by
  distance **above** the group average (most persuadable first: e.g. EPR members at 71–78 vs group 48).
- Spec quirk worth knowing: "s'écarte de son groupe" applies "whatever the score", so a député 20+ points
  *below* their group is also "à convaincre" (e.g. a SOC député at 4 vs group 24). The label follows CLAUDE.md;
  only the Accueil ordering pushes those cases down.
