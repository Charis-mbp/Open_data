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
