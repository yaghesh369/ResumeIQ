import streamlit as st
from ..analysis.skill_matcher import analyze_skill_gap, get_skill_priority, build_skill_gap_dataframe


def render_skill_gap_page():
    """Render the skill gap analysis page with data editor."""
    st.title("🎯 Skill Gap Analysis")
    st.markdown("---")

    if not st.session_state.get("resume_data") or not st.session_state.get("jd_data"):
        st.warning("⚠️ No analysis yet. Run a resume analysis first on the **Resume Analysis** page.")
        return

    sg = st.session_state.get("skill_gap")

    required_keys = {
        "matched_skills", "partial_skills", "missing_skills", "match_percentage",
        "matched_count", "partial_count", "missing_count",
    }
    if not isinstance(sg, dict) or not required_keys.issubset(sg) or not sg.get("jd_skills_detected"):
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
            sg = analyze_skill_gap(
                st.session_state.resume_data,
                st.session_state.jd_data,
                domain_keywords,
            )
            st.session_state.skill_gap = sg
        except Exception as error:
            st.error(f"Skill-gap calculation failed: {error}")
            return

    col1, col2, col3 = st.columns(3)
    with col1:
        st.success(f"✅ Exact matches: **{sg.get('matched_count', 0)}**")
    with col2:
        st.warning(f"◐ Partial: **{sg.get('partial_count', 0)}**")
    with col3:
        st.error(f"❌ Missing: **{sg.get('missing_count', 0)}**")

    st.progress(sg.get("match_percentage", 0) / 100)
    st.caption(f"Overall skill match: {sg.get('match_percentage', 0)}%")

    # AI-provided skill lists (semantic) merged with deterministic ones
    ai_matched = st.session_state.analysis.get("matched_skills", [])
    ai_missing = st.session_state.analysis.get("missing_skills", [])

    if ai_matched or ai_missing:
        with st.expander("🤖 Gemini-identified skills"):
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**AI matched:** " + (", ".join(ai_matched) or "_None_"))
            with c2:
                st.markdown("**AI missing:** " + (", ".join(ai_missing) or "_None_"))

    st.markdown("---")

    matched = sg.get("matched_skills", [])
    partial = sg.get("partial_skills", [])
    missing = sg.get("missing_skills", [])

    # Pandas DataFrame pipeline -> editable data editor
    df = build_skill_gap_dataframe(sg)

    st.markdown("### Skill Detail Table (editable · pandas DataFrame)")
    if not df.empty:
        edited_df = st.data_editor(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Skill": st.column_config.TextColumn("Skill"),
                "Requirement": st.column_config.TextColumn("Requirement", disabled=True),
                "Match": st.column_config.SelectboxColumn(
                    "Match",
                    options=["Matched", "Partial", "Missing"],
                ),
                "Priority": st.column_config.SelectboxColumn(
                    "Priority",
                    options=["High", "Medium", "Low"],
                    default="Medium",
                ),
            },
            key="skill_gap_editor",
        )

        # Priority summary computed with pandas
        priority_counts = edited_df["Priority"].value_counts().to_dict()
        p1, p2, p3 = st.columns(3)
        with p1:
            st.metric("High Priority", int(priority_counts.get("High", 0)))
        with p2:
            st.metric("Medium Priority", int(priority_counts.get("Medium", 0)))
        with p3:
            st.metric("Low Priority", int(priority_counts.get("Low", 0)))

        match_pct = (
            (edited_df["Match"] == "Matched").mean() * 100 if len(edited_df) else 0
        )
        st.progress(match_pct / 100)
        st.caption(f"Table match rate: {match_pct:.0f}%")
    else:
        detected_resume = sg.get("resume_skills_detected", [])
        detected_jd = sg.get("jd_skills_detected", [])
        if not detected_resume or not detected_jd:
            st.warning(
                "No comparable skills were detected. Check the parser diagnostics on "
                "Resume Analysis and use a clear Skills section or custom domain keywords."
            )
        else:
            st.info("No skill differences were found for this resume and job description.")

    # Deterministic priority ranking of missing skills
    if missing and st.session_state.jd_data:
        st.markdown("---")
        st.markdown("### 📈 Suggested Learning Priorities")
        priorities = get_skill_priority(missing, st.session_state.jd_data)
        for i, item in enumerate(priorities, 1):
            icon = "🔴" if item["priority"] == "High" else "🟡"
            st.markdown(f"{icon} **Priority {i}** — Add **{str(item['skill']).title()}** ({item['priority']} relevance in JD)")

    if not any([matched, partial, missing]):
        st.info("No explicit skills section detected. Upload a resume with a Skills section for detailed matching.")
