import hashlib

import streamlit as st

st.set_page_config(
    page_title="ResumeIQ — AI Resume Intelligence",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

from resumeiq.ui.dashboard import (
    apply_app_styles,
    init_session_state,
    render_sidebar,
    render_home_page,
    render_dashboard_page,
)
from resumeiq.ui.resume_analysis import render_resume_analysis_page
from resumeiq.ui.skill_gap import render_skill_gap_page
from resumeiq.ui.critic import render_critic_page
from resumeiq.ui.improvements import render_improvements_page
from resumeiq.ui.interview import render_interview_page
from resumeiq.ui.voice_interview import render_voice_interview_page


def render_compare_versions_page():
    """Render the resume version comparison page."""
    st.title("🔄 Compare Versions")
    st.caption("Score two resume versions against the same job description.")
    st.markdown("---")

    if not st.session_state.get("jd_text"):
        st.warning("⚠️ Please run an analysis first so a job description is available for scoring.")
        return

    from resumeiq.parser.resume_parser import parse_resume_upload, SUPPORTED_EXTENSIONS
    from resumeiq.analysis.ats_scorer import calculate_ats_score

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Resume V1")
        v1_file = st.file_uploader(
            f"Version 1 ({', '.join(SUPPORTED_EXTENSIONS)})", type=SUPPORTED_EXTENSIONS,
            key="v1_uploader",
        )

    with col2:
        st.markdown("### Resume V2")
        v2_file = st.file_uploader(
            f"Version 2 ({', '.join(SUPPORTED_EXTENSIONS)})", type=SUPPORTED_EXTENSIONS,
            key="v2_uploader",
        )

    def _fingerprint(uploaded) -> str:
        jd_text = st.session_state.jd_data.get("clean_text", "")
        jd_fingerprint = hashlib.sha256(jd_text.encode("utf-8")).hexdigest()
        return f"{getattr(uploaded, 'name', '')}:{getattr(uploaded, 'size', 0)}:{jd_fingerprint}"

    def ensure_scored(slot, uploaded):
        """Score a file once per unique upload (name+size); never re-scores stale."""
        fp = _fingerprint(uploaded)
        entry = st.session_state.version_comparison.get(slot)
        if isinstance(entry, dict) and entry.get("key") == fp:
            return
        with st.spinner(f"Scoring {slot.upper()} ({uploaded.name})..."):
            try:
                data = parse_resume_upload(uploaded)
                result = calculate_ats_score(data, st.session_state.jd_data)
                st.session_state.version_comparison[slot] = {
                    "key": fp, "score": result["ats_score"], "error": "",
                }
            except Exception as e:
                st.session_state.version_comparison[slot] = {
                    "key": fp, "score": None, "error": str(e),
                }

    def slot_result(slot, uploaded):
        """(score, error) for this exact file, or (None, '') when unscored."""
        entry = st.session_state.version_comparison.get(slot)
        if uploaded is None or not isinstance(entry, dict) or entry.get("key") != _fingerprint(uploaded):
            return None, ""
        return entry.get("score"), entry.get("error", "")

    if v1_file is not None:
        ensure_scored("v1", v1_file)
    if v2_file is not None:
        ensure_scored("v2", v2_file)

    v1, err1 = slot_result("v1", v1_file)
    v2, err2 = slot_result("v2", v2_file)
    for label, err in (("V1", err1), ("V2", err2)):
        if err:
            st.error(f"Could not score {label}: {err}")

    if v1 is not None or v2 is not None:
        st.markdown("---")
        rows = [
            {"Version": "V1", "ATS Score": v1 if v1 is not None else "—"},
            {"Version": "V2", "ATS Score": v2 if v2 is not None else "—"},
        ]
        st.dataframe(rows, use_container_width=True, hide_index=True)

        if v1 is not None and v2 is not None:
            delta = v2 - v1
            c1, c2 = st.columns(2)
            with c1:
                st.metric("Resume V1 ATS", v1)
                st.metric("Resume V2 ATS", v2, delta=f"{delta:+d}")
            with c2:
                arrow = "↑" if delta >= 0 else "↓"
                color = "green" if delta >= 0 else "red"
                st.markdown(
                    f"<h3 style='color:{color};'>Improvement: {delta:+d} ATS points {arrow}</h3>",
                    unsafe_allow_html=True,
                )
                if delta > 0:
                    st.success(f"V2 is stronger by {delta} points.")
                elif delta < 0:
                    st.error(f"V1 is actually stronger. Consider keeping V1.")
                else:
                    st.info("Both versions score equally.")

        if st.button("🔄 Clear Comparison"):
            st.session_state.version_comparison = {"v1": None, "v2": None}
            st.rerun()


def main():
    init_session_state()
    apply_app_styles()
    render_sidebar()

    pages = {
        "🏠 Home": render_home_page,
        "📄 Resume Analysis": render_resume_analysis_page,
        "📊 Dashboard": render_dashboard_page,
        "🎯 Skill Gap": render_skill_gap_page,
        "🔥 AI Critic": render_critic_page,
        "✨ Improvements": render_improvements_page,
        "🎤 Interview Prep": render_interview_page,
        "🎙️ Voice Practice": render_voice_interview_page,
        "🔄 Compare Versions": render_compare_versions_page,
    }

    page = st.session_state.current_page
    renderer = pages.get(page, render_home_page)
    renderer()


if __name__ == "__main__":
    main()
