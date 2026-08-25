import streamlit as st
from ..ai.gemini_client import analyze_resume_against_jd
from ..analysis.ats_scorer import calculate_ats_score
from ..analysis.skill_matcher import analyze_skill_gap
from ..parser.resume_parser import parse_resume_upload, SUPPORTED_EXTENSIONS
from ..parser.jd_parser import parse_job_description, parse_jd_upload
from ..utils.validators import validate_file


def render_resume_analysis_page():
    """Render the resume analysis page with upload + form."""
    st.title("📄 Resume Analysis")
    st.caption(
        "Upload your resume (PDF · DOCX · TXT · image), add the job description, "
        "then analyze — results are cached in session state."
    )
    st.markdown("---")

    with st.form("resume_analysis_form", clear_on_submit=False):
        st.markdown("#### 📑 Resume")
        uploaded_resume = st.file_uploader(
            f"Supported: {', '.join(SUPPORTED_EXTENSIONS)}",
            type=SUPPORTED_EXTENSIONS,
            key="resume_uploader",
            help="Images are read with Gemini vision OCR. Scanned PDFs should be uploaded as images.",
        )

        st.markdown("#### 💼 Job Description")
        jd_tab_paste, jd_tab_file = st.tabs(["Paste text", "Upload file"])

        jd_text = ""
        with jd_tab_paste:
            jd_text = st.text_area(
                "Paste the job description here",
                height=180,
                key="jd_paste",
                placeholder="Paste the full job description...",
            )
        with jd_tab_file:
            uploaded_jd = st.file_uploader(
                "Choose a JD file (txt/pdf/docx)",
                type=["pdf", "txt", "docx"],
                key="jd_uploader",
            )

        submitted = st.form_submit_button("🚀 Analyze Resume", use_container_width=True)

    if submitted:
        # Resolve JD source (file takes precedence)
        if uploaded_jd is not None:
            valid, message = validate_file(uploaded_jd)
            if not valid:
                st.error(f"❌ {message}")
                return
            try:
                jd_text = parse_jd_upload(uploaded_jd)["raw_text"]
            except Exception as e:
                st.error(f"❌ Could not read the JD file: {e}")
                return

        errors = []
        if not uploaded_resume:
            errors.append("Please upload a resume file.")
        else:
            valid, message = validate_file(uploaded_resume)
            if not valid:
                errors.append(message)
        if not jd_text or not jd_text.strip():
            errors.append("Please provide a job description.")

        for err in errors:
            st.error(err)
        if errors:
            return

        # Prevent a partial new run from being displayed with old derived results.
        for key in (
            "resume_data", "resume_text", "jd_data", "jd_text", "analysis",
            "critic", "improvements", "interview_questions", "ats_score",
            "ats_breakdown", "skill_gap", "detected_skills", "voice_evaluation",
            "voice_evaluations", "version_comparison", "custom_keywords",
        ):
            st.session_state[key] = {
                "resume_data": {}, "jd_data": {}, "analysis": {}, "critic": {},
                "improvements": {}, "interview_questions": {}, "ats_breakdown": {},
                "skill_gap": {}, "detected_skills": [], "voice_evaluations": [],
                "version_comparison": {"v1": None, "v2": None},
                "custom_keywords": [],
            }.get(key, 0 if key == "ats_score" else "")

        try:
            with st.spinner("Parsing resume..."):
                resume_data = parse_resume_upload(uploaded_resume)
                st.session_state.resume_data = resume_data
                st.session_state.resume_text = resume_data["clean_text"]
                from ..utils.text_cleaner import get_skills_from_sections

                st.session_state.detected_skills = get_skills_from_sections(
                    resume_data.get("sections", {})
                )
                _render_parse_diagnostics(resume_data)

            with st.spinner("Parsing job description..."):
                jd_data = parse_job_description(jd_text)
                st.session_state.jd_data = jd_data
                st.session_state.jd_text = jd_data["clean_text"]

            with st.spinner("Running deterministic ATS scoring..."):
                from ..analysis.domains import active_keywords

                override = st.session_state.get("domain_override", "Auto")
                custom_keywords = st.session_state.get("custom_keywords", [])
                domain_kw = (
                    active_keywords(jd_data["clean_text"], override, custom_keywords)
                    if override != "Auto"
                    else None
                )
                st.session_state.domain_label = override if override != "Auto" else ""
                ats_result = calculate_ats_score(resume_data, jd_data, domain_kw)
                st.session_state.ats_score = ats_result["ats_score"]
                st.session_state.ats_breakdown = ats_result["breakdown"]

            with st.spinner("Computing skill gap..."):
                st.session_state.skill_gap = analyze_skill_gap(resume_data, jd_data, domain_kw)

            with st.spinner("Gemini AI semantic analysis..."):
                st.session_state.analysis = analyze_resume_against_jd(
                    st.session_state.resume_text,
                    st.session_state.jd_text,
                )
                st.session_state.critic = {}
                st.session_state.improvements = {}
                st.session_state.interview_questions = {}
                st.session_state.skill_gap = analyze_skill_gap(
                    resume_data,
                    jd_data,
                    domain_kw,
                    st.session_state.analysis,
                )

            if st.session_state.analysis.get("ai_available"):
                st.success("✅ Analysis complete! Explore Dashboard, Skill Gap and AI pages.")
            else:
                st.warning(
                    "✅ Resume scoring is complete, but AI analysis is unavailable. "
                    "Check your API keys and model settings, then retry the analysis."
                )
            st.rerun()

        except ValueError as ve:
            st.error(f"❌ {ve}")
        except Exception as e:
            st.error(f"⚠️ Something went wrong during analysis: {e}")

    # Show cached result summary
    if st.session_state.get("resume_data") and st.session_state.get("jd_data"):
        # Rebuild this small deterministic result on every render so an old
        # session value can never hide valid parsed skills.
        try:
            from ..analysis.domains import active_keywords

            current_override = st.session_state.get("domain_override", "Auto")
            current_domain_keywords = (
                active_keywords(
                    st.session_state.jd_data.get("clean_text", ""),
                    current_override,
                    st.session_state.get("custom_keywords", []),
                )
                if current_override != "Auto"
                else None
            )
            st.session_state.skill_gap = analyze_skill_gap(
                st.session_state.resume_data,
                st.session_state.jd_data,
                current_domain_keywords,
                st.session_state.get("analysis", {}),
            )
        except Exception as error:
            st.session_state.skill_gap = {}
            st.warning(f"Skill-gap calculation failed: {error}")
        st.markdown("---")
        render_cached_summary()
        if st.session_state.get("resume_data"):
            _render_parse_diagnostics(st.session_state.resume_data)


