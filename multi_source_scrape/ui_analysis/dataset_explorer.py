"""
Qbias Dataset Explorer — Streamlit App
=======================================
Launch:  streamlit run dataset_explorer.py
"""

import hashlib
import json
import os
import random
import tempfile
from collections import Counter
from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ── CONFIGURATION ────────────────────────────────────────────────────────────
CLEANING_LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cleaning_log.csv")

RATING_ORDER = ["left", "lean left", "center", "lean right", "right"]
RATING_COLORS = {
    "left": "#2166ac",
    "lean left": "#67a9cf",
    "center": "#f7f7f7",
    "lean right": "#ef8a62",
    "right": "#b2182b",
}
STATUS_COLOR_MAP = {
    "SUCCESS": "#27ae60",
    "FAILED_HTTP_404": "#e74c3c",
    "FAILED_PARSE": "#f39c12",
    "FAILED_PAYWALL": "#8e44ad",
}

# ── HELPERS ──────────────────────────────────────────────────────────────────

def load_from_uploaded(uploaded_files: list) -> pd.DataFrame:
    rows: list[dict] = []
    for uf in uploaded_files:
        data = json.load(uf)
        for topic_slug, stances in data.items():
            for stance_key, article in stances.items():
                rows.append({
                    "source_file": uf.name,
                    "topic_slug": topic_slug,
                    "stance_key": stance_key,
                    **article,
                })
    return _post_process(pd.DataFrame(rows)) if rows else pd.DataFrame()


@st.cache_resource(show_spinner="Loading dataset from directory …")
def load_from_directory(data_dir: str) -> pd.DataFrame:
    rows: list[dict] = []
    for fname in sorted(os.listdir(data_dir)):
        if not fname.endswith(".json"):
            continue
        with open(os.path.join(data_dir, fname)) as f:
            data = json.load(f)
        for topic_slug, stances in data.items():
            for stance_key, article in stances.items():
                rows.append({
                    "source_file": fname,
                    "topic_slug": topic_slug,
                    "stance_key": stance_key,
                    **article,
                })
    return _post_process(pd.DataFrame(rows)) if rows else pd.DataFrame()


def _post_process(df: pd.DataFrame) -> pd.DataFrame:
    if "scrape_timestamp" in df.columns:
        df["scrape_timestamp"] = pd.to_datetime(df["scrape_timestamp"], errors="coerce")
        df["scrape_date"] = df["scrape_timestamp"].dt.date
    if "extracted_body_text" in df.columns:
        df["text_length"] = df["extracted_body_text"].fillna("").str.len()
    df["uid"] = df.index.astype(str)
    # duplicate URL detection
    if "url" in df.columns:
        url_counts = df["url"].value_counts()
        df["url_occurrences"] = df["url"].map(url_counts)
        df["is_duplicate_url"] = df["url_occurrences"] > 1
    return df


def load_cleaning_log() -> pd.DataFrame:
    if os.path.exists(CLEANING_LOG_PATH):
        return pd.read_csv(CLEANING_LOG_PATH, dtype=str).fillna("")
    return pd.DataFrame(columns=["uid", "flagged", "flag_reason", "notes", "timestamp"])


def save_cleaning_log(log_df: pd.DataFrame) -> None:
    log_df.to_csv(CLEANING_LOG_PATH, index=False)


def pretty_number(n) -> str:
    if pd.isna(n):
        return "—"
    n = float(n)
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(int(n))


def safe_list(val) -> list:
    """Safely extract a list from a DataFrame cell that might be list, NaN, None, or empty."""
    if isinstance(val, list):
        return val
    try:
        if pd.notna(val):
            return list(val) if hasattr(val, '__iter__') and not isinstance(val, str) else []
    except (TypeError, ValueError):
        pass
    return []




