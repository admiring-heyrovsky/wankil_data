import json
import os
import re
from collections import Counter

import altair as alt
import pandas as pd
import streamlit as st

CSV_FILE = "wankil_analyse.csv"  # Remplacer par le fichier voulu
TRANSCRIPTION_DIR = "transcription_output"

FRENCH_STOPWORDS = {
    #custom
    "ouais", "suis", "attends", "parce", "euh", "faut", "vraiment",
    # Articles et prépositions
    "le", "la", "les", "de", "du", "des", "un", "une", "et", "en", "à", "au",
    "aux", "par", "sur", "sous", "dans", "avec", "pour", "mais", "ou", "donc",
    "or", "ni", "car",
    # Pronoms
    "il", "ils", "elle", "elles", "je", "tu", "nous", "vous", "on",
    "me", "te", "se", "lui", "y", "ça", "ce", "cet", "cette", "ces",
    "qui", "que", "qu", "quoi", "dont", "où",
    "mon", "ma", "mes", "ton", "ta", "tes", "son", "sa", "ses",
    "notre", "nos", "votre", "vos", "leur", "leurs",
    "moi", "toi", "soi",
    # Négation et adverbes grammaticaux
    "si", "ne", "pas", "plus", "très", "bien", "là", "ici",
    "déjà", "encore", "jamais", "toujours", "peu", "beaucoup",
    "peut", "même", "aussi", "trop", "après", "avant", "alors",
    "tout", "tous", "toute", "toutes", "autre", "autres",
    "ainsi", "donc", "pourtant", "cependant", "quand", "puis",
    "enfin", "lors", "lorsque", "entre", "vers", "sans", "jusqu",
    # Interjections orales
    "oui", "non", "ah", "oh", "bah", "hein", "bon", "ben",
    # Être (toutes formes)
    "est", "sont", "être", "était", "étais", "étaient", "étions", "étiez",
    "sera", "serai", "seras", "serons", "serez", "seront",
    "soit", "soient", "fût", "été",
    # Avoir (toutes formes)
    "ai", "as", "avoir", "avait", "avais", "avaient", "avions", "aviez",
    "aura", "aurai", "auras", "aurons", "aurez", "auront", "ont", "ait", "eu",
    # Faire (toutes formes)
    "fait", "faire", "fais", "faisons", "faites", "font", "faisait",
    "faisais", "faisaient", "fera", "ferai", "feras", "feront",
    # Aller (toutes formes)
    "va", "vais", "vas", "aller", "allons", "allez", "vont",
    "allait", "allais", "allaient", "ira", "irai", "iras", "iront",
    # Dire (toutes formes)
    "dit", "dire", "dis", "disons", "dites", "disent",
    "disait", "disais", "disaient", "dira", "dirai", "diras", "diront",
    # Voir (toutes formes)
    "voit", "voir", "vois", "voyons", "voyez", "voient",
    "voyait", "voyais", "voyaient", "verra", "verrai", "verras", "verront", "vu",
    # Pouvoir (toutes formes)
    "peut", "pouvoir", "peux", "pouvons", "pouvez", "peuvent",
    "pouvait", "pouvais", "pouvaient", "pourra", "pourrai", "pourras", "pourront", "pu",
    # Vouloir (toutes formes)
    "veut", "vouloir", "veux", "voulons", "voulez", "veulent",
    "voulait", "voulais", "voulaient", "voudra", "voudrai", "voudras", "voudront", "voulu",
    # Savoir (toutes formes)
    "sait", "savoir", "sais", "savons", "savez", "savent",
    "savait", "savais", "savaient", "saura", "saurai", "sauras", "sauront", "su",
    # Venir (toutes formes)
    "vient", "venir", "viens", "venons", "venez", "viennent",
    "venait", "venais", "venaient", "viendra", "viendrai", "viendras", "viendront", "venu",
    # Prendre (toutes formes)
    "prend", "prendre", "prends", "prenons", "prenez", "prennent",
    "prenait", "prenais", "prenaient", "prendra", "prendrai", "prendras", "prendront", "pris",
    # Mettre (toutes formes)
    "met", "mettre", "mets", "mettons", "mettez", "mettent",
    "mettait", "mettais", "mettaient", "mettra", "mettrai", "mettras", "mettront", "mis",
    # Partir / aller (toutes formes)
    "part", "partir", "pars", "partons", "partez", "partent",
    "partait", "partais", "partaient", "partira", "partirai", "partiras", "partiront", "parti",
    # Comme / tel
    "comme", "tel", "telle", "tels", "telles",
    # Lettres seules (artefacts de transcription)
    "c", "j", "l", "m", "n", "s", "t", "d", "y",
}


