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

## Two user decisions (task 10)

- "S'écarte de son groupe" now applies only to députés **20+ points above** their group average (CLAUDE.md
  updated with the decision). 4 current députés flagged (EPR/DEM members at 71–78). Labels: 121 allié,
  109 opposant, 69 à convaincre, 275 données insuffisantes.
- New "🐴 cheval de Troie" flag for ambiguous decisions: the text voted and the author's intent point opposite
  ways. Checkbox on accepted Validation cards. Stored as `"ambigu": true` on the entry in validated.json (entry
  update, backup first). Still counted in the score, shown in the "Signal" column of every votes table.
  n° 2433 is flagged: the dispositif only adds a −50 % / 2050 climate target, while the exposé argues against
  new reactors. It stays "contre", by user decision.

## Hémicycle and the "Prochain vote" page (task 11), in progress

- **No public documentation found.** hemicycle.ai is a web app (it has a `/predictions` page) backed by
  `atlas.hemicycle.ai`, which serves the same HTML page for every path, so its API routes can't be found from
  outside. The key was never sent to a guessed address. **Needed from the user:** base URL, path of the
  per-député prediction, auth header, the id of an upcoming scrutin, and one sample response.
- `hemicycle.py`: the only client. It reads HEMICYCLE_API_KEY / HEMICYCLE_BASE_URL / HEMICYCLE_PREDICTION_PATH
  (with `{scrutin}`) / HEMICYCLE_AUTH_HEADER from .env, caches every response in
  `themes/<t>/hemicycle_cache/`, never raises, and logs to data/hemicycle.log. The response parser is tolerant
  (list, or dict with predictions/deputes/votes/data; id via acteurRef/uid/id, or name) and is to be tightened
  once a real response is seen.
- There was **no existing simulation**, so I wrote one in `scoring.simulation()`. A current député who cast
  pour/contre/abstention on under 20 % of the theme's validated scrutins in office → absent; otherwise the
  wanted vote if score (or else group average) ≥ 50, the opposite below. `scoring.raison()` builds the reason
  sentence (score, number of votes, group average, label, "s'écarte de son groupe").
- `theme.json` → `prochain_vote`: title, date ("à confirmer": not invented), wanted vote, position,
  `ref_hemicycle` (empty until known). nucleaire: next reading of the Grémillet bill, wanted "pour" (P4).
- "Prochain vote" page (2nd in the sidebar): predicted or simulated totals; "À rencontrer" = predicted against
  the organisation with past score ≥ 40 (`SEUIL_A_RENCONTRER`), highest first; "Alliés à mobiliser" = alliés
  predicted to abstain or be absent; button to open a Fiche. With no Hémicycle data, it shows the simulation and
  a short French message saying why. Tested: not configured, configured but unreachable. No crash.
- Simulation today: 138 pour, 114 contre, 322 absent; 12 to meet, 15 alliés to mobilise.

## Hémicycle loyalty and fiches (task 12)

- **Calls made** (Hémicycle MCP server): `loyaute_deputes` once per group, legislature 17, `limite=100`: 11 groups,
  55 credits. Non-inscrits are excluded by Hémicycle. Running the calls in parallel led to 422s and 429s (not
  billed), so I re-ran them one at a time. `lire_acteur` for the 30 députés shown in the three Accueil lists of
  `nucleaire` (default theme; `sante` has no validated matches yet, so its lists are empty): 30 credits.
  Total spent: 85 credits.
- **Cache**: `data/hemicycle/loyaute_<SIGLE>.json` and `data/hemicycle/acteurs/<id>.json`. These are trimmed copies,
  not the raw responses, which were too large to keep in full. Names are dropped from the loyalty files (they are
  in the DB). The fiche mandates list is cut to the current permanent commission and the current role.
  `data/` is gitignored, so **these files are not committed**: keep them, or the calls must be run again.
- **Coverage**: 527 of 574 current députés have a loyalty figure. RN has 133 members and the call returns at most
  100, so its 33 most loyal members are missing. They can't be flagged, which is the right result anyway.
  A député listed under two groups (e.g. Fruchon: LIOT and DR) keeps the entry of their current group.
