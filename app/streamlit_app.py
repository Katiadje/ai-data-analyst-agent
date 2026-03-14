"""
AI Data Analyst Agent — Streamlit Frontend.
"""

from __future__ import annotations

import os
import time

import requests
import streamlit as st

API_BASE = os.environ.get("API_BASE_URL", "http://localhost:8000/api/v1")
POLL_INTERVAL = 2

st.set_page_config(
    page_title="AI Data Analyst Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
  [data-testid="stAppViewContainer"] { background: #0F0F1A; color: #E2E8F0; }
  [data-testid="stSidebar"] { background: #13131F; border-right: 1px solid #1E1E35; }

  .metric-card {
    background: linear-gradient(135deg, #1E1E35 0%, #13131F 100%);
    border: 1px solid #2D2D50;
    border-radius: 12px;
    padding: 20px 24px;
    margin: 8px 0;
  }
  .metric-card h3 { color: #A78BFA; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.1em; margin: 0 0 8px 0; }
  .metric-card .value { color: #E2E8F0; font-size: 1.8rem; font-weight: 700; }
  .metric-card .sub { color: #64748B; font-size: 0.85rem; margin-top: 4px; }

  .insight-card {
    background: #1A1A2E;
    border-left: 4px solid #4F46E5;
    border-radius: 0 8px 8px 0;
    padding: 16px 20px;
    margin: 10px 0;
  }
  .insight-card.high { border-left-color: #EC4899; }
  .insight-card.medium { border-left-color: #F59E0B; }
  .insight-card.low { border-left-color: #10B981; }
  .insight-card h4 { color: #C4B5FD; margin: 0 0 6px 0; font-size: 0.95rem; }
  .insight-card p { color: #94A3B8; margin: 0; font-size: 0.88rem; line-height: 1.5; }
  .insight-badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    margin-bottom: 8px;
  }
  .badge-high { background: rgba(236,72,153,0.2); color: #EC4899; }
  .badge-medium { background: rgba(245,158,11,0.2); color: #F59E0B; }
  .badge-low { background: rgba(16,185,129,0.2); color: #10B981; }

  .progress-step { color: #7C3AED; font-size: 0.9rem; font-style: italic; }

  .hero { text-align: center; padding: 48px 0 32px; }
  .hero h1 {
    font-size: 2.8rem;
    font-weight: 800;
    background: linear-gradient(135deg, #4F46E5, #EC4899);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 12px;
  }
  .hero p { color: #64748B; font-size: 1.1rem; }

  .quality-ring {
    display: flex; align-items: center; justify-content: center;
    width: 80px; height: 80px; border-radius: 50%;
    border: 4px solid #4F46E5;
    font-size: 1.4rem; font-weight: 800; color: #A78BFA;
    margin: auto;
  }

  .stProgress > div > div { background: linear-gradient(90deg, #4F46E5, #EC4899) !important; }
  .stButton > button {
    background: linear-gradient(135deg, #4F46E5, #7C3AED);
    color: white; border: none; border-radius: 8px;
    font-weight: 600; padding: 12px 28px;
    transition: all 0.2s;
  }
  .stButton > button:hover { opacity: 0.9; transform: translateY(-1px); }

  h1, h2, h3 { color: #E2E8F0 !important; }
  .stMarkdown p { color: #CBD5E1; }
  [data-testid="stDataFrame"] { background: #1A1A2E; border-radius: 8px; }

  /* Fix composants natifs */
  [data-testid="stFileUploader"] {
    background: #1A1A2E !important;
    border: 2px dashed #4F46E5 !important;
    border-radius: 12px !important;
  }
  [data-testid="stFileUploader"] * { color: #E2E8F0 !important; }
  [data-testid="stFileUploaderDropzone"] { background: #1A1A2E !important; }

  .stTextInput input {
    background: #1A1A2E !important;
    color: #E2E8F0 !important;
    border: 1px solid #2D2D50 !important;
    border-radius: 8px !important;
  }
  .stTextInput label { color: #94A3B8 !important; }

  .stTabs [data-baseweb="tab"] { color: #64748B !important; background: transparent !important; }
  .stTabs [aria-selected="true"] { color: #A78BFA !important; border-bottom-color: #4F46E5 !important; }
  .stTabs [data-baseweb="tab-list"] { background: #13131F !important; }

  [data-testid="stAlert"] { background: #1A1A2E !important; color: #E2E8F0 !important; border: 1px solid #2D2D50 !important; }
  section[data-testid="stSidebar"] * { color: #CBD5E1 !important; }
  code { background: #1A1A2E !important; color: #A78BFA !important; }
</style>
""", unsafe_allow_html=True)


# ── Helpers ────────────────────────────────────────────────────────────────────

def upload_file(file_bytes: bytes, filename: str) -> dict:
    r = requests.post(
        f"{API_BASE}/upload",
        files={"file": (filename, file_bytes, "application/octet-stream")},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def start_analysis(session_id: str) -> dict:
    r = requests.post(f"{API_BASE}/analyse/{session_id}", timeout=10)
    r.raise_for_status()
    return r.json()


def get_status(session_id: str) -> dict:
    r = requests.get(f"{API_BASE}/analyse/{session_id}", timeout=10)
    r.raise_for_status()
    return r.json()


def quality_color(score: float) -> str:
    if score >= 80:
        return "#10B981"
    if score >= 60:
        return "#F59E0B"
    return "#EC4899"


# ── Sidebar ────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 🤖 AI Data Analyst")
    st.markdown("---")
    st.markdown("""
**How it works:**
1. 📤 Upload any CSV or Excel file
2. 🧠 The AI agent profiles your data
3. 🔍 It finds key insights automatically
4. 📊 Generates relevant visualizations
5. 📝 Writes a full narrative report

**Supported formats:**
- CSV (`.csv`)
- Excel (`.xlsx`, `.xls`)

**Max file size:** 50 MB
""")
    st.markdown("---")
    st.markdown("""
**Stack:**
- 🦜 LangGraph (Agent)
- ⚡ FastAPI (Backend)
- 🐼 Pandas (Analysis)
- 🎨 Seaborn / Matplotlib
""")
    st.markdown("---")
    st.caption("Built by [Katiadje](https://github.com/Katiadje) · v1.0.0")


# ── Hero ───────────────────────────────────────────────────────────────────────

st.markdown("""
<div class="hero">
  <h1>🤖 AI Data Analyst Agent</h1>
  <p>Drop your dataset. The agent does the rest — profiling, insights, visualizations, report.</p>
</div>
""", unsafe_allow_html=True)


# ── Session State ──────────────────────────────────────────────────────────────

if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "analysis_done" not in st.session_state:
    st.session_state.analysis_done = False
if "result" not in st.session_state:
    st.session_state.result = None


# ── Upload Section ─────────────────────────────────────────────────────────────

col_upload, col_info = st.columns([2, 1])

with col_upload:
    uploaded_file = st.file_uploader(
        "Upload your dataset",
        type=["csv", "xlsx", "xls"],
        help="CSV or Excel file, max 50 MB",
    )

with col_info:
    st.markdown("### 💡 Try with sample data")
    st.markdown("Don't have a dataset? Use any public CSV:")
    st.code("https://raw.githubusercontent.com/datasciencedojo/datasets/master/titanic.csv", language="text")
    sample_url = st.text_input("Or paste a direct CSV URL:", placeholder="https://...")

run_col, _ = st.columns([1, 3])
with run_col:
    run_btn = st.button("🚀 Run Analysis", use_container_width=True)

if run_btn:
    st.session_state.analysis_done = False
    st.session_state.result = None
    file_bytes = None
    filename = None

    if uploaded_file:
        file_bytes = uploaded_file.read()
        filename = uploaded_file.name
    elif sample_url:
        with st.spinner("Fetching dataset from URL..."):
            try:
                r = requests.get(sample_url, timeout=15)
                r.raise_for_status()
                file_bytes = r.content
                filename = sample_url.split("/")[-1] or "dataset.csv"
                if not filename.endswith((".csv", ".xlsx")):
                    filename += ".csv"
            except Exception as e:
                st.error(f"Failed to fetch URL: {e}")

    if file_bytes and filename:
        with st.spinner("Uploading file..."):
            try:
                upload_resp = upload_file(file_bytes, filename)
                st.session_state.session_id = upload_resp["session_id"]
                start_analysis(st.session_state.session_id)
                st.success(f"✅ Analysis started! Session: `{st.session_state.session_id[:8]}...`")
            except Exception as e:
                st.error(f"Failed to start analysis: {e}")
    else:
        st.warning("Please upload a file or provide a URL first.")


# ── Polling ────────────────────────────────────────────────────────────────────

if st.session_state.session_id and not st.session_state.analysis_done:
    progress_placeholder = st.empty()

    while True:
        try:
            data = get_status(st.session_state.session_id)
        except Exception as e:
            st.error(f"Error fetching status: {e}")
            break

        status = data.get("status", "unknown")
        progress = data.get("progress", 0)
        step = data.get("current_step", "")

        with progress_placeholder.container():
            st.markdown(f"**{step}**")
            st.progress(progress / 100)
            st.markdown(f"<p class='progress-step'>⏳ {progress}% complete...</p>", unsafe_allow_html=True)

        if status == "done":
            st.session_state.analysis_done = True
            st.session_state.result = data
            progress_placeholder.empty()
            break
        elif status == "error":
            progress_placeholder.empty()
            st.error(f"❌ Analysis failed: {data.get('error', 'Unknown error')}")
            break

        time.sleep(POLL_INTERVAL)

    st.rerun()


# ── Results ────────────────────────────────────────────────────────────────────

if st.session_state.analysis_done and st.session_state.result:
    result = st.session_state.result
    profile = result.get("profile", {})
    insights = result.get("insights", {})
    charts = result.get("charts", [])
    duration = result.get("duration_s") or 0

    st.markdown("---")
    st.markdown("## 📊 Analysis Results")

    k1, k2, k3, k4 = st.columns(4)
    shape = profile.get("shape", {})
    quality = profile.get("data_quality_score", 0)
    n_insights = len(insights.get("key_insights", []))
    n_charts = len(charts)

    with k1:
        st.markdown(f"""<div class="metric-card">
          <h3>📦 Rows</h3>
          <div class="value">{shape.get('rows', 0):,}</div>
          <div class="sub">{shape.get('columns', 0)} columns</div>
        </div>""", unsafe_allow_html=True)
    with k2:
        st.markdown(f"""<div class="metric-card">
          <h3>✅ Data Quality</h3>
          <div class="value" style="color:{quality_color(quality)}">{quality:.0f}/100</div>
          <div class="sub">Quality score</div>
        </div>""", unsafe_allow_html=True)
    with k3:
        st.markdown(f"""<div class="metric-card">
          <h3>🔍 Insights</h3>
          <div class="value">{n_insights}</div>
          <div class="sub">Key findings</div>
        </div>""", unsafe_allow_html=True)
    with k4:
        st.markdown(f"""<div class="metric-card">
          <h3>⏱️ Duration</h3>
          <div class="value">{duration:.1f}s</div>
          <div class="sub">{n_charts} charts generated</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("---")

    tab_report, tab_insights, tab_charts, tab_profile, tab_quality = st.tabs([
        "📝 Report", "🔍 Insights", "📊 Charts", "🗂️ Profile", "⚠️ Quality"
    ])

    with tab_report:
        st.markdown("### Executive Report")
        exec_summary = insights.get("executive_summary", "")
        if exec_summary:
            st.info(exec_summary)
        if result.get("report_md"):
            st.markdown(result["report_md"])

    with tab_insights:
        st.markdown("### 🔍 Key Insights")
        for ins in insights.get("key_insights", []):
            importance = ins.get("importance", "medium")
            st.markdown(f"""
<div class="insight-card {importance}">
  <span class="insight-badge badge-{importance}">{importance}</span>
  <h4>{ins.get('title', '')}</h4>
  <p>{ins.get('description', '')}</p>
</div>""", unsafe_allow_html=True)

        if insights.get("business_implications"):
            st.markdown("### 💼 Business Implications")
            for impl in insights["business_implications"]:
                st.markdown(f"- {impl}")

        if insights.get("recommended_analyses"):
            st.markdown("### 🗺️ Recommended Next Steps")
            for rec in insights["recommended_analyses"]:
                st.markdown(f"- {rec}")

    with tab_charts:
        st.markdown("### 📊 Generated Visualizations")
        if not charts:
            st.info("No charts were generated for this dataset.")
        else:
            for i in range(0, len(charts), 2):
                cols = st.columns(2)
                for j, col in enumerate(cols):
                    if i + j < len(charts):
                        chart = charts[i + j]
                        with col:
                            st.markdown(f"**{chart.get('title', '')}**")
                            url = chart.get("url", "")
                            if url:
                                try:
                                    r = requests.get(url, timeout=10)
                                    if r.status_code == 200:
                                        st.image(r.content, use_container_width=True)
                                    else:
                                        st.warning("Chart not accessible.")
                                except Exception:
                                    st.warning("Could not load chart.")
                            if chart.get("description"):
                                st.caption(chart["description"])

    with tab_profile:
        st.markdown("### 🗂️ Column Profiles")
        cols_data = profile.get("column_profiles", [])
        if cols_data:
            import pandas as pd
            df_profile = pd.DataFrame([
                {
                    "Column": c.get("name", ""),
                    "Type": c.get("dtype", ""),
                    "Category": c.get("category", ""),
                    "Missing %": f"{c.get('missing_pct', 0):.1f}%",
                    "Unique": c.get("unique_count", 0),
                }
                for c in cols_data
            ])
            st.dataframe(df_profile, use_container_width=True, hide_index=True)

    with tab_quality:
        st.markdown("### ⚠️ Data Quality Assessment")
        quality_issues = profile.get("quality_issues", [])
        observations = profile.get("key_observations", [])

        col_q1, col_q2 = st.columns([1, 3])
        with col_q1:
            st.markdown(f"""
<div style="text-align:center; padding:20px;">
  <div class="quality-ring" style="border-color:{quality_color(quality)}; color:{quality_color(quality)}">
    {quality:.0f}
  </div>
  <p style="color:#64748B; margin-top:8px; font-size:0.85rem;">Quality Score</p>
</div>""", unsafe_allow_html=True)
        with col_q2:
            if quality_issues:
                st.markdown("**Issues detected:**")
                for issue in quality_issues:
                    st.markdown(f"⚠️ {issue}")
            else:
                st.success("No critical data quality issues detected.")
            if observations:
                st.markdown("**Key observations:**")
                for obs in observations:
                    st.markdown(f"💡 {obs}")

    st.markdown("---")
    if st.button("🔄 New Analysis", use_container_width=False):
        st.session_state.session_id = None
        st.session_state.analysis_done = False
        st.session_state.result = None
        st.rerun()