@st.cache_data
def load_transcriptions(transcription_dir: str) -> dict:
    """Charge tous les fichiers JSON de transcription en mémoire (mis en cache)."""
    transcriptions = {}
    if not os.path.isdir(transcription_dir):
        return transcriptions
    for fname in os.listdir(transcription_dir):
        if fname.endswith("_transcription.json"):
            video_id = fname.replace("_transcription.json", "")
            fpath = os.path.join(transcription_dir, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    transcriptions[video_id] = json.load(f)
            except Exception:
                pass
    return transcriptions


def format_time(seconds: float) -> str:
    """Convertit des secondes en HH:MM:SS ou MM:SS."""
    s = int(seconds)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{sec:02d}"
    return f"{m}:{sec:02d}"


def youtube_url_at(base_url: str, seconds: float) -> str:
    return f"{base_url}&t={int(seconds)}"


def compute_normalized_monthly(expression: str, transcriptions: dict, df: pd.DataFrame, case_sensitive: bool = False) -> pd.DataFrame:
    """Retourne un DataFrame avec les occurrences normalisées par mois pour une expression."""
    q = expression if case_sensitive else expression.lower()
    occ_by_video: dict = {}
    for video_id, data in transcriptions.items():
        for seg in data.get("segments", []):
            text = seg.get("text", "").strip()
            if not text:
                continue
            haystack = text if case_sensitive else text.lower()
            if q in haystack:
                occ_by_video[video_id] = occ_by_video.get(video_id, 0) + 1

    if not occ_by_video:
        return pd.DataFrame(columns=["month_date", "occ_par_video"])

    df_v = df[df["id"].isin(occ_by_video)][["id", "upload_date"]].copy()
    df_v["occurrences"] = df_v["id"].map(occ_by_video)
    df_v["month_date"] = df_v["upload_date"].dt.to_period("M").dt.to_timestamp()

    df_monthly_occ = df_v.groupby("month_date")["occurrences"].sum().reset_index()

    df_transcribed_monthly = (
        df[df["id"].isin(transcriptions.keys())]
        .assign(month_date=lambda d: d["upload_date"].dt.to_period("M").dt.to_timestamp())
        .groupby("month_date")
        .size()
        .reset_index(name="nb_videos")
    )

    df_norm = df_monthly_occ.merge(df_transcribed_monthly, on="month_date", how="left")
    df_norm["occ_par_video"] = (df_norm["occurrences"] / df_norm["nb_videos"]).round(3)
    return df_norm[["month_date", "occ_par_video", "occurrences", "nb_videos"]].sort_values("month_date")


# ─────────────────────────────────────────────
st.title("Wankil Studio - Statistiques")

if not os.path.isfile(CSV_FILE):
    st.error(f"Fichier CSV introuvable : `{CSV_FILE}`")
    st.stop()

df = pd.read_csv(CSV_FILE)

# Nettoyage
df["view_count"] = df["view_count"].astype(str).str.replace(",", "").astype(int)
df["duration_min"] = df["duration"] / 60
df["upload_date"] = pd.to_datetime(df["upload_date"], format="%Y-%m-%d")
df["views_per_min"] = df["view_count"] / df["duration_min"]
df["day_of_week"] = df["upload_date"].dt.day_name()
df["month"] = df["upload_date"].dt.to_period("M").astype(str)
df["month_num"] = df["upload_date"].dt.month
_today = pd.Timestamp.today().normalize()
df["age_days"] = (_today - df["upload_date"]).dt.days.clip(lower=1)
df["views_per_day"] = (df["view_count"] / df["age_days"]).round(1)
# La colonne "analyse" peut être string "true"/"false" selon le CSV
df["analyse"] = df["analyse"].astype(str).str.lower() == "true"

df_sorted = df.sort_values("upload_date").reset_index(drop=True)
df_sorted["date_str"] = df_sorted["upload_date"].dt.strftime("%Y-%m-%d")
df_sorted["cumul_views"] = df_sorted["view_count"].cumsum()

# Pré-calculé ici pour ne pas le recalculer à chaque rendu de tab4
id_to_meta = {
    row["id"]: {"title": row["title"], "url": row["url"], "upload_date": row["upload_date"]}
    for _, row in df.iterrows()
}

# ─────────────────────────────────────────────
# Résumé général
st.header("Résumé général")
col1, col2, col3 = st.columns(3)
col1.metric("Vidéos totales", len(df))
nb_transcrites = (df["analyse"] == True).sum()
col2.metric("Transcrites", nb_transcrites)
col2.metric("Pourcentage transcrites", f"{nb_transcrites / len(df) * 100:.1f}%")
col3.metric("Vues totales", f"{df['view_count'].sum():,}")

col4, col5, col6 = st.columns(3)
col4.metric("Durée totale (h)", f"{df['duration'].sum() / 3600:.1f}")
col5.metric("Durée moyenne (min)", f"{df['duration_min'].mean():.1f}")
col6.metric("Vues moyennes / vidéo", f"{df['view_count'].mean():,.0f}")

# ─────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["🏆 Tops", "📈 Évolution", "📊 Distributions", "🔍 Transcriptions", "📋 Tableau"]
)

# ════════════════════════════════════════════
_LINK_COL = st.column_config.LinkColumn("▶", display_text="▶ Ouvrir", width="small")