def _render_parse_diagnostics(resume_data: dict):
    """Show what the parser actually extracted so users can verify quality."""
    sections = resume_data.get("sections", {})
    detected = [k for k in ("summary", "skills", "experience", "projects", "education", "certifications") if sections.get(k)]

    with st.expander("🔬 Parser diagnostics — verify extraction quality", expanded=False):
        c1, c2, c3 = st.columns(3)
        c1.metric("Characters", len(resume_data.get("clean_text", "")))
        c2.metric("Sections found", f"{len(detected)}/6")
        c3.metric("Skills detected", len(st.session_state.get("detected_skills", [])))

        for key in ("summary", "skills", "experience", "projects", "education", "certifications"):
            content = sections.get(key, "").strip()
            if content:
                label = key.title()
                st.markdown(f"**{label}**")
                preview = content if len(content) <= 400 else content[:400] + "…"
                st.text(preview)
            else:
                st.warning(f"⚠️ '{key.title()}' section not detected — header may use unusual wording.")

        if not detected:
            st.error(
                "No standard section headers found. The document parsed but appears to "
                "have no recognizable headers (SUMMARY / SKILLS / EXPERIENCE...). "
                "Scoring will fall back to keyword scanning."
            )


def render_cached_summary():
    """Render a compact summary of the cached analysis."""
    skill_gap = st.session_state.get("skill_gap")
    required_keys = {
        "matched_skills", "partial_skills", "missing_skills", "match_percentage",
        "matched_count", "partial_count", "missing_count",
    }
    if not isinstance(skill_gap, dict) or not required_keys.issubset(skill_gap) or (
        st.session_state.get("resume_data")
        and st.session_state.get("jd_data")
        and not skill_gap.get("jd_skills_detected")
    ):
        try:
            from ..analysis.domains import active_keywords

            override = st.session_state.get("domain_override", "Auto")
            domain_keywords = (
                active_keywords(
                    st.session_state.jd_data.get("clean_text", ""),
                    override,
                    st.session_state.get("custom_keywords", []),
                )
                if override != "Auto"
                else None
            )
            skill_gap = analyze_skill_gap(
                st.session_state.resume_data,
                st.session_state.jd_data,
                domain_keywords,
                st.session_state.get("analysis", {}),
            )
            st.session_state.skill_gap = skill_gap
        except Exception as error:
            st.warning(f"Skill-gap calculation could not be completed: {error}")
            skill_gap = {}

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("ATS Score", f"{st.session_state.ats_score}/100")
    with col2:
        match = st.session_state.analysis.get("job_match_score", 0)
        st.metric("Job Match", f"{match}%")
    with col3:
        sg = skill_gap
        st.metric(
            "Skill Match",
            f"{sg.get('match_percentage', 0)}%",
            f"{sg.get('matched_count', 0) + sg.get('partial_count', 0)} covered",
        )

    if not st.session_state.analysis.get("ai_available"):
        st.info("AI insights are unavailable for this run. Deterministic ATS and skill results are still valid.")

    sg = skill_gap or {}
    missing = sg.get("missing_skills", [])
    matched = sg.get("matched_skills", [])
    partial = sg.get("partial_skills", [])

    col1, col2, col3 = st.columns(3)
    with col1:
        st.success("**Matched**\n" + ("\n".join(f"✓ {s.title()}" for s in matched) or "_None_"))
    with col2:
        st.warning("**Partial**\n" + ("\n".join(f"◐ {s.title()}" for s in partial) or "_None_"))
    with col3:
        st.error("**Missing**\n" + ("\n".join(f"✗ {s.title()}" for s in missing) or "_None_"))

    recs = st.session_state.analysis.get("recommendations", [])
    if recs:
        with st.expander("📌 Top Recommendations"):
            for i, rec in enumerate(recs, 1):
                st.markdown(f"**Priority {i}** — {rec}")
