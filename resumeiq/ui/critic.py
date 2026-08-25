import streamlit as st
from ..ai.gemini_client import generate_resume_critic


def _critic_has_content(critic: dict) -> bool:
    """True when the critique contains at least one usable field."""
    return bool(
        critic.get("overall_assessment")
        or critic.get("weak_bullets")
        or critic.get("missing_keywords")
        or critic.get("vague_claims")
        or critic.get("improvement_suggestions")
    )


def render_critic_page():
    """Render the AI resume critic page."""
    st.title("🔥 AI Resume Critic")
    st.caption("Ruthless, job-specific review — not generic career advice.")
    st.markdown("---")

    if not st.session_state.get("resume_data") or not st.session_state.get("jd_data"):
        st.warning("⚠️ No analysis yet. Run a resume analysis first on the **Resume Analysis** page.")
        return

    if not st.session_state.get("critic") or not _critic_has_content(
        st.session_state.get("critic", {})
    ):
        if st.button("🔍 Generate Critique", use_container_width=True):
            with st.spinner("Gemini is reviewing your resume against the JD..."):
                try:
                    result = generate_resume_critic(
                        st.session_state.resume_text,
                        st.session_state.jd_text,
                    )
                    if not _critic_has_content(result):
                        st.error(
                            "⚠️ AI returned an empty critique (service may be busy). "
                            "Please try again."
                        )
                    else:
                        st.session_state.critic = result
                        st.rerun()
                except Exception as e:
                    st.error(f"⚠️ AI service temporarily unavailable: {e}")
        return

    critic = st.session_state.critic

    overall = critic.get("overall_assessment", "")
    if overall:
        st.info(f"**Overall:** {overall}")

    # Weak bullets with before/after
    weak_bullets = critic.get("weak_bullets", [])
    if weak_bullets:
        st.markdown(f"### ❌ Weak Bullet Points ({len(weak_bullets)})")
        for i, item in enumerate(weak_bullets, 1):
            if isinstance(item, dict):
                with st.expander(f"Bullet {i}: {str(item.get('original', ''))[:70]}..."):
                    st.markdown("**Original**")
                    st.markdown(f"> {item.get('original', '—')}")
                    st.markdown("**Problem**")
                    st.error(item.get("problem", "—"))
                    st.markdown("**Suggested improvement**")
                    st.success(item.get("improved", "—"))
            else:
                st.markdown(f"- {item}")

    missing_kw = critic.get("missing_keywords", [])
    if missing_kw:
        with st.expander(f"📌 Missing Keywords ({len(missing_kw)})"):
            st.markdown(", ".join(f"`{k}`" for k in missing_kw))

    vague = critic.get("vague_claims", [])
    if vague:
        with st.expander(f"⚠ Vague Claims ({len(vague)})"):
            for v in vague:
                st.markdown(f"- {v}")

    suggestions = critic.get("improvement_suggestions", [])
    if suggestions:
        with st.expander(f"✨ Improvement Suggestions ({len(suggestions)})"):
            for i, s in enumerate(suggestions, 1):
                st.markdown(f"**{i}.** {s}")

    if st.button("🔄 Regenerate Critique"):
        st.session_state.critic = {}
        st.rerun()
