"""
Qbias Dataset Explorer — Streamlit App
=======================================
Launch:  streamlit run dataset_explorer.py
"""

import json
import os
import random
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ── CONFIGURATION ────────────────────────────────────────────────────────────
DEFAULT_DATA_DIR = os.path.join(os.path.dirname(__file__), "output", "per_domain")
CLEANING_LOG_PATH = os.path.join(os.path.dirname(__file__), "cleaning_log.csv")

RATING_ORDER = ["left", "lean left", "center", "lean right", "right"]
RATING_COLORS = {
    "left": "#2166ac",
    "lean left": "#67a9cf",
    "center": "#f7f7f7",
    "lean right": "#ef8a62",
    "right": "#b2182b",
}
STANCE_COLORS = {"left": "#2166ac", "center": "#878787", "right": "#b2182b"}

# ── HELPERS ──────────────────────────────────────────────────────────────────

@st.cache_data(show_spinner="Loading dataset …")
def load_dataset(data_dir: str) -> pd.DataFrame:
    """Read every per-domain JSON file and flatten into a single DataFrame."""
    rows: list[dict] = []
    for fname in sorted(os.listdir(data_dir)):
        if not fname.endswith(".json"):
            continue
        fpath = os.path.join(data_dir, fname)
        with open(fpath) as f:
            data = json.load(f)
        for topic_slug, stances in data.items():
            for stance_key, article in stances.items():
                row = {
                    "source_file": fname,
                    "topic_slug": topic_slug,
                    "stance_key": stance_key,
                    **article,
                }
                rows.append(row)
    df = pd.DataFrame(rows)
    if "scrape_timestamp" in df.columns:
        df["scrape_timestamp"] = pd.to_datetime(df["scrape_timestamp"], errors="coerce")
        df["scrape_date"] = df["scrape_timestamp"].dt.date
    if "extracted_body_text" in df.columns:
        df["text_length"] = df["extracted_body_text"].fillna("").str.len()
    df["uid"] = df.index.astype(str)
    return df


def load_cleaning_log() -> pd.DataFrame:
    if os.path.exists(CLEANING_LOG_PATH):
        return pd.read_csv(CLEANING_LOG_PATH, dtype=str).fillna("")
    return pd.DataFrame(columns=["uid", "flagged", "flag_reason", "notes", "timestamp"])


def save_cleaning_log(log_df: pd.DataFrame) -> None:
    log_df.to_csv(CLEANING_LOG_PATH, index=False)


def pretty_number(n: int | float) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(int(n))


