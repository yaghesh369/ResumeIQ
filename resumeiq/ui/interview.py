import streamlit as st
from ..ai.gemini_client import generate_interview_questions


def render_interview_page():
    """Render the interview preparation page."""
    st.title("🎤 Interview Preparation")
    st.caption("Questions generated from YOUR resume and the target job description.")
    st.markdown("---")

    if not st.session_state.get("resume_data") or not st.session_state.get("jd_data"):
        st.warning("⚠️ No analysis yet. Run a resume analysis first on the **Resume Analysis** page.")
        return

    if not st.session_state.get("interview_questions") or not any(
        st.session_state.get("interview_questions", {}).values()
    ):
        if st.button("🎤 Generate Interview Questions", use_container_width=True):
            with st.spinner("Gemini is preparing your questions..."):
                try:
                    result = generate_interview_questions(
                        st.session_state.resume_data,
                        st.session_state.jd_data,
                    )
                    if not any(result.values()):
                        st.error(
                            "⚠️ AI returned no questions (service may be busy). "
                            "Please try again."
                        )
                    else:
                        st.session_state.interview_questions = result
                        st.rerun()
                except Exception as e:
                    st.error(f"⚠️ AI service temporarily unavailable: {e}")
        return

    iq = st.session_state.interview_questions

    tabs = st.tabs(["📚 Domain (5)", "📦 Project (5)", "👥 HR (3)", "🎯 Role-specific (5)"])

    with tabs[0]:
        _render_question_list(iq.get("technical", []))
    with tabs[1]:
        _render_question_list(iq.get("project", []))
    with tabs[2]:
        _render_question_list(iq.get("hr", []))
    with tabs[3]:
        _render_question_list(iq.get("role_specific", []))

    with st.expander("💡 Answering Tips"):
        st.markdown(
            "- **Domain:** relate answers directly to the JD's required skills.\n"
            "- **Project:** use the STAR method — Situation, Task, Action, Result.\n"
            "- **HR:** prepare concise stories about motivation and teamwork.\n"
            "- **Role-specific:** research the company and mirror its vocabulary."
        )

    # Downloadable question set
    all_text = (
        "DOMAIN QUESTIONS\n" + "\n".join(f"{i}. {q}" for i, q in enumerate(iq.get("technical", []), 1)) + "\n\n" +
        "PROJECT QUESTIONS\n" + "\n".join(f"{i}. {q}" for i, q in enumerate(iq.get("project", []), 1)) + "\n\n" +
        "HR QUESTIONS\n" + "\n".join(f"{i}. {q}" for i, q in enumerate(iq.get("hr", []), 1)) + "\n\n" +
        "ROLE-SPECIFIC QUESTIONS\n" + "\n".join(f"{i}. {q}" for i, q in enumerate(iq.get("role_specific", []), 1))
    )
    st.download_button(
        "⬇️ Download Question Set",
        data=all_text,
        file_name="resumeiq_interview_questions.txt",
        mime="text/plain",
        use_container_width=True,
    )

    if st.button("🔄 Regenerate Questions"):
        st.session_state.interview_questions = {}
        st.rerun()


def _render_question_list(questions):
    """Render a numbered question list."""
    if not questions:
        st.info("_No questions returned. Try regenerating._")
        return
    for i, q in enumerate(questions, 1):
        st.markdown(f"**{i}.** {q}")
