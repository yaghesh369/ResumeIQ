import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from ..analysis.skill_matcher import build_skill_gap_dataframe, build_breakdown_dataframe
from ..analysis.domains import DOMAIN_CHOICES, resolve_domain
from ..analysis.scoring import score_band


def apply_app_styles():
    """Apply the shared visual language once per Streamlit rerun."""
    st.markdown(
        """
        <style>
        :root { --ink: #17212b; --muted: #63707c; --accent: #0b7285; --warm: #f59f00; }
        .stApp { background: #f7f9f7; color: var(--ink); }
        .block-container { max-width: 1240px; padding-top: 4.5rem; padding-bottom: 3rem; }
        main [data-testid="stMarkdownContainer"], main label, main [data-testid="stCaptionContainer"] { color: var(--ink); }
        main [data-testid="stCaptionContainer"] { color: var(--muted); }
        [data-testid="stSidebar"] { background: #102a2e; border-right: 1px solid #d8e3df; }
        [data-testid="stSidebar"] > div:first-child { height: 100vh; overflow-y: auto; }
        [data-testid="stSidebar"] * { color: #edf6f3; }
        [data-testid="stSidebar"] .stCaption { color: #b7d0cb; }
        h1, h2, h3 { letter-spacing: 0; color: var(--ink); }
        .hero-panel { background: linear-gradient(125deg, #d8f3dc 0%, #f8edeb 62%, #fff3bf 100%); border: 1px solid #c9ded7; padding: 2.2rem 2.4rem; border-radius: 8px; margin: 0 auto 1.3rem; max-width: 1160px; }
        .hero-kicker { color: var(--accent); font-size: .78rem; font-weight: 700; letter-spacing: .12em; text-transform: uppercase; }
        .hero-panel h1 { font-family: Georgia, serif; font-size: clamp(2.2rem, 5vw, 4.4rem); line-height: 1; margin: .4rem 0 .8rem; }
        .hero-panel p { max-width: 650px; color: #40515a; font-size: 1.05rem; }
        .section-label { color: var(--accent); font-size: .76rem; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; }
        div[data-testid="stMetric"] { background: #ffffff; border: 1px solid #dce7e2; border-radius: 8px; padding: .8rem 1rem; box-shadow: 0 2px 8px rgba(16,42,46,.04); }
        div[data-testid="stMetricLabel"] { color: var(--muted); }
        .stButton > button { min-height: 2.5rem; border: 1px solid #b9cbc5; border-radius: 6px; background: #ffffff; color: var(--ink); font-weight: 600; transition: background .15s ease, border-color .15s ease, transform .15s ease; }
        .stButton > button p { color: inherit !important; }
        .stButton > button:hover { border-color: var(--accent); background: #e8f5f2; color: #075b69; transform: translateY(-1px); }
        .stButton > button[kind="primary"] { background: var(--accent); border-color: var(--accent); color: #ffffff; }
        .stButton > button[kind="primary"]:hover { background: #075b69; border-color: #075b69; color: #ffffff; }
        [data-testid="stSidebar"] .stButton > button { background: transparent; border-color: #356168; color: #edf6f3; text-align: left; }
        [data-testid="stSidebar"] .stButton > button:hover { background: #1b4549; border-color: #79c7c0; color: #ffffff; }
        main input, main textarea, main [data-baseweb="select"] { color: var(--ink) !important; background: #ffffff !important; }
        main input::placeholder, main textarea::placeholder { color: #718096 !important; opacity: 1; }
        main [data-baseweb="select"] * { color: var(--ink) !important; }
        [data-testid="stSidebar"] [data-baseweb="select"], [data-testid="stSidebar"] [data-baseweb="select"] > div { color: #ffffff !important; background: #1b4549 !important; border-color: #79c7c0 !important; }
        [data-testid="stSidebar"] [data-baseweb="select"] *, [data-testid="stSidebar"] [data-baseweb="select"] input { color: #ffffff !important; background: transparent !important; }
        [data-testid="stSidebar"] [role="combobox"], [data-testid="stSidebar"] [role="combobox"] * { color: #ffffff !important; }
        [data-testid="stSidebar"] .react-aria-ComboBox [role="group"] { background: #1b4549 !important; border: 1px solid #79c7c0 !important; border-radius: 6px; }
        [data-testid="stSidebar"] .react-aria-ComboBox [role="group"] input { color: #ffffff !important; background: transparent !important; }
        [data-testid="stSidebar"] .react-aria-ComboBox [role="group"] button { color: #ffffff !important; background: transparent !important; border: 0 !important; }
        [data-testid="stSidebar"] [role="listbox"], [data-testid="stSidebar"] [role="option"] { background: #1b4549 !important; color: #ffffff !important; }
        [data-testid="stAlert"] p, [data-testid="stAlert"] div { color: inherit; }
        [data-testid="stFileUploader"] section { background: #ffffff; border-color: #b9cbc5; }
        [data-testid="stFileUploader"] section * { color: var(--ink); }
        [data-testid="stDataFrame"], [data-testid="stDataEditor"] { max-width: 100%; overflow-x: auto; }
        [data-testid="stPlotlyChart"] { max-width: 100%; overflow: hidden; }
        @media (max-width: 768px) {
            .block-container { max-width: none; padding: 4rem .85rem 2rem; }
            [data-testid="stHorizontalBlock"] { flex-direction: column; gap: .55rem; }
            [data-testid="column"] { width: 100% !important; flex: 1 1 100% !important; min-width: 100% !important; }
            .hero-panel { padding: 1.35rem 1.1rem; }
            .hero-panel h1 { font-size: 2.45rem; line-height: 1.05; }
            .hero-panel p { font-size: .98rem; }
            h1 { font-size: 2rem !important; }
            h2 { font-size: 1.55rem !important; }
            h3 { font-size: 1.2rem !important; }
            div[data-testid="stMetric"] { padding: .65rem .8rem; }
            div[data-testid="stMetricValue"] { font-size: 1.45rem; }
            [data-testid="stTabs"] [role="tablist"] { overflow-x: auto; flex-wrap: nowrap; }
            [data-testid="stTabs"] button[role="tab"] { white-space: nowrap; }
            .stFileUploader section { padding: .65rem; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def init_session_state():
    """Initialize all session state variables once at startup."""
    defaults = {
        "resume_text": "",
        "jd_text": "",
        "resume_data": {},
        "jd_data": {},
        "analysis": {},
        "critic": {},
        "improvements": {},
        "interview_questions": {},
        "ats_score": 0,
        "ats_breakdown": {},
        "skill_gap": {},
        "current_page": "🏠 Home",
        "version_comparison": {"v1": None, "v2": None},
        "voice_evaluations": [],
        "detected_skills": [],
        "domain_override": "Auto",
        "custom_keywords": [],
        "domain_label": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def render_sidebar():
    """Render the application sidebar navigation."""
    with st.sidebar:
        st.markdown(
            "<h2 style='text-align:center;color:#4F8BF9;'>🏆 ResumeIQ</h2>",
            unsafe_allow_html=True,
        )
        st.caption("AI Resume Intelligence Platform")
        st.markdown("---")

        pages = [
            "🏠 Home",
            "📄 Resume Analysis",
            "📊 Dashboard",
            "🎯 Skill Gap",
            "🔥 AI Critic",
            "✨ Improvements",
            "🎤 Interview Prep",
            "🎙️ Voice Practice",
            "🔄 Compare Versions",
        ]
        for page in pages:
            if st.button(page, use_container_width=True):
                st.session_state.current_page = page
                st.rerun()

        st.markdown("---")
        st.markdown("#### 🧭 Job Domain")
        st.selectbox(
            "Scoring vocabulary",
            DOMAIN_CHOICES,
            key="domain_override",
            help=(
                "Auto detects the domain from the job description. "
                "Override it if the detection misses (e.g., niche roles)."
            ),
        )
        if st.session_state.domain_override == "Custom":
            custom_text = st.text_area(
                "Custom domain keywords",
                value=", ".join(st.session_state.get("custom_keywords", [])),
                placeholder="e.g. GIS, ArcGIS, land surveying, zoning",
                help="Enter skills and tools separated by commas or new lines.",
                key="custom_domain_keywords_input",
            )
            st.session_state.custom_keywords = [
                keyword.strip().lower()
                for keyword in custom_text.replace("\n", ",").split(",")
                if keyword.strip()
            ]

        st.markdown("---")
        st.markdown("### 🤖 AI Engine")
        st.caption("Gemini 3.6 Flash + Groq fallback")

        st.markdown("---")
        with st.expander("ℹ️ About"):
            st.info(
                "ResumeIQ combines deterministic ATS scoring, skill matching "
                "and Gemini-powered semantic analysis to show how well a resume "
                "fits a job — before you apply."
            )

        # Reset button
        if st.button("🗑️ Reset Session", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()


def render_home_page():
    """Render the home / landing page."""
    st.markdown(
        """
        <div class="hero-panel">
            <div class="hero-kicker">Resume intelligence workspace</div>
            <h1>Make your next application sharper.</h1>
            <p>Turn a resume and a job description into a clear action plan: compatibility, skill gaps, stronger language, and focused interview practice.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown('<div class="section-label">01 · Upload</div>', unsafe_allow_html=True)
        st.markdown("#### Bring your resume")
        st.caption("PDF, DOCX, TXT, or a clear image")
    with c2:
        st.markdown('<div class="section-label">02 · Compare</div>', unsafe_allow_html=True)
        st.markdown("#### Add the target role")
        st.caption("Paste the job description or upload it")
    with c3:
        st.markdown('<div class="section-label">03 · Act</div>', unsafe_allow_html=True)
        st.markdown("#### Leave with a plan")
        st.caption("See what to keep, fix, and learn next")

    if st.button("🚀 Start Analysis", use_container_width=True):
        st.session_state.current_page = "📄 Resume Analysis"
        st.rerun()

    st.markdown("---")
    st.markdown('<div class="section-label">Your toolkit</div>', unsafe_allow_html=True)
    st.markdown("### One workspace, four useful signals")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("ATS Score", "0-100", help="Estimated ATS compatibility")
    with col2:
        st.metric("Job Match", "%", help="Semantic match via Gemini AI")
    with col3:
        st.metric("Skill Gap", "matched vs missing", help="Deterministic skill comparison")
    with col4:
        st.metric("Interview Prep", "18 questions", help="Tailored to resume + role")


def render_kpi_row():
    """Render the top KPI metric cards."""
    analysis = st.session_state.get("analysis", {})
    sg = st.session_state.get("skill_gap", {})

    match_score = analysis.get("job_match_score", 0)
    matched_pct = sg.get("match_percentage", 0) if isinstance(sg, dict) else 0
    missing_count = sg.get("missing_count", 0)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("ATS Score", f"{st.session_state.ats_score}/100")
    with col2:
        st.metric("Job Match", f"{match_score}%")
    with col3:
        st.metric("Skill Match", f"{matched_pct}%")
    with col4:
        st.metric("Missing Skills", missing_count)


def render_skill_match_chart(skill_gap: dict):
    """Render skill match donut chart, aggregated via a Pandas DataFrame."""
    df = build_skill_gap_dataframe(skill_gap)

    if df.empty:
        st.info("No skills data available.")
        return

    # DataFrame aggregation pipeline
    counts = df["Match"].value_counts()
    labels_map = {"Matched": "Matched ✅", "Partial": "Partial ◐", "Missing": "Missing ❌"}
    color_map = {"Matched ✅": "#00CC96", "Partial ◐": "#FFA15A", "Missing ❌": "#EF553B"}
    labels = [labels_map.get(m, m) for m in counts.index]
    values = counts.tolist()
    colors = [color_map.get(lbl, "#9E9E9E") for lbl in labels]

    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.6,
                marker_colors=colors,
            )
        ]
    )
    fig.update_layout(
        title="Skill Match Distribution",
        height=350,
        margin=dict(t=40, b=10),
        showlegend=True,
    )
    st.plotly_chart(fig, use_container_width=True)


