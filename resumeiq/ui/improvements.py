import streamlit as st
from ..ai.gemini_client import generate_resume_improvement


def _improvements_have_content(imp: dict) -> bool:
    return bool(
        imp.get("summary")
        or imp.get("experience_bullets")
        or imp.get("project_descriptions")
        or imp.get("skills_section")
    )


def render_improvements_page():
    """Render the resume improvements page with BEFORE/AFTER tabs."""
    st.title("✨ Resume Improvements")
    st.caption("ATS-friendly rewording of your existing content — nothing is invented.")
    st.markdown("---")

    if not st.session_state.get("resume_data") or not st.session_state.get("jd_data"):
        st.warning("⚠️ No analysis yet. Run a resume analysis first on the **Resume Analysis** page.")
        return

    if not st.session_state.get("improvements") or not _improvements_have_content(
        st.session_state.get("improvements", {})
    ):
        if st.button("✨ Generate Improved Sections", use_container_width=True):
            with st.spinner("Gemini is rewriting your resume sections..."):
                try:
                    result = generate_resume_improvement(
                        st.session_state.resume_text,
                        st.session_state.jd_text,
                    )
                    if not _improvements_have_content(result):
                        st.error(
                            "⚠️ AI returned no improvements (service may be busy). "
                            "Please try again."
                        )
                    else:
                        st.session_state.improvements = result
                        st.rerun()
                except Exception as e:
                    st.error(f"⚠️ AI service temporarily unavailable: {e}")
        return

    imp = st.session_state.improvements

    tab1, tab2, tab3, tab4 = st.tabs(["Summary", "Experience", "Projects", "Skills"])

    with tab1:
        st.markdown("**BEFORE (your original)**")
        original_summary = (
            st.session_state.resume_data.get("sections", {}).get("summary", "").strip()
            or st.session_state.resume_text[:400]
            or "_No text_"
        )
        st.text_area("Original", original_summary[:800], height=160, key="orig_summary", disabled=True)
        st.markdown("**AFTER (AI improved)**")
        st.text_area(
            "Improved summary",
            imp.get("summary", "") or "_No improvement returned_",
            height=160,
            key="imp_summary",
        )

    with tab2:
        bullets = imp.get("experience_bullets", [])
        if bullets:
            for i, b in enumerate(bullets, 1):
                st.markdown(f"**{i}.** {b}")
        else:
            st.info("_No experience improvements returned._")

    with tab3:
        projects = imp.get("project_descriptions", [])
        if projects:
            for i, p in enumerate(projects, 1):
                st.markdown(f"**Project {i}**\n\n{p}")
        else:
            st.info("_No project improvements returned._")

    with tab4:
        skills = imp.get("skills_section", "")
        if skills:
            st.text_area("Improved skills section", skills, height=200, key="imp_skills")
        else:
            st.info("_No skills section improvement returned._")

    notes = imp.get("change_notes", [])
    if notes:
        with st.expander("🧠 Why these changes"):
            for n in notes:
                st.markdown(f"- {n}")

    # Full download of improved content
    full_text = (
        f"IMPROVED SUMMARY\n{'='*60}\n{imp.get('summary', '')}\n\n"
        f"EXPERIENCE BULLETS\n{'='*60}\n" +
        "\n".join(f"- {b}" for b in imp.get("experience_bullets", [])) + "\n\n"
        f"PROJECT DESCRIPTIONS\n{'='*60}\n" +
        "\n\n".join(f"- {p}" for p in imp.get("project_descriptions", [])) + "\n\n"
        f"SKILLS SECTION\n{'='*60}\n{imp.get('skills_section', '')}\n"
    )
    st.download_button(
        "⬇️ Download Improved Resume Content",
        data=full_text,
        file_name="resumeiq_improved.txt",
        mime="text/plain",
        use_container_width=True,
    )

    if st.button("🔄 Regenerate Improvements"):
        st.session_state.improvements = {}
        st.rerun()
