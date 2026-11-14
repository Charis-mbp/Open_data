# Démo : Boussole parlementaire (environ 3 minutes)

Avant : `.venv/bin/streamlit run app.py`, navigateur en plein écran, page **Accueil** ouverte.
Thème : Nucléaire et énergie. Document : note de la Sfen sur la PPE (février 2026).

## 1. Accueil (45 s)

- Lire la phrase du haut : « Collez le document de position d'une organisation… »
- Montrer la note de la Sfen dans le cadre, puis ouvrir « Positions extraites » :
  « Le modèle en a tiré 4 positions, chacune appuyée sur une citation du texte. »
- Montrer les trois colonnes : alliés, à convaincre, opposants.
  « 121 alliés, 69 à convaincre, 109 opposants. 275 députés n'ont pas assez de votes sur ces scrutins
  pour être classés : on ne les invente pas. »

## 2. Fiche député (60 s)

- Cliquer **Natalia Pouzyreff** en tête de la colonne « À convaincre ».
- « Elle est à 78, son groupe EPR est à 48 : elle s'écarte de son groupe. C'est une porte d'entrée. »
- Descendre au tableau « Les votes derrière le score » :
  « Chaque ligne est un vrai vote. Elle a voté contre les trajectoires de sortie du nucléaire, comme le voulait
  la Sfen… mais contre l'ensemble de la loi Grémillet, avec son groupe. Voilà le sujet du rendez-vous. »
- Cliquer **Voir le scrutin** sur une ligne : la page officielle de l'Assemblée s'ouvre. « Tout est vérifiable. »

## 3. Classement (30 s)

- Page **Classement**, filtrer Groupe = « Ensemble pour la République ».
- « On voit d'un coup qui, dans un groupe, est proche de vos positions. Colonne Note : ceux qui s'écartent. »
- Une phrase sur EPR à 48 : « Camp pro-nucléaire, mais la majorité a souvent rejeté les amendements
  pro-nucléaires de l'opposition. La Boussole compte les votes, pas les intentions. »

## 4. Validation (30 s)

- Page **Validation des scrutins**, vue « Acceptés », ouvrir une carte d'amendement.
  « Le modèle a lu l'exposé de l'amendement et propose le vote que la Sfen aurait voulu. Une personne accepte,
  inverse ou rejette. Le modèle propose, l'humain décide, et le score est un simple calcul. »

## 5. Coulisses (15 s, si le temps le permet)

- **Shortlist** : « Sur 9 895 scrutins, 150 touchent le thème et sont vraiment disputés. »
- **Scrutins** : chercher « Grémillet »… rien : le nom n'apparaît pas dans les données. Chercher
  « programmation nationale » : 207 scrutins. « On travaille sur les données brutes de l'Assemblée. »

## Conclusion (10 s)

« Une carte vérifiable de l'Assemblée sur votre dossier, en quelques minutes. Un nouveau thème, c'est un
nouveau dossier : santé, agriculture, numérique. »

## Si on vous demande

- **Et un autre document ?** L'analyse d'un nouveau document passe par le modèle puis par une validation
  humaine (une dizaine de minutes de relecture). La démo montre le résultat complet sur la note de la Sfen.
- **Le modèle peut se tromper ?** Oui, c'est pour ça qu'une personne valide chaque scrutin et que chaque vote est lié
  à sa source. Le modèle ne produit jamais de score.
- **Pourquoi 275 non classés ?** Les votes sur amendements réunissent peu de députés en séance. Moins de 5 votes
  pour ou contre : pas de score.