- **New rule** (`scoring.py`): "s'écarte de son groupe" = Hémicycle loyalty ≥ `ECART_LOYAUTE` (5) points below the
  group median **and** theme score above the group average. I kept the second condition so the "only more
  favourable than the group" decision from earlier today still holds. Loyalty alone has no direction.
  5 points is my choice: depending on the group, the median sits between 90 % (LIOT) and 99 % (LFI, RN), and
  5 points picks out the clear outliers.
- **Effect on nucleaire**: 8 flagged, down from 4 under the old rule. The old 4 (Pouzyreff, Melchior, Fesneau,
  Riotton) are no longer flagged: they are loyal overall. Now flagged: Ménagé and Dussausaye (RN, 92 and 87 vs
  group 86), Lam and Brard (HOR), Daubié and Brocard (DEM), Brulebois and L. Tanguy (EPR). Totals per label
  are unchanged (121/109/69/275) because 4 alliés moved to à convaincre in both versions.
  **Worth a look**: Dussausaye is 1 point above his group on the theme and RN votes very much as a block, so his
  "à convaincre" rests on his overall loyalty, not on nuclear.
- **Fiche député**: framed box with profession, commission (name from the local AMO organe files, since Hémicycle
  only gives the code), role, HATVP link, and loyalty vs group median. Caption credits Hémicycle and the AN
  open-data licence. Loyalty shows for anyone with a figure; the fiche part only for the 30 cached députés.
- Hémicycle's `lire_acteur` returns at most 50 mandates, newest first, so the first election date and the number
  of terms can't be read reliably. I left them out.
- DEMO.md, HANDOFF.md and prospectus.html still describe the 20-point rule. Not touched (outside this task).

## Demo database, stricter group rule, docs (task 13)

- `make_demo_db.py` → `data/boussole_demo.db`, 2.5 MB: 150 scrutins, 22 848 votes, 655 députés, 14 groupes.
  On top of the tables asked for, I also copied **mandats** (684 rows; scoring needs the mandate periods) and
  the **149 amendements** of those scrutins plus their parents (matching reads the exposé). Without them the
  app breaks on the demo DB. `shortlist.DB_PATH` uses `boussole.db` if present, else the demo copy, and
  `app.py` imports it from there. All 7 pages run on the demo DB with identical figures. On the demo DB, the
  Scrutins page says that only the shortlisted scrutins are loaded.
- `.gitignore`: `data/` → `data/*` with exceptions for `data/boussole_demo.db` and `data/hemicycle/`.
- Rule: `ECART_GROUPE = 10`, so the theme score must be at least 10 points above the group average, on top of
  the loyalty condition. 2 remain: Daubié (DEM, 61 vs 51) and Brulebois (EPR, 60 vs 48, only 5 votes).
  Labels: 125 allié, 109 opposant, 65 à convaincre, 275 insuffisant. All 30 Accueil députés still have a fiche.
- Docs: the demo example is now **Daubié**, not Pouzyreff: he has 23 votes, sits on the economic affairs
  committee, and is 10th in the À convaincre column. Brulebois was too thin, with 5 votes. The prospectus
  counters were partly stale before this task (101 opposants), and are now fixed. HANDOFF.md rewritten
  (GitHub remote, demo DB, Hémicycle). README.md added.

## Dark, animated redesign (task 14)

- New style "Nuit et cuivre" in `styles.py`, now the default (the two light styles are kept for reference).
  `.streamlit/config.toml` switched to a dark base so tables and charts match.
- Animations are CSS only (no new dependency): blocks slide in on load, compass needle swings in the header,
  counters count up, label bar and score ring fill, hover lift on cards and buttons. Disabled under
  "reduced motion".
- New visuals: counters + stacked label bar (Accueil, Classement), score-by-group dot chart with Altair
  (Classement, ships with Streamlit, added to requirements.txt), score ring (Fiche député), coloured
  column headers on Accueil.
- The counters' count-up uses CSS `@property`: works in Chrome/Edge/Firefox 128+; older browsers show the final number.
- `themes/sante/` is empty, so only `nucleaire` appears in the selector (unchanged by this task).