with tab1:
    st.subheader("Top 10 - Vues")
    top_views = df.nlargest(10, "view_count")[
        ["title", "url", "view_count", "upload_date", "duration_min"]
    ].copy()
    top_views["view_count_fmt"] = top_views["view_count"].apply(lambda x: f"{x:,}")
    top_views["duration_min"] = top_views["duration_min"].round(1)
    st.dataframe(
        top_views[["title", "url", "view_count_fmt", "duration_min", "upload_date"]].rename(
            columns={"view_count_fmt": "vues", "duration_min": "durée (min)"}
        ),
        column_config={"url": _LINK_COL},
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Top 10 - Durée")
    top_duration = df.nlargest(10, "duration")[
        ["title", "url", "duration_min", "upload_date"]
    ].copy()
    top_duration["duration_min"] = top_duration["duration_min"].round(1)
    st.dataframe(
        top_duration.rename(columns={"duration_min": "durée (min)"}),
        column_config={"url": _LINK_COL},
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Top 10 - Vues par minute (efficacité)")
    top_vpm = df.nlargest(10, "views_per_min")[
        ["title", "url", "views_per_min", "view_count", "duration_min", "upload_date"]
    ].copy()
    top_vpm["views_per_min"] = top_vpm["views_per_min"].round(0).astype(int)
    top_vpm["view_count"] = top_vpm["view_count"].apply(lambda x: f"{x:,}")
    top_vpm["duration_min"] = top_vpm["duration_min"].round(1)
    st.dataframe(
        top_vpm.rename(
            columns={
                "views_per_min": "vues/min",
                "view_count": "vues totales",
                "duration_min": "durée (min)",
            }
        ),
        column_config={"url": _LINK_COL},
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Top 10 - Performance récente (vues / jour depuis mise en ligne)")
    st.caption("Corrige le biais d'ancienneté : une vieille vidéo accumule des vues mécaniquement.")
    top_vpd = df.nlargest(10, "views_per_day")[
        ["title", "url", "views_per_day", "view_count", "age_days", "upload_date"]
    ].copy()
    top_vpd["view_count"] = top_vpd["view_count"].apply(lambda x: f"{x:,}")
    st.dataframe(
        top_vpd.rename(
            columns={
                "views_per_day": "vues/jour",
                "view_count": "vues totales",
                "age_days": "âge (jours)",
            }
        ),
        column_config={"url": _LINK_COL},
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Vues par jour vs Âge de la vidéo")
    st.altair_chart(
        alt.Chart(df).mark_circle(size=60, opacity=0.6).encode(
            x=alt.X("age_days:Q", title="Âge (jours)"),
            y=alt.Y("views_per_day:Q", title="Vues / jour"),
            color=alt.Color("analyse:N", title="Transcrite"),
            tooltip=["title", "age_days", "views_per_day", "view_count", "upload_date"],
        ),
        use_container_width=True,
    )

# ════════════════════════════════════════════
with tab2:
    st.subheader("Évolution des vues au fil du temps")
    st.altair_chart(
        alt.Chart(df_sorted).mark_line(point=True).encode(
            x=alt.X("date_str:O", title="Date", sort=None),
            y=alt.Y("view_count:Q", title="Vues"),
            tooltip=["date_str", "title", "view_count"],
        ),
        use_container_width=True,
    )

    st.subheader("Cumul des vues dans le temps")
    st.altair_chart(
        alt.Chart(df_sorted).mark_area(line=True, opacity=0.4).encode(
            x=alt.X("date_str:O", title="Date", sort=None),
            y=alt.Y("cumul_views:Q", title="Vues cumulées"),
            tooltip=["date_str", "title", "cumul_views"],
        ),
        use_container_width=True,
    )

    st.subheader("Évolution de la durée des vidéos (min)")
    st.altair_chart(
        alt.Chart(df_sorted).mark_line(point=True).encode(
            x=alt.X("date_str:O", title="Date", sort=None),
            y=alt.Y("duration_min:Q", title="Durée (min)"),
            tooltip=["date_str", "title", "duration_min"],
        ),
        use_container_width=True,
    )

    st.subheader("Vues moyennes par mois")
    monthly = (
        df.groupby("month")["view_count"]
        .agg(["mean", "sum", "count"])
        .reset_index()
        .rename(columns={"mean": "vues_moy", "sum": "vues_total", "count": "nb_videos"})
    )
    st.altair_chart(
        alt.Chart(monthly).mark_bar().encode(
            x=alt.X("month:O", title="Mois"),
            y=alt.Y("vues_moy:Q", title="Vues moyennes"),
            tooltip=["month", "vues_moy", "vues_total", "nb_videos"],
        ),
        use_container_width=True,
    )

    st.subheader("Cadence de publication (vidéos par mois)")
    pub_cadence = (
        df.groupby("month")
        .size()
        .reset_index(name="nb_videos")
        .sort_values("month")
    )
    st.altair_chart(
        alt.Chart(pub_cadence).mark_bar().encode(
            x=alt.X("month:O", title="Mois", sort=None),
            y=alt.Y("nb_videos:Q", title="Vidéos publiées"),
            color=alt.Color("nb_videos:Q", scale=alt.Scale(scheme="blues"), legend=None),
            tooltip=["month", "nb_videos"],
        ),
        use_container_width=True,
    )

# ════════════════════════════════════════════
with tab3:
    st.subheader("Distribution des durées")
    st.altair_chart(
        alt.Chart(df).mark_bar().encode(
            x=alt.X("duration_min:Q", bin=alt.Bin(maxbins=15), title="Durée (min)"),
            y=alt.Y("count():Q", title="Nombre de vidéos"),
            tooltip=[alt.Tooltip("count():Q", title="Vidéos")],
        ),
        use_container_width=True,
    )

    st.subheader("Distribution des vues")
    st.altair_chart(
        alt.Chart(df).mark_bar().encode(
            x=alt.X("view_count:Q", bin=alt.Bin(maxbins=15), title="Vues"),
            y=alt.Y("count():Q", title="Nombre de vidéos"),
            tooltip=[alt.Tooltip("count():Q", title="Vidéos")],
        ),
        use_container_width=True,
    )

    st.subheader("Vues vs Durée (scatter)")
    st.altair_chart(
        alt.Chart(df).mark_circle(size=80).encode(
            x=alt.X("duration_min:Q", title="Durée (min)"),
            y=alt.Y("view_count:Q", title="Vues"),
            color=alt.Color("analyse:N", title="Transcrite"),
            tooltip=["title", "duration_min", "view_count", "upload_date"],
        ),
        use_container_width=True,
    )

    st.subheader("Publications par jour de la semaine")
    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    day_counts = (
        df["day_of_week"]
        .value_counts()
        .reindex(day_order, fill_value=0)
        .reset_index()
        .rename(columns={"day_of_week": "jour", "count": "nb_videos"})
    )
    st.altair_chart(
        alt.Chart(day_counts).mark_bar().encode(
            x=alt.X("jour:O", sort=day_order, title="Jour"),
            y=alt.Y("nb_videos:Q", title="Vidéos publiées"),
            tooltip=["jour", "nb_videos"],
        ),
        use_container_width=True,
    )

    st.subheader("Saisonnalité (par mois de l'année, toutes années confondues)")
    _MONTH_FR = {1:"Jan",2:"Fév",3:"Mar",4:"Avr",5:"Mai",6:"Juin",
                 7:"Juil",8:"Août",9:"Sep",10:"Oct",11:"Nov",12:"Déc"}
    _month_order = list(_MONTH_FR.values())
    df_season = df.copy()
    df_season["month_name"] = df_season["month_num"].map(_MONTH_FR)
    seasonality = (
        df_season.groupby(["month_num", "month_name"])
        .agg(vues_moy=("view_count", "mean"), nb_videos=("view_count", "count"))
        .reset_index()
        .sort_values("month_num")
    )
    seasonality["vues_moy"] = seasonality["vues_moy"].round(0).astype(int)

    col_s1, col_s2 = st.columns(2)
    with col_s1:
        st.caption("Vues moyennes par mois de l'année")
        st.altair_chart(
            alt.Chart(seasonality).mark_bar().encode(
                x=alt.X("month_name:O", sort=_month_order, title="Mois"),
                y=alt.Y("vues_moy:Q", title="Vues moyennes"),
                color=alt.Color("vues_moy:Q", scale=alt.Scale(scheme="blues"), legend=None),
                tooltip=["month_name", "vues_moy", "nb_videos"],
            ),
            use_container_width=True,
        )
    with col_s2:
        st.caption("Nombre de vidéos publiées par mois de l'année")
        st.altair_chart(
            alt.Chart(seasonality).mark_bar().encode(
                x=alt.X("month_name:O", sort=_month_order, title="Mois"),
                y=alt.Y("nb_videos:Q", title="Vidéos publiées"),
                color=alt.Color("nb_videos:Q", scale=alt.Scale(scheme="oranges"), legend=None),
                tooltip=["month_name", "nb_videos", "vues_moy"],
            ),
            use_container_width=True,
        )

# ════════════════════════════════════════════
with tab5:
    st.subheader("Toutes les vidéos")
    display_df = df[
        ["analyse", "title", "url", "upload_date", "view_count", "duration_min", "views_per_min", "views_per_day"]
    ].copy()
    display_df["view_count"] = display_df["view_count"].apply(lambda x: f"{x:,}")
    display_df["duration_min"] = display_df["duration_min"].round(1)
    display_df["views_per_min"] = display_df["views_per_min"].round(0).astype(int)
    st.dataframe(
        display_df.rename(
            columns={
                "duration_min": "durée (min)",
                "views_per_min": "vues/min",
                "view_count": "vues",
                "views_per_day": "vues/jour",
            }
        ).sort_values("upload_date", ascending=False),
        column_config={"url": _LINK_COL},
        use_container_width=True,
        hide_index=True,
    )

# ════════════════════════════════════════════
with tab4:
    transcriptions = load_transcriptions(TRANSCRIPTION_DIR)

    if not transcriptions:
        st.warning(f"Aucun fichier de transcription trouvé dans `{TRANSCRIPTION_DIR}/`.")
    else:
        nb_trans_files = len(transcriptions)

        # ── Métriques globales ──────────────────────────────────────
        total_words = sum(
            len(t.get("text", "").split()) for t in transcriptions.values()
        )
        avg_words = total_words / nb_trans_files if nb_trans_files else 0

        # Durée de parole réelle (somme des segments non vides)
        total_speech_sec = 0.0
        for t in transcriptions.values():
            for seg in t.get("segments", []):
                if seg.get("text", "").strip():
                    total_speech_sec += seg["end"] - seg["start"]

        col1, col2, col3 = st.columns(3)
        col1.metric("Fichiers transcrits", nb_trans_files)
        col2.metric("Mots transcrits (total)", f"{total_words:,}")
        col3.metric("Mots / vidéo (moy.)", f"{avg_words:,.0f}")

        col4, col5 = st.columns(2)
        col4.metric("Durée de parole totale (h)", f"{total_speech_sec / 3600:.1f}")
        col5.metric("Durée de parole / vidéo (min)", f"{total_speech_sec / 60 / nb_trans_files:.1f}")

        # Pré-calcul : mots totaux transcrits par mois (pour normalisation / 1000 mots)
        _wm: dict = {}
        for _vid_id, _data in transcriptions.items():
            _meta = id_to_meta.get(_vid_id)
            if _meta is None:
                continue
            _md = _meta["upload_date"].to_period("M").to_timestamp()
            _wm[_md] = _wm.get(_md, 0) + len(_data.get("text", "").split())
        df_words_monthly = pd.DataFrame(
            [{"month_date": k, "total_words": v} for k, v in _wm.items()]
        )

        st.divider()

        # ── Mots les plus fréquents ─────────────────────────────────
        st.subheader("Mots les plus fréquents")

        col_a, col_b = st.columns(2)
        top_n = col_a.slider("Nombre de mots à afficher", 10, 50, 30, step=5)
        filter_stops = col_b.checkbox("Filtrer les mots courants", value=True)

        word_counter: Counter = Counter()
        for data in transcriptions.values():
            raw = data.get("text", "")
            tokens = re.findall(r"\b[a-zA-ZÀ-ÿ]{3,}\b", raw.lower())
            if filter_stops:
                tokens = [w for w in tokens if w not in FRENCH_STOPWORDS]
            word_counter.update(tokens)

        top_words = word_counter.most_common(top_n)
        if top_words:
            df_words = pd.DataFrame(top_words, columns=["mot", "occurrences"])
            st.altair_chart(
                alt.Chart(df_words).mark_bar().encode(
                    x=alt.X("occurrences:Q", title="Occurrences"),
                    y=alt.Y("mot:N", sort="-x", title=None),
                    color=alt.Color("occurrences:Q", scale=alt.Scale(scheme="blues"), legend=None),
                    tooltip=["mot", "occurrences"],
                ),
                use_container_width=True,
            )

        # ── Recherche full-text ─────────────────────────────────────
        st.subheader("🔍 Recherche dans les transcriptions")

        query = st.text_input(
            "Mot ou expression à rechercher",
            placeholder="ex: Pokémon, minecraft, putain...",
        )
        case_sensitive = st.checkbox("Sensible à la casse", value=False)
        max_results = st.slider("Résultats max", 5, 100, 20, step=5)

        if query:
            q = query if case_sensitive else query.lower()
            results = []
            for video_id, data in transcriptions.items():
                for seg in data.get("segments", []):
                    text = seg.get("text", "").strip()
                    if not text:
                        continue
                    haystack = text if case_sensitive else text.lower()
                    if q in haystack:
                        meta = id_to_meta.get(video_id, {})
                        results.append(
                            {
                                "video_id": video_id,
                                "title": meta.get("title", video_id),
                                "url": meta.get("url", f"https://www.youtube.com/watch?v={video_id}"),
                                "upload_date": meta.get("upload_date", pd.Timestamp.min),
                                "start": seg["start"],
                                "end": seg["end"],
                                "text": text,
                            }
                        )
            results.sort(key=lambda r: (r["upload_date"], r["start"]))

            st.markdown(
                f"**{len(results)} occurrence(s)** trouvée(s)"
                + (f" — affichage des {max_results} premières" if len(results) > max_results else "")
            )

            # ── Graphique : occurrences au fil du temps ─────────────
            if results:
                # Compte les occurrences par vidéo et joint avec la date
                occ_by_video = {}
                for r in results:
                    occ_by_video[r["video_id"]] = occ_by_video.get(r["video_id"], 0) + 1

                df_occ = (
                    df[df["id"].isin(occ_by_video)]
                    [["id", "title", "upload_date"]]
                    .copy()
                )
                df_occ["occurrences"] = df_occ["id"].map(occ_by_video)
                df_occ["date_str"] = df_occ["upload_date"].dt.strftime("%Y-%m-%d")
                df_occ["title_short"] = df_occ["title"].str[:50] + df_occ["title"].apply(lambda t: "…" if len(t) > 50 else "")
                df_occ = df_occ.sort_values("upload_date")

                st.altair_chart(
                    alt.Chart(df_occ).mark_bar().encode(
                        x=alt.X("date_str:O", title="Date", sort=None),
                        y=alt.Y("occurrences:Q", title="Occurrences"),
                        tooltip=["date_str", "title_short", "occurrences"],
                    ),
                    use_container_width=True,
                )

                # Courbe d'évolution : agrégation par mois
                df_occ["month_date"] = df_occ["upload_date"].dt.to_period("M").dt.to_timestamp()
                df_monthly = (
                    df_occ.groupby("month_date")["occurrences"]
                    .sum()
                    .reset_index()
                    .rename(columns={"occurrences": "occurrences_mois"})
                    .sort_values("month_date")
                )
                base_m = alt.Chart(df_monthly)
                line_m = base_m.mark_line(color="#4c78a8", strokeWidth=1.5, opacity=0.5).encode(
                    x=alt.X("month_date:T", title="Mois"),
                    y=alt.Y("occurrences_mois:Q", title="Occurrences"),
                    tooltip=[alt.Tooltip("month_date:T", title="Mois", format="%Y-%m"), "occurrences_mois"],
                )
                points_m = base_m.mark_circle(size=60, color="#4c78a8", opacity=0.6).encode(
                    x=alt.X("month_date:T"),
                    y=alt.Y("occurrences_mois:Q"),
                    tooltip=[alt.Tooltip("month_date:T", title="Mois", format="%Y-%m"), "occurrences_mois"],
                )
                loess_m = base_m.mark_line(color="orange", strokeWidth=2.5).transform_loess(
                    "month_date", "occurrences_mois", bandwidth=0.3
                ).encode(
                    x=alt.X("month_date:T"),
                    y=alt.Y("occurrences_mois:Q"),
                )
                # Graphiques côte à côte
                col_left, col_right = st.columns(2)

                with col_left:
                    st.caption("Occurrences brutes par mois — bleu : données, orange : tendance lissée (LOESS)")
                    st.altair_chart((line_m + points_m + loess_m).properties(height=300), use_container_width=True)

                # Graphique normalisé : occurrences / nb vidéos transcrites publiées ce mois
                df_transcribed_monthly = (
                    df[df["id"].isin(transcriptions.keys())]
                    .assign(month_date=lambda d: d["upload_date"].dt.to_period("M").dt.to_timestamp())
                    .groupby("month_date")
                    .size()
                    .reset_index(name="nb_videos")
                )
                df_norm = df_monthly.merge(df_transcribed_monthly, on="month_date", how="left")
                df_norm["occ_par_video"] = (df_norm["occurrences_mois"] / df_norm["nb_videos"]).round(2)

                base_n = alt.Chart(df_norm)
                line_n = base_n.mark_line(color="#4c78a8", strokeWidth=1.5, opacity=0.5).encode(
                    x=alt.X("month_date:T", title="Mois"),
                    y=alt.Y("occ_par_video:Q", title="Occurrences / vidéo"),
                    tooltip=[
                        alt.Tooltip("month_date:T", title="Mois", format="%Y-%m"),
                        alt.Tooltip("occ_par_video:Q", title="Occ. / vidéo"),
                        alt.Tooltip("nb_videos:Q", title="Vidéos publiées"),
                    ],
                )
                points_n = base_n.mark_circle(size=60, color="#4c78a8", opacity=0.6).encode(
                    x=alt.X("month_date:T"),
                    y=alt.Y("occ_par_video:Q"),
                    tooltip=[
                        alt.Tooltip("month_date:T", title="Mois", format="%Y-%m"),
                        alt.Tooltip("occ_par_video:Q", title="Occ. / vidéo"),
                        alt.Tooltip("nb_videos:Q", title="Vidéos publiées"),
                    ],
                )
                loess_n = base_n.mark_line(color="orange", strokeWidth=2.5).transform_loess(
                    "month_date", "occ_par_video", bandwidth=0.3
                ).encode(
                    x=alt.X("month_date:T"),
                    y=alt.Y("occ_par_video:Q"),
                )

                with col_right:
                    st.caption("Occurrences normalisées (÷ nb vidéos transcrites ce mois) — tendance corrigée du volume de publication")
                    st.altair_chart((line_n + points_n + loess_n).properties(height=300), use_container_width=True)

                # Graphique normalisé / 1000 mots
                df_norm_1k = df_monthly.merge(df_words_monthly, on="month_date", how="left")
                df_norm_1k["occ_par_1000mots"] = (
                    df_norm_1k["occurrences_mois"] / df_norm_1k["total_words"] * 1000
                ).round(4)

                base_1k = alt.Chart(df_norm_1k)
                line_1k = base_1k.mark_line(color="#4c78a8", strokeWidth=1.5, opacity=0.5).encode(
                    x=alt.X("month_date:T", title="Mois"),
                    y=alt.Y("occ_par_1000mots:Q", title="Occurrences / 1 000 mots"),
                    tooltip=[
                        alt.Tooltip("month_date:T", title="Mois", format="%Y-%m"),
                        alt.Tooltip("occ_par_1000mots:Q", title="Occ. / 1 000 mots"),
                        alt.Tooltip("total_words:Q", title="Mots transcrits ce mois"),
                    ],
                )
                points_1k = base_1k.mark_circle(size=60, color="#4c78a8", opacity=0.6).encode(
                    x=alt.X("month_date:T"),
                    y=alt.Y("occ_par_1000mots:Q"),
                    tooltip=[
                        alt.Tooltip("month_date:T", title="Mois", format="%Y-%m"),
                        alt.Tooltip("occ_par_1000mots:Q", title="Occ. / 1 000 mots"),
                        alt.Tooltip("total_words:Q", title="Mots transcrits ce mois"),
                    ],
                )
                loess_1k = base_1k.mark_line(color="orange", strokeWidth=2.5).transform_loess(
                    "month_date", "occ_par_1000mots", bandwidth=0.3
                ).encode(
                    x=alt.X("month_date:T"),
                    y=alt.Y("occ_par_1000mots:Q"),
                )
                st.caption("Occurrences / 1 000 mots transcrits ce mois — corrige les biais de longueur et de volume")
                st.altair_chart((line_1k + points_1k + loess_1k).properties(height=300), use_container_width=True)

            for r in results[:max_results]:
                yt_link = youtube_url_at(r["url"], r["start"])
                timestamp = format_time(r["start"])
                # Highlight le mot dans le texte
                highlighted = re.sub(
                    re.escape(query),
                    f"**{query}**",
                    r["text"],
                    flags=0 if case_sensitive else re.IGNORECASE,
                )
                with st.expander(f"[{timestamp}] {r['title']}"):
                    st.markdown(highlighted)
                    st.markdown(f"[▶ Ouvrir à {timestamp} sur YouTube]({yt_link})")

        st.divider()

        # ── Analyse comparative multi-expressions ───────────────────
        st.subheader("📊 Analyse comparative")
        st.caption("Entrez une expression par ligne. Le graphique affiche l'évolution normalisée (occurrences / vidéos publiées ce mois) pour chaque expression.")

        _TEMPLATES = {
            "🤬 Vulgarité": (
                "putain\nmerde\ncon\nconnard\nbordel\nchier\nfoutre\nenculé\nsalope\nchiotte"
            ),
            "💰 Argent": (
                "argent\nthune\nfric\nblé\neuro\nprix\nacheter\npayer\ngratuit\nabonnement\nsolde"
            ),
            "🏆 Victoire / Défaite": (
                "victoire\ngagné\ngagne\nperdu\nperd\ndéfaite\nchampio\nnul\néliminé\nremporté"
            ),
            "😂 Réactions": (
                "incroyable\nimpossible\nwaow\nomg\nchoqué\nfou\ndingue\nurgent\nattends\nnon"
            ),
            "🎮 Gaming": (
                "respawn\nboss\nlevel\nskin\ncraft\nbuild\nstream\nnoob\nkill\nspawn\ndamage"
            ),
        }

        if "comparative_input" not in st.session_state:
            st.session_state["comparative_input"] = ""

        st.caption("Templates :")
        _tcols = st.columns(len(_TEMPLATES))
        for _col, (_label, _content) in zip(_tcols, _TEMPLATES.items()):
            if _col.button(_label, use_container_width=True):
                st.session_state["comparative_input"] = _content

        expressions_input = st.text_area(
            "Expressions à comparer (une par ligne)",
            placeholder="putain\nmerde\nwow",
            height=120,
            key="comparative_input",
        )

        expressions = [e.strip() for e in expressions_input.splitlines() if e.strip()]

        if expressions:
            frames = []
            for expr in expressions:
                df_e = compute_normalized_monthly(expr, transcriptions, df)
                if not df_e.empty:
                    df_e["expression"] = expr
                    frames.append(df_e)

            if frames:
                df_compare = pd.concat(frames, ignore_index=True)

                # ── Graphique par expression ────────────────────────
                base_c = alt.Chart(df_compare)
                lines_c = base_c.mark_line(strokeWidth=1.5, opacity=0.5).encode(
                    x=alt.X("month_date:T", title="Mois"),
                    y=alt.Y("occ_par_video:Q", title="Occurrences / vidéo"),
                    color=alt.Color("expression:N", title="Expression"),
                    tooltip=[
                        alt.Tooltip("month_date:T", title="Mois", format="%Y-%m"),
                        alt.Tooltip("expression:N", title="Expression"),
                        alt.Tooltip("occ_par_video:Q", title="Occ. / vidéo"),
                        alt.Tooltip("nb_videos:Q", title="Vidéos ce mois"),
                    ],
                )
                points_c = base_c.mark_circle(size=55, opacity=0.6).encode(
                    x=alt.X("month_date:T"),
                    y=alt.Y("occ_par_video:Q"),
                    color=alt.Color("expression:N"),
                    tooltip=[
                        alt.Tooltip("month_date:T", title="Mois", format="%Y-%m"),
                        alt.Tooltip("expression:N", title="Expression"),
                        alt.Tooltip("occ_par_video:Q", title="Occ. / vidéo"),
                    ],
                )
                loess_c = base_c.mark_line(strokeWidth=2.5).transform_loess(
                    "month_date", "occ_par_video", groupby=["expression"], bandwidth=0.3
                ).encode(
                    x=alt.X("month_date:T"),
                    y=alt.Y("occ_par_video:Q"),
                    color=alt.Color("expression:N"),
                )
                st.altair_chart(
                    (lines_c + points_c + loess_c).properties(height=350),
                    use_container_width=True,
                )

                # ── Graphique normalisé / 1000 mots ────────────────
                df_compare_1k = df_compare.merge(df_words_monthly, on="month_date", how="left")
                df_compare_1k["occ_par_1000mots"] = (
                    df_compare_1k["occurrences"] / df_compare_1k["total_words"] * 1000
                ).round(4)

                base_c1k = alt.Chart(df_compare_1k)
                lines_c1k = base_c1k.mark_line(strokeWidth=1.5, opacity=0.5).encode(
                    x=alt.X("month_date:T", title="Mois"),
                    y=alt.Y("occ_par_1000mots:Q", title="Occurrences / 1 000 mots"),
                    color=alt.Color("expression:N", title="Expression"),
                    tooltip=[
                        alt.Tooltip("month_date:T", title="Mois", format="%Y-%m"),
                        alt.Tooltip("expression:N", title="Expression"),
                        alt.Tooltip("occ_par_1000mots:Q", title="Occ. / 1 000 mots"),
                        alt.Tooltip("total_words:Q", title="Mots transcrits ce mois"),
                    ],
                )
                points_c1k = base_c1k.mark_circle(size=55, opacity=0.6).encode(
                    x=alt.X("month_date:T"),
                    y=alt.Y("occ_par_1000mots:Q"),
                    color=alt.Color("expression:N"),
                    tooltip=[
                        alt.Tooltip("month_date:T", title="Mois", format="%Y-%m"),
                        alt.Tooltip("expression:N", title="Expression"),
                        alt.Tooltip("occ_par_1000mots:Q", title="Occ. / 1 000 mots"),
                    ],
                )
                loess_c1k = base_c1k.mark_line(strokeWidth=2.5).transform_loess(
                    "month_date", "occ_par_1000mots", groupby=["expression"], bandwidth=0.3
                ).encode(
                    x=alt.X("month_date:T"),
                    y=alt.Y("occ_par_1000mots:Q"),
                    color=alt.Color("expression:N"),
                )
                st.caption("Normalisé / 1 000 mots transcrits ce mois — corrige les biais de longueur et de volume de publication")
                st.altair_chart(
                    (lines_c1k + points_c1k + loess_c1k).properties(height=350),
                    use_container_width=True,
                )

                # ── Graphique cumulé ────────────────────────────────
                df_cumul = (
                    df_compare.groupby("month_date")[["occurrences", "nb_videos"]]
                    .first()  # nb_videos identique pour tous les mots ce mois-là
                    .reset_index()
                )
                df_cumul["occ_total"] = df_compare.groupby("month_date")["occurrences"].sum().values
                df_cumul["occ_par_video_cumul"] = (df_cumul["occ_total"] / df_cumul["nb_videos"]).round(3)
                df_cumul = df_cumul.sort_values("month_date")

                base_cum = alt.Chart(df_cumul)
                line_cum = base_cum.mark_line(color="#e45756", strokeWidth=1.5, opacity=0.5).encode(
                    x=alt.X("month_date:T", title="Mois"),
                    y=alt.Y("occ_par_video_cumul:Q", title="Occurrences cumulées / vidéo"),
                    tooltip=[
                        alt.Tooltip("month_date:T", title="Mois", format="%Y-%m"),
                        alt.Tooltip("occ_par_video_cumul:Q", title="Cumul occ. / vidéo"),
                        alt.Tooltip("nb_videos:Q", title="Vidéos ce mois"),
                    ],
                )
                points_cum = base_cum.mark_circle(size=55, color="#e45756", opacity=0.6).encode(
                    x=alt.X("month_date:T"),
                    y=alt.Y("occ_par_video_cumul:Q"),
                    tooltip=[
                        alt.Tooltip("month_date:T", title="Mois", format="%Y-%m"),
                        alt.Tooltip("occ_par_video_cumul:Q", title="Cumul occ. / vidéo"),
                    ],
                )
                loess_cum = base_cum.mark_line(color="#9b0000", strokeWidth=2.5).transform_loess(
                    "month_date", "occ_par_video_cumul", bandwidth=0.3
                ).encode(
                    x=alt.X("month_date:T"),
                    y=alt.Y("occ_par_video_cumul:Q"),
                )
                st.caption(f"Cumul de toutes les expressions : {', '.join(expressions)}")
                st.altair_chart(
                    (line_cum + points_cum + loess_cum).properties(height=300),
                    use_container_width=True,
                )

                # ── Graphique cumulé / 1000 mots ────────────────────
                df_cumul_1k = df_cumul.merge(df_words_monthly, on="month_date", how="left")
                df_cumul_1k["occ_par_1000mots_cumul"] = (
                    df_cumul_1k["occ_total"] / df_cumul_1k["total_words"] * 1000
                ).round(4)

                base_cum_1k = alt.Chart(df_cumul_1k)
                line_cum_1k = base_cum_1k.mark_line(color="#e45756", strokeWidth=1.5, opacity=0.5).encode(
                    x=alt.X("month_date:T", title="Mois"),
                    y=alt.Y("occ_par_1000mots_cumul:Q", title="Occurrences cumulées / 1 000 mots"),
                    tooltip=[
                        alt.Tooltip("month_date:T", title="Mois", format="%Y-%m"),
                        alt.Tooltip("occ_par_1000mots_cumul:Q", title="Cumul occ. / 1 000 mots"),
                        alt.Tooltip("total_words:Q", title="Mots transcrits ce mois"),
                    ],
                )
                points_cum_1k = base_cum_1k.mark_circle(size=55, color="#e45756", opacity=0.6).encode(
                    x=alt.X("month_date:T"),
                    y=alt.Y("occ_par_1000mots_cumul:Q"),
                    tooltip=[
                        alt.Tooltip("month_date:T", title="Mois", format="%Y-%m"),
                        alt.Tooltip("occ_par_1000mots_cumul:Q", title="Cumul occ. / 1 000 mots"),
                    ],
                )
                loess_cum_1k = base_cum_1k.mark_line(color="#9b0000", strokeWidth=2.5).transform_loess(
                    "month_date", "occ_par_1000mots_cumul", bandwidth=0.3
                ).encode(
                    x=alt.X("month_date:T"),
                    y=alt.Y("occ_par_1000mots_cumul:Q"),
                )
                st.caption(f"Cumul / 1 000 mots — {', '.join(expressions)}")
                st.altair_chart(
                    (line_cum_1k + points_cum_1k + loess_cum_1k).properties(height=300),
                    use_container_width=True,
                )
            else:
                st.info("Aucune occurrence trouvée pour les expressions saisies.")

        st.divider()

        # ── Couverture de parole par vidéo ──────────────────────────
        st.subheader("Couverture de parole par vidéo")
        st.caption(
            "Ratio : durée cumulée des segments parlés / durée totale de la vidéo. "
            "Un ratio élevé = peu de silences."
        )

        coverage_rows = []
        for _, row in df.iterrows():
            vid_id = row["id"]
            if vid_id not in transcriptions:
                continue
            speech_sec = sum(
                seg["end"] - seg["start"]
                for seg in transcriptions[vid_id].get("segments", [])
                if seg.get("text", "").strip()
            )
            total_sec = row["duration"]
            coverage_rows.append(
                {
                    "title": row["title"][:50] + ("…" if len(row["title"]) > 50 else ""),
                    "url": row["url"],
                    "couverture_%": round(min(speech_sec / total_sec * 100, 100), 1) if total_sec else 0,
                    "parole_min": round(speech_sec / 60, 1),
                    "durée_min": round(total_sec / 60, 1),
                }
            )

        if coverage_rows:
            df_cov = pd.DataFrame(coverage_rows).sort_values("couverture_%", ascending=False)
            st.altair_chart(
                alt.Chart(df_cov.head(20)).mark_bar().encode(
                    x=alt.X("couverture_%:Q", title="Couverture de parole (%)", scale=alt.Scale(domain=[0, 100])),
                    y=alt.Y("title:N", sort="-x", title=None),
                    color=alt.Color("couverture_%:Q", scale=alt.Scale(scheme="greens"), legend=None),
                    tooltip=["title", "couverture_%", "parole_min", "durée_min"],
                ),
                use_container_width=True,
            )
            st.caption("Toutes les vidéos :")
            st.dataframe(
                df_cov.rename(columns={"couverture_%": "couverture (%)", "parole_min": "parole (min)", "durée_min": "durée (min)"}),
                column_config={"url": _LINK_COL},
                use_container_width=True,
                hide_index=True,
                height=400,
            )

        st.divider()

        # ── Vitesse d'élocution ─────────────────────────────────────
        st.subheader("Vitesse d'élocution (mots / minute de parole)")
        st.caption("Mots totaux ÷ durée de parole réelle. Mesure le rythme de parole par vidéo.")

        wpm_rows = []
        for _, row in df.iterrows():
            vid_id = row["id"]
            if vid_id not in transcriptions:
                continue
            data = transcriptions[vid_id]
            total_w = len(data.get("text", "").split())
            speech_sec = sum(
                seg["end"] - seg["start"]
                for seg in data.get("segments", [])
                if seg.get("text", "").strip()
            )
            if speech_sec > 0:
                wpm_rows.append({
                    "title": row["title"][:45] + ("…" if len(row["title"]) > 45 else ""),
                    "upload_date": row["upload_date"],
                    "mots_par_min": round(total_w / (speech_sec / 60), 1),
                    "mots_total": total_w,
                    "parole_min": round(speech_sec / 60, 1),
                })

        if wpm_rows:
            df_wpm = pd.DataFrame(wpm_rows).sort_values("mots_par_min", ascending=False)
            st.altair_chart(
                alt.Chart(df_wpm.head(20)).mark_bar().encode(
                    x=alt.X("mots_par_min:Q", title="Mots / minute"),
                    y=alt.Y("title:N", sort="-x", title=None),
                    color=alt.Color("mots_par_min:Q", scale=alt.Scale(scheme="purples"), legend=None),
                    tooltip=["title", "mots_par_min", "mots_total", "parole_min"],
                ),
                use_container_width=True,
            )

            df_wpm_time = df_wpm.sort_values("upload_date")
            df_wpm_time["month_date"] = df_wpm_time["upload_date"].dt.to_period("M").dt.to_timestamp()
            df_wpm_monthly = (
                df_wpm_time.groupby("month_date")["mots_par_min"]
                .mean()
                .round(1)
                .reset_index()
                .rename(columns={"mots_par_min": "mots_par_min_moy"})
            )
            base_wpm = alt.Chart(df_wpm_monthly)
            line_wpm = base_wpm.mark_line(color="#7b52ab", strokeWidth=1.5, opacity=0.5).encode(
                x=alt.X("month_date:T", title="Mois"),
                y=alt.Y("mots_par_min_moy:Q", title="Mots / minute (moy.)"),
                tooltip=[alt.Tooltip("month_date:T", format="%Y-%m"), "mots_par_min_moy"],
            )
            points_wpm = base_wpm.mark_circle(size=55, color="#7b52ab", opacity=0.6).encode(
                x=alt.X("month_date:T"),
                y=alt.Y("mots_par_min_moy:Q"),
                tooltip=[alt.Tooltip("month_date:T", format="%Y-%m"), "mots_par_min_moy"],
            )
            loess_wpm = base_wpm.mark_line(color="orange", strokeWidth=2.5).transform_loess(
                "month_date", "mots_par_min_moy", bandwidth=0.3
            ).encode(
                x=alt.X("month_date:T"),
                y=alt.Y("mots_par_min_moy:Q"),
            )
            st.caption("Évolution de la vitesse d'élocution dans le temps — orange : tendance lissée (LOESS)")
            st.altair_chart((line_wpm + points_wpm + loess_wpm).properties(height=300), use_container_width=True)

        st.divider()

        # ── Richesse du vocabulaire (TTR) ───────────────────────────
        st.subheader("Richesse du vocabulaire (Type-Token Ratio)")
        st.caption(
            "TTR = mots uniques / mots totaux. Un TTR élevé = vocabulaire plus varié. "
            "Calculé sur le texte brut (mots ≥ 3 lettres) sans filtrage de mots courants."
        )

        ttr_rows = []
        for _, row in df.iterrows():
            vid_id = row["id"]
            if vid_id not in transcriptions:
                continue
            raw = transcriptions[vid_id].get("text", "")
            tokens = re.findall(r"\b[a-zA-ZÀ-ÿ]{3,}\b", raw.lower())
            if len(tokens) >= 50:
                ttr = round(len(set(tokens)) / len(tokens), 4)
                ttr_rows.append({
                    "title": row["title"][:45] + ("…" if len(row["title"]) > 45 else ""),
                    "upload_date": row["upload_date"],
                    "ttr": ttr,
                    "mots_uniques": len(set(tokens)),
                    "mots_total": len(tokens),
                })

        if ttr_rows:
            df_ttr = pd.DataFrame(ttr_rows).sort_values("ttr", ascending=False)

            col_t1, col_t2 = st.columns(2)
            with col_t1:
                st.caption("Top 15 — Vocabulaire le plus riche")
                st.altair_chart(
                    alt.Chart(df_ttr.head(15)).mark_bar().encode(
                        x=alt.X("ttr:Q", title="TTR"),
                        y=alt.Y("title:N", sort="-x", title=None),
                        color=alt.Color("ttr:Q", scale=alt.Scale(scheme="greens"), legend=None),
                        tooltip=["title", "ttr", "mots_uniques", "mots_total"],
                    ),
                    use_container_width=True,
                )
            with col_t2:
                st.caption("Bottom 15 — Vocabulaire le moins varié")
                st.altair_chart(
                    alt.Chart(df_ttr.tail(15)).mark_bar().encode(
                        x=alt.X("ttr:Q", title="TTR"),
                        y=alt.Y("title:N", sort="-x", title=None),
                        color=alt.Color("ttr:Q", scale=alt.Scale(scheme="reds"), legend=None),
                        tooltip=["title", "ttr", "mots_uniques", "mots_total"],
                    ),
                    use_container_width=True,
                )

            df_ttr_time = df_ttr.sort_values("upload_date")
            df_ttr_time["month_date"] = df_ttr_time["upload_date"].dt.to_period("M").dt.to_timestamp()
            df_ttr_monthly = (
                df_ttr_time.groupby("month_date")["ttr"]
                .mean()
                .round(4)
                .reset_index()
                .rename(columns={"ttr": "ttr_moy"})
            )
            base_ttr = alt.Chart(df_ttr_monthly)
            line_ttr = base_ttr.mark_line(color="#2ca02c", strokeWidth=1.5, opacity=0.5).encode(
                x=alt.X("month_date:T", title="Mois"),
                y=alt.Y("ttr_moy:Q", title="TTR moyen"),
                tooltip=[alt.Tooltip("month_date:T", format="%Y-%m"), "ttr_moy"],
            )
            points_ttr = base_ttr.mark_circle(size=55, color="#2ca02c", opacity=0.6).encode(
                x=alt.X("month_date:T"),
                y=alt.Y("ttr_moy:Q"),
                tooltip=[alt.Tooltip("month_date:T", format="%Y-%m"), "ttr_moy"],
            )
            loess_ttr = base_ttr.mark_line(color="orange", strokeWidth=2.5).transform_loess(
                "month_date", "ttr_moy", bandwidth=0.3
            ).encode(
                x=alt.X("month_date:T"),
                y=alt.Y("ttr_moy:Q"),
            )
            st.caption("Évolution du TTR moyen dans le temps — orange : tendance lissée (LOESS)")
            st.altair_chart((line_ttr + points_ttr + loess_ttr).properties(height=300), use_container_width=True)


