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