# ── PAGE CONFIG ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Qbias Dataset Explorer",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
[data-testid="stMetric"] {
    background: #f0f2f6; border: 1px solid #d1d5db;
    border-radius: 8px; padding: 12px 16px;
}
[data-testid="stMetric"] label {
    color: #555 !important;
}
[data-testid="stMetric"] [data-testid="stMetricValue"] {
    color: #1a1a2e !important;
}
[data-testid="stMetric"] [data-testid="stMetricDelta"] {
    color: inherit !important;
}
.block-container { padding-top: 1.2rem; }
div[data-testid="stExpander"] details {
    border: 1px solid #e1e4e8; border-radius: 8px;
}
.dup-badge { background: #e74c3c; color: white; padding: 2px 8px; border-radius: 10px; font-size: 0.8em; font-weight: 600; }
.ok-badge  { background: #27ae60; color: white; padding: 2px 8px; border-radius: 10px; font-size: 0.8em; }
</style>
""", unsafe_allow_html=True)

# ── SIDEBAR — DATA LOADING ──────────────────────────────────────────────────
with st.sidebar:
    st.title("📰 Qbias Explorer")

    load_method = st.radio("Load dataset", ["Upload JSON files", "Local directory path"], index=0)

    if load_method == "Upload JSON files":
        uploaded = st.file_uploader(
            "Drop per-domain JSON files here",
            type=["json"],
            accept_multiple_files=True,
        )
    else:
        data_dir = st.text_input(
            "Directory path",
            value="/nfs/home/abdullaha/qbias/Qbias/multi_source_scrape/output/per_domain",
        )

    st.divider()
    page = st.radio("Navigate", ["Dashboard", "Article Inspector", "Cleaning Log"], index=0)

# ── LOAD DATA ────────────────────────────────────────────────────────────────
df = pd.DataFrame()

if load_method == "Upload JSON files":
    if uploaded:
        cache_key = hashlib.md5("".join(f.name for f in uploaded).encode()).hexdigest()
        if st.session_state.get("_upload_key") != cache_key:
            st.session_state["_upload_key"] = cache_key
            st.session_state["_upload_df"] = load_from_uploaded(uploaded)
        df = st.session_state.get("_upload_df", pd.DataFrame())
    else:
        st.info("Upload one or more per-domain JSON files using the sidebar to get started.")
        st.stop()
else:
    if not os.path.isdir(data_dir):
        st.error(f"Directory not found: `{data_dir}`")
        st.stop()
    df = load_from_directory(data_dir)

if df.empty:
    st.warning("No articles found. Check your files / directory.")
    st.stop()


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE 1 — DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
if page == "Dashboard":
    st.header("Dataset Dashboard")

    # ── Top metrics ──────────────────────────────────────────────────────────
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Total Articles", pretty_number(len(df)))
    c2.metric("Unique Topics", pretty_number(df["topic_slug"].nunique()))
    c3.metric("Sources", df["domain"].nunique() if "domain" in df.columns else 0)
    c4.metric("Success Rate", f"{(df['execution_status'] == 'SUCCESS').mean():.0%}" if "execution_status" in df.columns else "—")
    avg_len = df.loc[df["execution_status"] == "SUCCESS", "text_length"].mean() if "execution_status" in df.columns else None
    c5.metric("Avg Text Len", pretty_number(avg_len))
    dup_count = int(df["is_duplicate_url"].sum()) if "is_duplicate_url" in df.columns else 0
    c6.metric("Duplicate URLs", dup_count, delta=f"{dup_count} rows" if dup_count else None, delta_color="inverse")

    st.divider()

    # ── Duplicate URL report ─────────────────────────────────────────────────
    if dup_count > 0:
        with st.expander(f"⚠️ Duplicate URLs — {dup_count} articles share a URL with another row", expanded=False):
            dup_df = df[df["is_duplicate_url"]][["domain", "topic_slug", "stance_key", "url", "url_occurrences"]].sort_values("url_occurrences", ascending=False)
            st.dataframe(dup_df, use_container_width=True, height=300)

    # ── Row 1 ────────────────────────────────────────────────────────────────
    col_l, col_r = st.columns(2)

    with col_l:
        st.subheader("Articles by Source")
        source_counts = df.groupby("domain").size().reset_index(name="count").sort_values("count", ascending=True)
        fig = px.bar(source_counts, y="domain", x="count", orientation="h", color_discrete_sequence=["#4a90d9"])
        fig.update_layout(yaxis_title="", xaxis_title="Articles", height=420, margin=dict(l=0, r=20, t=10, b=30))
        st.plotly_chart(fig, use_container_width=True)

    with col_r:
        st.subheader("Political Rating Distribution")
        rating_counts = df["rating"].value_counts().reindex(RATING_ORDER, fill_value=0).reset_index()
        rating_counts.columns = ["rating", "count"]
        colors = [RATING_COLORS.get(r, "#999") for r in rating_counts["rating"]]
        fig = go.Figure(go.Bar(x=rating_counts["rating"], y=rating_counts["count"], marker_color=colors, text=rating_counts["count"], textposition="outside"))
        fig.update_layout(xaxis_title="", yaxis_title="Articles", height=420, margin=dict(l=0, r=20, t=10, b=30))
        st.plotly_chart(fig, use_container_width=True)

    # ── Row 2 ────────────────────────────────────────────────────────────────
    col_l2, col_r2 = st.columns(2)
    with col_l2:
        st.subheader("Execution Status")
        status_counts = df["execution_status"].value_counts().reset_index()
        status_counts.columns = ["status", "count"]
        colors = [STATUS_COLOR_MAP.get(s, "#999") for s in status_counts["status"]]
        fig = go.Figure(go.Pie(labels=status_counts["status"], values=status_counts["count"], marker=dict(colors=colors), hole=0.45, textinfo="label+percent"))
        fig.update_layout(height=380, margin=dict(l=0, r=0, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

    with col_r2:
        st.subheader("Stance Coverage per Topic")
        stance_per_topic = df.groupby("topic_slug")["stance_key"].nunique().value_counts().sort_index().reset_index()
        stance_per_topic.columns = ["stances_covered", "topic_count"]
        fig = px.bar(stance_per_topic, x="stances_covered", y="topic_count", color_discrete_sequence=["#6c5ce7"], text="topic_count")
        fig.update_layout(xaxis_title="Stances Covered", yaxis_title="Topics", height=380, margin=dict(l=0, r=20, t=10, b=30))
        st.plotly_chart(fig, use_container_width=True)

    # ── Avg text length ──────────────────────────────────────────────────────
    st.subheader("Average Text Length by Source")
    st.caption("Spot providers with suspiciously short or long articles.")
    success_df = df[df["execution_status"] == "SUCCESS"] if "execution_status" in df.columns else df
    if not success_df.empty and "text_length" in success_df.columns:
        avg_text = success_df.groupby("domain")["text_length"].agg(["mean", "median"]).reset_index().sort_values("mean", ascending=True)
        avg_text.columns = ["domain", "mean_len", "median_len"]
        fig = go.Figure()
        fig.add_trace(go.Bar(y=avg_text["domain"], x=avg_text["mean_len"], orientation="h", name="Mean", marker_color="#4a90d9", text=avg_text["mean_len"].round(0).astype(int), textposition="outside"))
        fig.add_trace(go.Bar(y=avg_text["domain"], x=avg_text["median_len"], orientation="h", name="Median", marker_color="#a0c4e8"))
        fig.update_layout(barmode="group", xaxis_title="Characters", yaxis_title="", height=450, margin=dict(l=0, r=60, t=10, b=30), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig, use_container_width=True)

    # ── Failures ─────────────────────────────────────────────────────────────
    if "execution_status" in df.columns:
        failures = df[df["execution_status"] != "SUCCESS"]
        if not failures.empty:
            st.subheader("Failures by Source & Type")
            fail_matrix = failures.groupby(["domain", "execution_status"]).size().reset_index(name="count")
            fig = px.bar(fail_matrix, x="domain", y="count", color="execution_status", barmode="stack", color_discrete_map=STATUS_COLOR_MAP, height=380)
            fig.update_layout(xaxis_title="", yaxis_title="Failed articles", margin=dict(l=0, r=20, t=10, b=30), xaxis_tickangle=-45, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE 2 — ARTICLE INSPECTOR
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Article Inspector":
    st.header("Article Inspector")

    cleaning_log = load_cleaning_log()

    # ── Sidebar filters ──────────────────────────────────────────────────────
    with st.sidebar:
        st.subheader("Filters")
        filter_domain = st.multiselect("Source / Domain", sorted(df["domain"].unique()), default=[])
        filter_rating = st.multiselect("Rating", RATING_ORDER, default=[])
        filter_status = st.multiselect("Execution Status", sorted(df["execution_status"].unique()), default=[])
        filter_stance = st.multiselect("Stance Key", sorted(df["stance_key"].unique()), default=[])
        filter_dupes = st.checkbox("Only duplicate URLs", value=False)

    filtered = df.copy()
    if filter_domain:
        filtered = filtered[filtered["domain"].isin(filter_domain)]
    if filter_rating:
        filtered = filtered[filtered["rating"].isin(filter_rating)]
    if filter_status:
        filtered = filtered[filtered["execution_status"].isin(filter_status)]
    if filter_stance:
        filtered = filtered[filtered["stance_key"].isin(filter_stance)]
    if filter_dupes and "is_duplicate_url" in filtered.columns:
        filtered = filtered[filtered["is_duplicate_url"]]

    if filtered.empty:
        st.info("No articles match the current filters.")
        st.stop()

    st.caption(f"**{len(filtered):,}** articles match your filters.")

    # ── Article selection ────────────────────────────────────────────────────
    sel1, sel2 = st.columns([4, 1])
    with sel1:
        options_map = {}
        for idx, row in filtered.iterrows():
            hl = row["extracted_headline"][:70] if pd.notna(row.get("extracted_headline")) else row["topic_slug"][:50]
            dup_tag = " 🔴DUP" if row.get("is_duplicate_url") else ""
            label = f"[{row['domain']}] {hl}  ({row['stance_key']}){dup_tag}"
            options_map[label] = idx
        selected_label = st.selectbox("Select an article", list(options_map.keys()), index=0)
    with sel2:
        if st.button("🎲 Random", use_container_width=True):
            st.session_state["_rand_idx"] = random.choice(filtered.index.tolist())
            st.rerun()

    if "_rand_idx" in st.session_state:
        rand_idx = st.session_state.pop("_rand_idx")
        art = filtered.loc[rand_idx] if rand_idx in filtered.index else filtered.iloc[0]
    else:
        art = filtered.loc[options_map[selected_label]]

    st.divider()

    # ── Metadata cards ───────────────────────────────────────────────────────
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Domain", art["domain"])
    m2.metric("Rating", art.get("rating", "—"))
    m3.metric("Stance", art.get("stance_key", "—"))
    m4.metric("Status", art.get("execution_status", "—"))
    m5.metric("HTTP", art.get("http_status_code", "—"))

    m6, m7, m8 = st.columns(3)
    m6.metric("Text Length", f"{art.get('text_length', 0):,} chars" if pd.notna(art.get("text_length")) else "—")
    slug = str(art["topic_slug"])
    m7.metric("Topic", slug[:30] + "…" if len(slug) > 30 else slug)
    is_dup = art.get("is_duplicate_url", False)
    dup_n = int(art.get("url_occurrences", 1))
    m8.metric("URL Copies", dup_n, delta="DUPLICATE" if is_dup else "unique", delta_color="inverse" if is_dup else "normal")

    # URL bar
    url = art.get("url", "")
    if url:
        dup_html = f'  <span class="dup-badge">DUPLICATE ×{dup_n}</span>' if is_dup else '  <span class="ok-badge">unique</span>'
        st.markdown(f'🔗 **URL:** `{url}`{dup_html}', unsafe_allow_html=True)
    st.caption(f"Source file: `{art.get('source_file', '—')}`")

    # If duplicate, show the other articles sharing this URL
    if is_dup:
        with st.expander(f"🔴 {dup_n} articles share this URL — click to see all"):
            dup_rows = df[df["url"] == url][["domain", "topic_slug", "stance_key", "extracted_headline", "source_file"]]
            st.dataframe(dup_rows, use_container_width=True)

    st.divider()

    # Auto-open the original page in a new browser tab
    if url:
        art_id = f"{art.get('source_file', '')}_{art.get('topic_slug', '')}_{art.get('stance_key', '')}"
        if st.session_state.get("_last_opened_art") != art_id:
            st.session_state["_last_opened_art"] = art_id
            st.components.v1.html(
                f'<script>window.open("{url}", "_blank");</script>',
                height=0,
            )

    st.subheader("Extracted Content")

    # ── Article headline + raw JSON toggle ─────────────────────────────
    headline = art.get("extracted_headline")
    if headline and str(headline).strip():
        st.markdown(f"# {str(headline).strip()}")

    # Build the original JSON object for this datapoint
    json_fields = [
        "domain", "url", "rating", "http_status_code",
        "execution_status", "extracted_headline", "extracted_body_text",
        "error_payload", "extracted_images", "extracted_interactives",
        "extracted_videos",
    ]
    raw_obj = {}
    for field in json_fields:
        val = art.get(field)
        if val is not None:
            try:
                if pd.notna(val):
                    raw_obj[field] = val
            except (TypeError, ValueError):
                raw_obj[field] = val

    with st.expander("🔍 Raw JSON for this datapoint"):
        st.code(json.dumps(raw_obj, indent=2, default=str), language="json")

    body = str(art.get("extracted_body_text", "") or "")

    # ── Full article body (rendered as markdown) ─────────────────────────
    with st.expander("📝 Full Article Text", expanded=True):
        if body.strip():
            st.markdown(body.replace("$", "\\$"))
        else:
            st.warning("No body text extracted.")

    # ── Images with captions ─────────────────────────────────────────────
    images = safe_list(art.get("extracted_images"))
    if images:
        with st.expander(f"🖼️ Images ({len(images)})", expanded=True):
            for i, img in enumerate(images):
                if isinstance(img, dict):
                    img_url = img.get("url", "")
                    alt = img.get("alt", "")
                    caption = img.get("caption", "")
                else:
                    img_url, alt, caption = str(img), "", ""

                if img_url:
                    st.image(img_url, use_container_width=True)
                    info_parts = []
                    if caption:
                        info_parts.append(f"**Caption:** {caption}")
                    if alt:
                        info_parts.append(f"**Alt:** {alt}")
                    info_parts.append(f"`{img_url}`")
                    st.markdown("  \n".join(info_parts))
                    if i < len(images) - 1:
                        st.divider()
    else:
        st.info("No images extracted.")

    # ── Videos ───────────────────────────────────────────────────────────
    videos = safe_list(art.get("extracted_videos"))
    if videos:
        with st.expander(f"🎬 Videos ({len(videos)})"):
            for v in videos[:5]:
                st.code(v.get("url", str(v)) if isinstance(v, dict) else str(v), language=None)

    # ── Error payload ────────────────────────────────────────────────────
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
        "Headings not in markdown",
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
            placeholder="Add observations about this article or provider …",
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
            cleaning_log.loc[cleaning_log["uid"] == uid, list(new_row.keys())] = list(new_row.values())
        else:
            cleaning_log = pd.concat([cleaning_log, pd.DataFrame([new_row])], ignore_index=True)
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

    log_enriched = cleaning_log.copy()
    log_enriched["uid"] = log_enriched["uid"].astype(str)
    df_for_merge = df.copy()
    df_for_merge["uid"] = df_for_merge.index.astype(str)
    log_enriched = log_enriched.merge(
        df_for_merge[["uid", "domain", "extracted_headline", "topic_slug", "rating", "execution_status"]],
        on="uid",
        how="left",
    )

    show_flagged_only = st.checkbox("Show only flagged articles", value=False)
    if show_flagged_only:
        log_enriched = log_enriched[log_enriched["flagged"] == "True"]

    display_cols = ["domain", "extracted_headline", "flagged", "flag_reason", "notes", "timestamp"]
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

    col_dl1, col_dl2 = st.columns(2)
    with col_dl1:
        st.download_button(
            "📥 Download Cleaning Log (CSV)",
            data=cleaning_log.to_csv(index=False),
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