## Redesign step 1: "Encre et cuivre" look and the new Accueil (task 14)

- `styles.py` rewritten: one palette (ink, hairlines, copper only on the wordmark dot and the primary button,
  three label colours), Bricolage Grotesque / IBM Plex Sans / IBM Plex Mono. Earlier gimmicks removed:
  gradient title, glows, slide-in blocks, pulsing pills, lifting cards. The compass logo is replaced by a
  "Cleon" wordmark (sidebar and page header). Helpers still used by other pages (compteurs, repartition,
  jauge, entete) are kept but drawn flat. `.streamlit/config.toml` follows the new palette.
- Navigation stays in the sidebar, as CLAUDE.md asks; the prototype's top bar is not used.
- Accueil, built from live data: hero (question, document form, hemicycle), then five sections, each opened
  by a "cut" (a ruled strip with the section name and one fact): positions with their quotes and validated
  counts, group averages drawn to scale with the 30/70 thresholds, the three lists (top 10, buttons that open
  the fiche), entry-point cards for the "s'écarte de son groupe" députés, the method, and an expander with the
  technical notes.
- Hemicycle: `styles.hemicycle_svg()`, 574 seats on 11 rows, groups as wedges left to right (`ORDRE_GROUPES` in
  app.py; a group not in the list sits just before NI), best scores on the inner rows. Static; each seat's
  tooltip gives name, group and score. The prototype's group highlight on hover is not done.
- Removed: PITCH and COMMENT_UTILISATEUR (replaced by the hero and the method section).
- Checked: all 7 pages run with no error (AppTest). No screenshot: headless Firefox hangs on Streamlit.

## Redesign step 2: Classement and Fiche député (task 15)

- Shared helpers in `styles.py`: `tete_page` (mono label, big title, one paragraph), `encart` (side box with
  term/definition rows and a source line), `metriques` (ruled row of big mono figures). `bandeau_validation`
  is now a mono info line.
- Emoji removed from labels, vote categories and the "cheval de Troie" flag (plain text). The Altair cloud
  uses the new palette and fonts.
- Classement: page head, search, filters, label counters; then a "Le nuage" section and a "Le tableau" section.
  Clicking a row of the table opens that député's fiche (`on_select` callback). The old "Votes derrière un
  score" selector at the bottom is gone: the fiche shows those votes, so every score still links to its votes.
- Fiche député: page head with name, group, circonscription, AN link and label badges; the député selector sits
  top right. "Thème" section: score, group average and aligned/opposed as big figures, the
  "s'écarte de son groupe" explanation when it applies, and the Hémicycle box on the right (now shows
  "non mesurée" when loyalty is missing). Then "Les votes derrière le score" with the table.
- Checked with AppTest: all pages run; Daubié's fiche has the alert, Girard's does not. The row click cannot be
  simulated in AppTest; check it by hand.

## Redesign step 3: Prochain vote, Validation, Scrutins, Shortlist (task 16)

- Every page now opens with `styles.tete_page` and separates sections with `styles.coupe`.
- Prochain vote: the short bill name as title, the full title and wanted vote under it; the simulation notice is
  a quiet side-ruled line instead of a yellow warning; pour / contre / abstention / absent as big figures
  (wanted vote green, opposite red) over a stacked bar; "À rencontrer" and "Alliés à mobiliser" each in their
  own section. Clicking a row opens the fiche (same callback as Classement, now generic), so the selector at
  the bottom is gone.
- Validation: figures for accepted / rejected / not validated; each card has a mono header line (number, date,
  position) with a status badge (accepté, accepté vote inversé, rejeté, non validé) instead of emoji, the
  scrutin title as a link, the position, the proposed vote in large type, a confidence bar and the model's reason.
  Amendment exposé, ambiguity checkbox and the three buttons are unchanged.
- Shortlist: three figures (with a keyword, after filters, kept), then the table and the per-group detail as
  sections. Scrutins: page head with the count; the demo-database note moved into the head.
- Checked with AppTest: all 7 pages run; the "Acceptés" view shows 51 cards (50 accepted, 1 inverted).