# ── PAGE CONFIG ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Qbias Dataset Explorer",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    [data-testid="stMetric"] {
        background: #f8f9fb;
        border: 1px solid #e1e4e8;
        border-radius: 8px;
        padding: 12px 16px;
    }
    .block-container { padding-top: 1.5rem; }
    div[data-testid="stExpander"] details {
        border: 1px solid #e1e4e8;
        border-radius: 8px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── SIDEBAR ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("📰 Qbias Explorer")
    data_dir = st.text_input("Dataset directory", value=DEFAULT_DATA_DIR)
    page = st.radio("Navigate", ["Dashboard", "Article Inspector", "Cleaning Log"], index=0)

# ── LOAD DATA ────────────────────────────────────────────────────────────────
if not os.path.isdir(data_dir):
    st.error(f"Directory not found: `{data_dir}`")
    st.stop()

df = load_dataset(data_dir)
if df.empty:
    st.warning("No articles found in the specified directory.")
    st.stop()

# ══════════════════════════════════════════════════════════════════════════════
#  PAGE 1 — DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
if page == "Dashboard":
    st.header("Dataset Dashboard")

    # ── Top-level metrics ────────────────────────────────────────────────────
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Articles", pretty_number(len(df)))
    c2.metric("Unique Topics", pretty_number(df["topic_slug"].nunique()))
    c3.metric("Sources", df["domain"].nunique())
    c4.metric("Success Rate", f"{(df['execution_status'] == 'SUCCESS').mean():.0%}")
    avg_len = df.loc[df["execution_status"] == "SUCCESS", "text_length"].mean()
    c5.metric("Avg Text Length", pretty_number(avg_len) if pd.notna(avg_len) else "—")

    st.divider()

    # ── Row 1: Articles by Source + Rating distribution ──────────────────────
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Articles by Source")
        source_counts = (
            df.groupby("domain")
            .size()
            .reset_index(name="count")
            .sort_values("count", ascending=True)
        )
        fig = px.bar(
            source_counts,
            y="domain",
            x="count",
            orientation="h",
            color_discrete_sequence=["#4a90d9"],
        )
        fig.update_layout(
            yaxis_title="",
            xaxis_title="Articles",
            height=420,
            margin=dict(l=0, r=20, t=10, b=30),
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_right:
        st.subheader("Political Rating Distribution")
        rating_counts = (
            df["rating"]
            .value_counts()
            .reindex(RATING_ORDER, fill_value=0)
            .reset_index()
        )
        rating_counts.columns = ["rating", "count"]
        colors = [RATING_COLORS.get(r, "#999") for r in rating_counts["rating"]]
        fig = go.Figure(
            go.Bar(
                x=rating_counts["rating"],
                y=rating_counts["count"],
                marker_color=colors,
                text=rating_counts["count"],
                textposition="outside",
            )
        )
        fig.update_layout(
            xaxis_title="",
            yaxis_title="Articles",
            height=420,
            margin=dict(l=0, r=20, t=10, b=30),
        )
        st.plotly_chart(fig, use_container_width=True)

    # ── Row 2: Execution status + Stance breakdown ───────────────────────────
    col_left2, col_right2 = st.columns(2)

    with col_left2:
        st.subheader("Execution Status")
        status_counts = df["execution_status"].value_counts().reset_index()
        status_counts.columns = ["status", "count"]
        status_color_map = {
            "SUCCESS": "#27ae60",
            "FAILED_HTTP_404": "#e74c3c",
            "FAILED_PARSE": "#f39c12",
            "FAILED_PAYWALL": "#8e44ad",
        }
        colors = [status_color_map.get(s, "#999") for s in status_counts["status"]]
        fig = go.Figure(
            go.Pie(
                labels=status_counts["status"],
                values=status_counts["count"],
                marker=dict(colors=colors),
                hole=0.45,
                textinfo="label+percent",
            )
        )
        fig.update_layout(height=380, margin=dict(l=0, r=0, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

    with col_right2:
        st.subheader("Stance Coverage per Topic")
        stance_per_topic = (
            df.groupby("topic_slug")["stance_key"]
            .nunique()
            .value_counts()
            .sort_index()
            .reset_index()
        )
        stance_per_topic.columns = ["stances_covered", "topic_count"]
        fig = px.bar(
            stance_per_topic,
            x="stances_covered",
            y="topic_count",
            color_discrete_sequence=["#6c5ce7"],
            text="topic_count",
        )
        fig.update_layout(
            xaxis_title="Number of Stances Covered",
            yaxis_title="Topics",
            height=380,
            margin=dict(l=0, r=20, t=10, b=30),
        )
        st.plotly_chart(fig, use_container_width=True)

    # ── Row 3: Avg text length by source (anomaly spotter) ───────────────────
    st.subheader("Average Text Length by Source")
    st.caption("Helps spot providers with suspiciously short or long articles.")

    success_df = df[df["execution_status"] == "SUCCESS"]
    if not success_df.empty:
        avg_text = (
            success_df.groupby("domain")["text_length"]
            .agg(["mean", "median", "std", "count"])
            .reset_index()
            .sort_values("mean", ascending=True)
        )
        avg_text.columns = ["domain", "mean_len", "median_len", "std_len", "n"]
        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                y=avg_text["domain"],
                x=avg_text["mean_len"],
                orientation="h",
                name="Mean",
                marker_color="#4a90d9",
                text=avg_text["mean_len"].round(0).astype(int),
                textposition="outside",
            )
        )
        fig.add_trace(
            go.Bar(
                y=avg_text["domain"],
                x=avg_text["median_len"],
                orientation="h",
                name="Median",
                marker_color="#a0c4e8",
            )
        )
        fig.update_layout(
            barmode="group",
            xaxis_title="Characters",
            yaxis_title="",
            height=450,
            margin=dict(l=0, r=60, t=10, b=30),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(fig, use_container_width=True)

    # ── Row 4: Timeline ─────────────────────────────────────────────────────
    if "scrape_date" in df.columns:
        st.subheader("Scrape Timeline")
        timeline = (
            df.groupby(["scrape_date", "domain"])
            .size()
            .reset_index(name="count")
        )
        fig = px.area(
            timeline,
            x="scrape_date",
            y="count",
            color="domain",
            height=380,
        )
        fig.update_layout(
            xaxis_title="",
            yaxis_title="Articles scraped",
            margin=dict(l=0, r=20, t=10, b=30),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(fig, use_container_width=True)

    # ── Row 5: Failure breakdown by source ───────────────────────────────────
    failures = df[df["execution_status"] != "SUCCESS"]
    if not failures.empty:
        st.subheader("Failures by Source & Type")
        fail_matrix = (
            failures.groupby(["domain", "execution_status"])
            .size()
            .reset_index(name="count")
        )
        fig = px.bar(
            fail_matrix,
            x="domain",
            y="count",
            color="execution_status",
            barmode="stack",
            color_discrete_map=status_color_map,
            height=380,
        )
        fig.update_layout(
            xaxis_title="",
            yaxis_title="Failed articles",
            margin=dict(l=0, r=20, t=10, b=30),
            xaxis_tickangle=-45,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(fig, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE 2 — ARTICLE INSPECTOR
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Article Inspector":
    st.header("Article Inspector")

    cleaning_log = load_cleaning_log()

    # ── Sidebar filters ─────────────────────────────────────────────────────
    with st.sidebar:
        st.subheader("Filters")

        filter_domain = st.multiselect(
            "Source / Domain",
            options=sorted(df["domain"].unique()),
            default=[],
        )
        filter_rating = st.multiselect(
            "Rating",
            options=RATING_ORDER,
            default=[],
        )
        filter_status = st.multiselect(
            "Execution Status",
            options=sorted(df["execution_status"].unique()),
            default=[],
        )
        filter_stance = st.multiselect(
            "Stance Key",
            options=sorted(df["stance_key"].unique()),
            default=[],
        )

    # Apply filters
    filtered = df.copy()
    if filter_domain:
        filtered = filtered[filtered["domain"].isin(filter_domain)]
    if filter_rating:
        filtered = filtered[filtered["rating"].isin(filter_rating)]
    if filter_status:
        filtered = filtered[filtered["execution_status"].isin(filter_status)]
    if filter_stance:
        filtered = filtered[filtered["stance_key"].isin(filter_stance)]

    if filtered.empty:
        st.info("No articles match the current filters.")
        st.stop()

    st.caption(f"**{len(filtered):,}** articles match your filters.")

    # ── Article selection ────────────────────────────────────────────────────
    sel_col1, sel_col2 = st.columns([3, 1])
    with sel_col1:
        options_map = {
            f"[{row['domain']}] {row['extracted_headline'][:80] if pd.notna(row['extracted_headline']) else row['topic_slug']}"
            + f"  ({row['stance_key']})": idx
            for idx, row in filtered.iterrows()
        }
        selected_label = st.selectbox(
            "Select an article",
            options=list(options_map.keys()),
            index=0,
        )
    with sel_col2:
        if st.button("🎲 Random Article", use_container_width=True):
            rand_idx = random.choice(filtered.index.tolist())
            st.session_state["_rand_idx"] = rand_idx
            st.rerun()

    # Handle random selection
    if "_rand_idx" in st.session_state:
        rand_idx = st.session_state.pop("_rand_idx")
        if rand_idx in filtered.index:
            art = filtered.loc[rand_idx]
        else:
            art = filtered.iloc[0]
    else:
        art = filtered.loc[options_map[selected_label]]

    st.divider()

    # ── Metadata block ───────────────────────────────────────────────────────
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Domain", art["domain"])
    m2.metric("Rating", art.get("rating", "—"))
    m3.metric("Stance", art.get("stance_key", "—"))
    m4.metric("Status", art.get("execution_status", "—"))

    m5, m6, m7, m8 = st.columns(4)
    m5.metric("HTTP Code", art.get("http_status_code", "—"))
    m6.metric(
        "Text Length",
        f"{art.get('text_length', 0):,} chars" if pd.notna(art.get("text_length")) else "—",
    )
    ts = art.get("scrape_timestamp")
    m7.metric("Scraped", ts.strftime("%Y-%m-%d %H:%M") if pd.notna(ts) else "—")
    m8.metric("Topic Slug", art["topic_slug"][:25] + "…" if len(str(art["topic_slug"])) > 25 else art["topic_slug"])

    with st.expander("🔗 URL & Source File"):
        st.code(art.get("url", "—"), language=None)
        st.caption(f"Source file: `{art.get('source_file', '—')}`  |  Topic: `{art['topic_slug']}`")

    st.divider()

    # ── Article content + image ──────────────────────────────────────────────
    content_col, image_col = st.columns([3, 2])

    with content_col:
        st.subheader(art.get("extracted_headline") or "*(no headline)*")
        body = art.get("extracted_body_text")
        if body and str(body).strip():
            st.markdown(
                f'<div style="max-height:500px; overflow-y:auto; padding:12px; '
                f'background:#fafafa; border:1px solid #e1e4e8; border-radius:8px; '
                f'line-height:1.7; font-size:0.95rem;">{body}</div>',
                unsafe_allow_html=True,
            )
        else:
            st.warning("No body text extracted for this article.")

    with image_col:
        images = art.get("extracted_images")
        if isinstance(images, list) and len(images) > 0:
            st.subheader("Images")
            for img in images[:5]:
                if isinstance(img, dict):
                    img_url = img.get("url", "")
                    alt = img.get("alt", "")
                else:
                    img_url = str(img)
                    alt = ""
                if img_url:
                    st.image(img_url, caption=alt[:120] if alt else None, use_container_width=True)
        else:
            st.info("No images extracted for this article.")

        videos = art.get("extracted_videos")
        if isinstance(videos, list) and len(videos) > 0:
            with st.expander(f"🎬 Videos ({len(videos)})"):
                for v in videos[:5]:
                    if isinstance(v, dict):
                        st.code(v.get("url", str(v)), language=None)
                    else:
                        st.code(str(v), language=None)

    # ── Error payload ────────────────────────────────────────────────────────
    err = art.get("error_payload")
    if err and str(err).strip() and str(err) != "None":
        with st.expander("⚠️ Error Payload"):
            st.code(str(err), language="json")

    st.divider()

    # ── Flagging & Notes ─────────────────────────────────────────────────────
    st.subheader("Flag & Annotate")

    uid = str(art.name) if hasattr(art, "name") else art["uid"]
    existing = cleaning_log[cleaning_log["uid"] == uid]
    has_existing = not existing.empty

    flag_reasons = [
        "Empty / missing text",
        "Broken encoding / garbled text",
        "Wrong image",
        "Content mismatch (headline ≠ body)",
        "Paywall / incomplete content",
        "Duplicate article",
        "Other",
    ]

    fc1, fc2 = st.columns([1, 2])
    with fc1:
        flagged = st.checkbox(
            "🚩 Flag this article",
            value=bool(has_existing and existing.iloc[0]["flagged"] == "True"),
            key=f"flag_{uid}",
        )
        flag_reason = st.selectbox(
            "Reason",
            options=[""] + flag_reasons,
            index=(
                (flag_reasons.index(existing.iloc[0]["flag_reason"]) + 1)
                if has_existing and existing.iloc[0]["flag_reason"] in flag_reasons
                else 0
            ),
            key=f"reason_{uid}",
            disabled=not flagged,
        )
    with fc2:
        notes = st.text_area(
            "Notes",
            value=existing.iloc[0]["notes"] if has_existing else "",
            height=120,
            placeholder="Add observations about this article or its provider …",
            key=f"notes_{uid}",
        )

    if st.button("💾 Save Annotation", type="primary", use_container_width=True):
        new_row = {
            "uid": uid,
            "flagged": str(flagged),
            "flag_reason": flag_reason if flagged else "",
            "notes": notes,
            "timestamp": datetime.now().isoformat(),
        }
        if has_existing:
            cleaning_log.loc[cleaning_log["uid"] == uid, list(new_row.keys())] = list(
                new_row.values()
            )
        else:
            cleaning_log = pd.concat(
                [cleaning_log, pd.DataFrame([new_row])], ignore_index=True
            )
        save_cleaning_log(cleaning_log)
        st.success("Annotation saved.")


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE 3 — CLEANING LOG
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Cleaning Log":
    st.header("Cleaning Log")

    cleaning_log = load_cleaning_log()

    if cleaning_log.empty:
        st.info("No annotations yet. Use the Article Inspector to flag articles and add notes.")
        st.stop()

    flag_count = (cleaning_log["flagged"] == "True").sum()
    noted_count = (cleaning_log["notes"].str.strip() != "").sum()

    lc1, lc2, lc3 = st.columns(3)
    lc1.metric("Total Annotations", len(cleaning_log))
    lc2.metric("Flagged Articles", int(flag_count))
    lc3.metric("With Notes", int(noted_count))

    st.divider()

    # Merge with main dataset for richer view
    log_enriched = cleaning_log.copy()
    log_enriched["uid"] = log_enriched["uid"].astype(str)
    df["uid"] = df.index.astype(str)
    log_enriched = log_enriched.merge(
        df[["uid", "domain", "extracted_headline", "topic_slug", "rating", "execution_status"]],
        on="uid",
        how="left",
    )

    show_flagged_only = st.checkbox("Show only flagged articles", value=False)
    if show_flagged_only:
        log_enriched = log_enriched[log_enriched["flagged"] == "True"]

    display_cols = [
        "domain",
        "extracted_headline",
        "flagged",
        "flag_reason",
        "notes",
        "timestamp",
    ]
    available_cols = [c for c in display_cols if c in log_enriched.columns]
    st.dataframe(
        log_enriched[available_cols],
        use_container_width=True,
        height=500,
        column_config={
            "extracted_headline": st.column_config.TextColumn("Headline", width="large"),
            "notes": st.column_config.TextColumn("Notes", width="large"),
            "flagged": st.column_config.TextColumn("Flagged", width="small"),
        },
    )

    st.divider()

    # Export
    col_dl1, col_dl2 = st.columns(2)
    with col_dl1:
        csv_data = cleaning_log.to_csv(index=False)
        st.download_button(
            "📥 Download Cleaning Log (CSV)",
            data=csv_data,
            file_name="cleaning_log.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with col_dl2:
        if st.button("🗑️ Clear All Annotations", use_container_width=True):
            if os.path.exists(CLEANING_LOG_PATH):
                os.remove(CLEANING_LOG_PATH)
            st.success("Cleaning log cleared.")
            st.rerun()