def render_ats_breakdown_chart(breakdown: dict):
    """Render ATS score breakdown from a Pandas DataFrame pipeline."""
    if not breakdown:
        return

    df = build_breakdown_dataframe(breakdown)  # DataFrame: Category | Score

    fig = go.Figure(
        data=[
            go.Bar(
                x=df["Score"],
                y=df["Category"],
                orientation="h",
                marker_color="#4F8BF9",
                text=[f"{v}%" for v in df["Score"]],
                textposition="auto",
            )
        ]
    )
    fig.update_layout(
        title=f"ATS Score Breakdown ({len(df)} components · pandas pipeline)",
        xaxis=dict(range=[0, 100], title="Score"),
        height=320,
        margin=dict(t=40, b=30),
    )
    st.plotly_chart(fig, use_container_width=True)


def render_dashboard_page():
    """Render the main dashboard page."""
    st.title("📊 Dashboard")
    st.markdown("---")

    if not st.session_state.get("resume_data") or not st.session_state.get("jd_data"):
        st.warning("⚠️ No analysis yet. Run a resume analysis first.")
        if st.button("→ Go to Resume Analysis"):
            st.session_state.current_page = "📄 Resume Analysis"
            st.rerun()
        return

    render_kpi_row()
    st.markdown("---")

    band = score_band(st.session_state.get("ats_score"))
    st.markdown(
        f"<div style='border-left:4px solid {band['color']};padding:.55rem 1rem;background:#fff;'>"
        f"<strong>{band['emoji']} {band['label']} compatibility</strong>"
        f"<span style='color:#63707c;'> &nbsp; Your ATS score reflects the current resume and role.</span></div>",
        unsafe_allow_html=True,
    )
    st.markdown("---")

    domain = resolve_domain(
        st.session_state.get("jd_text", ""),
        st.session_state.get("domain_override", "Auto"),
    )
    if st.session_state.get("domain_override", "Auto") != "Auto":
        st.caption(f"🧭 Scoring domain: **{domain['label']}** (manual override)")
    elif domain["primary"]:
        top3 = sorted(domain["scores"].items(), key=lambda kv: kv[1], reverse=True)[:3]
        hint = " · ".join(f"{k} ({v})" for k, v in top3 if v)
        st.caption(f"🧭 Detected domain: **{domain['label']}** — {hint}")

    summary = st.session_state.analysis.get("summary", "")
    if summary:
        st.info(f"**AI Summary:** {summary}")

    left, right = st.columns(2)
    with left:
        render_ats_breakdown_chart(st.session_state.get("ats_breakdown", {}))
    with right:
        render_skill_match_chart(st.session_state.get("skill_gap", {}))

    st.markdown("---")
    with st.expander("🧠 AI Reasoning & Details"):
        details = {
            "Matched Skills": st.session_state.skill_gap.get("matched_skills", []),
            "Partial Skills": st.session_state.skill_gap.get("partial_skills", []),
            "Missing Skills": st.session_state.skill_gap.get("missing_skills", []),
            "Recommendations": st.session_state.analysis.get("recommendations", []),
            "Weak Sections": st.session_state.analysis.get("weak_sections", []),
        }
        for title, items in details.items():
            st.markdown(f"**{title}** ({len(items)})")
            if items:
                for item in items:
                    st.markdown(f"- {item}")
            else:
                st.caption("_None recorded._")


def render_version_comparison(v1_score, v2_score):
    """Render version comparison metrics."""
    delta = (v2_score or 0) - (v1_score or 0)
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Resume V1 ATS", v1_score if v1_score is not None else "—")
    with col2:
        st.metric("Resume V2 ATS", v2_score if v2_score is not None else "—")
    with col3:
        sign = "+" if delta >= 0 else ""
        st.metric("Improvement", f"{sign}{delta}", delta=f"{sign}{delta} ↑")
