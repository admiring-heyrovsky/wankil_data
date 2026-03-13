# Wankil Studio — Dashboard de statistiques

Tableau de bord interactif construit avec **Streamlit** pour explorer les vidéos YouTube de [Wankil Studio - Laink et Terracid](https://www.youtube.com/@WankilStudio).

---

## Structure du projet

```
wankil_data/
├── stats.py                  # Application Streamlit principale
├── wankil_analyse.csv        # Métadonnées des vidéos
└── transcription_output/     # Transcriptions JSON (une par vidéo)
    └── <video_id>_transcription.json
```

### `wankil_analyse.csv`

Chaque ligne correspond à une vidéo avec les colonnes suivantes :

| Colonne        | Description                                  |
|----------------|----------------------------------------------|
| `analyse`      | `true` si la vidéo a été transcrite          |
| `title`        | Titre de la vidéo                            |
| `url`          | URL YouTube                                  |
| `id`           | Identifiant YouTube (ex: `S3lfYNzTsnI`)      |
| `duration`     | Durée en secondes                            |
| `uploader`     | Nom de la chaîne                             |
| `upload_date`  | Date de mise en ligne (`YYYY-MM-DD`)         |
| `view_count`   | Nombre de vues                               |
| `thumbnail`    | URL de la miniature                          |

### `transcription_output/`

Fichiers JSON générés par un modèle de transcription automatique (style Whisper). Chaque fichier contient :
- `text` : transcription complète de la vidéo
- `segments` : liste de segments horodatés (`start`, `end`, `text`)

---

## Lancer l'application

```bash
pip install -r requirements.txt
streamlit run stats.py
```

---

## Métriques calculées

Avant l'affichage, plusieurs colonnes dérivées sont calculées à partir du CSV :

| Métrique           | Formule                                      | Utilité                                                              |
|--------------------|----------------------------------------------|----------------------------------------------------------------------|
| `duration_min`     | `duration / 60`                              | Durée en minutes, plus lisible                                       |
| `views_per_min`    | `view_count / duration_min`                  | "Efficacité" : vues ramenées à la durée                              |
| `age_days`         | `aujourd'hui − upload_date` (min. 1 jour)    | Âge de la vidéo en jours                                            |
| `views_per_day`    | `view_count / age_days`                      | Performance récente, corrige le biais d'ancienneté                  |
| `cumul_views`      | Somme cumulée des vues (ordre chronologique) | Progression globale du catalogue                                     |
| `day_of_week`      | Jour de la semaine de publication            | Analyse des habitudes de publication                                 |

---

## Onglets de l'interface

### 🏆 Tops

Classements des 10 meilleures vidéos selon quatre critères :

- **Vues totales** — le classement brut, favorise naturellement les vidéos les plus anciennes.
- **Durée** — les vidéos les plus longues.
- **Vues par minute** (`view_count / duration_min`) — mesure l'*efficacité* d'une vidéo : à durée égale, laquelle a généré le plus de vues ? Une vidéo courte très virale peut dépasser une longue vidéo populaire.
- **Vues par jour** (`view_count / age_days`) — corrige le biais d'ancienneté. Une vidéo de 2019 avec 2 millions de vues peut avoir moins de dynamique qu'une vidéo de la semaine dernière avec 500k vues. Cette métrique compare les vidéos sur un pied d'égalité indépendamment de leur date de publication.

Un scatter plot **Vues/jour vs Âge** permet de visualiser la distribution de toutes les vidéos et d'identifier les outliers (vidéos exceptionnellement performantes pour leur âge).

---

### 📈 Évolution

Graphiques temporels pour suivre l'évolution du catalogue dans le temps :

- **Vues par vidéo** au fil du temps — détecte les pics de popularité ponctuels.
- **Vues cumulées** — croissance totale de l'audience du catalogue.
- **Durée des vidéos** — permet de voir si le format a évolué (vidéos plus longues, plus courtes).
- **Vues moyennes par mois** — moyenne des vues de toutes les vidéos publiées ce mois-là, pour identifier les mois les plus performants.
- **Cadence de publication** — nombre de vidéos publiées par mois, utile pour repérer les périodes de forte ou faible activité.

---

### 📊 Distributions

Analyses de la répartition globale :

- **Distribution des durées** — histogramme pour voir si les vidéos se concentrent autour d'une durée typique.
- **Distribution des vues** — histogramme révélant l'asymétrie classique des contenus YouTube (quelques vidéos très virales, beaucoup de vidéos "normales").
- **Vues vs Durée (scatter)** — y a-t-il une corrélation entre la longueur d'une vidéo et son succès ?
- **Publications par jour de la semaine** — quel(s) jour(s) Wankil publie-t-il le plus souvent ?
- **Saisonnalité** — toutes années confondues, certains mois de l'année sont-ils plus prolifiques ou plus performants ?

---

### 🔍 Transcriptions

Onglet d'analyse linguistique basé sur les transcriptions automatiques des vidéos.

#### Métriques globales
- Nombre de fichiers transcrits, mots transcrits au total, moyenne par vidéo.
- **Durée de parole réelle** : somme de la durée de tous les segments non vides — distingue le temps effectivement parlé du temps total de la vidéo (musiques, silences...).

#### Mots les plus fréquents

Tous les textes transcrits sont tokenisés (mots de 3 lettres minimum, en minuscules). Une liste de **stopwords français** étendue — articles, pronoms, formes conjuguées des verbes courants (*être*, *avoir*, *faire*, *aller*...), et interjections orales (*euh*, *ouais*, *bah*) — peut être activée pour ne garder que les mots à valeur sémantique réelle. Le résultat est affiché sous forme de graphique en barres horizontales trié par fréquence.

#### Recherche full-text

Recherche d'un mot ou d'une expression dans tous les segments de toutes les vidéos transcrites. Pour chaque résultat :
- Le mot est mis en surbrillance dans le segment.
- Un lien YouTube pointe directement au bon timestamp (`&t=<secondes>`).

Trois graphiques temporels accompagnent les résultats :

| Graphique | Calcul | Pourquoi |
|-----------|--------|----------|
| **Occurrences brutes par mois** | Somme des occurrences dans les vidéos publiées ce mois | Vue brute de la fréquence dans le temps |
| **Occurrences / vidéo** | `occurrences_du_mois ÷ nb_vidéos_transcrites_ce_mois` | Corrige le biais de cadence : un mois avec 10 vidéos n'est pas comparable à un mois avec 3 |
| **Occurrences / 1 000 mots** | `occurrences_du_mois ÷ total_mots_transcrits_ce_mois × 1 000` | Normalisation la plus fine : corrige à la fois le nombre de vidéos *et* leur longueur |

Chaque graphique inclut une **courbe de tendance LOESS** (lissage non-paramétrique, bande passante 0.3) pour dégager la tendance longue derrière le bruit ponctuel.

#### Analyse comparative multi-expressions

Entrez plusieurs expressions (une par ligne) pour les comparer sur les mêmes axes temporels. Des templates prédéfinis sont disponibles :

| Template | Expressions types |
|----------|------------------|
| 🤬 Vulgarité | putain, merde, con, bordel... |
| 💰 Argent | argent, thune, euro, prix... |
| 🏆 Victoire / Défaite | victoire, gagné, perdu, défaite... |
| 😂 Réactions | incroyable, dingue, fou, choqué... |
| 🎮 Gaming | respawn, boss, level, skin, build... |

Les graphiques comparatifs utilisent les mêmes normalisations (÷ vidéos, ÷ 1 000 mots) ainsi qu'un graphique **cumulé** qui somme toutes les expressions pour voir l'évolution globale d'un thème.

---

### 📋 Tableau

Vue tabulaire complète de toutes les vidéos, triées par date décroissante, avec toutes les métriques calculées et des liens cliquables vers YouTube.

---

## Stack technique

| Outil | Rôle |
|-------|------|
| [Streamlit](https://streamlit.io) | Interface web interactive |
| [Pandas](https://pandas.pydata.org) | Manipulation des données |
| [Altair](https://altair-viz.github.io) | Visualisations déclaratives |
| Python stdlib (`json`, `re`, `collections`) | Traitement des transcriptions |
