import streamlit as st
import plotly.graph_objects as go

from ..ai.gemini_client import evaluate_voice_answer, generate_interview_questions


def render_voice_interview_page():
    """Multimodal voice interview practice: AI question -> mic answer -> scored feedback."""
    st.title("🎤 Voice Interview Practice")
    st.caption(
        "AI asks a question from YOUR resume + target job. Record your spoken answer — "
        "Gemini listens to the audio and scores you on four dimensions."
    )
    st.markdown("---")

    if not st.session_state.get("resume_data") or not st.session_state.get("jd_data"):
        st.warning("⚠️ Run a resume analysis first so questions can be tailored (Resume Analysis page).")
        return

    # --- Question source -------------------------------------------------
    iq = st.session_state.get("interview_questions")
    if not iq:
        st.info("No question set generated yet.")
        if st.button("🎤 Generate Interview Questions"):
            with st.spinner("Gemini is preparing your questions..."):
                try:
                    st.session_state.interview_questions = generate_interview_questions(
                        st.session_state.resume_data,
                        st.session_state.jd_data,
                    )
                    st.rerun()
                except Exception as e:
                    st.error(f"⚠️ AI service temporarily unavailable: {e}")
        return

    # Flatten all categories into one pool
    pool = []
    for category, questions in iq.items():
        if not isinstance(questions, list):
            continue
        for q in questions:
            pool.append({"category": category.replace("_", " ").title(), "question": str(q)})

    if not pool:
        st.warning("Question set is empty — regenerate it.")
        return

    left, right = st.columns([3, 1])
    with left:
        idx = st.selectbox(
            f"Choose a question ({len(pool)} available)",
            range(len(pool)),
            format_func=lambda i: f"[{pool[i]['category']}] {pool[i]['question'][:90]}",
            key="voice_question_select",
        )
    with right:
        st.markdown("<br>", unsafe_allow_html=True)
        st.metric("Questions", len(pool))

    current = pool[idx]
    stored_question = st.session_state.get("voice_evaluation_question")
    if stored_question != current["question"]:
        st.session_state.pop("voice_evaluation", None)
        st.session_state.pop("voice_evaluation_question", None)
    st.markdown("---")
    st.markdown(f"### ❓ {current['question']}")
    st.caption(f"Category: {current['category']}")

    # --- Recording --------------------------------------------------------
    audio = st.audio_input("🎙️ Record your answer (speak clearly, 60–120 seconds)")

    col_eval, col_clear = st.columns([1, 1])
    run_eval = col_eval.button("📊 Evaluate My Answer", type="primary", use_container_width=True,
                               disabled=audio is None)
    clear = col_clear.button("🧹 Clear Current Result", use_container_width=True,
                             disabled=not st.session_state.get("voice_evaluation"))

    if clear:
        # Clear only the on-screen result — practice history is preserved
        st.session_state.pop("voice_evaluation", None)
        st.session_state.pop("voice_evaluation_question", None)
        st.rerun()

    if audio is not None and run_eval:
        audio_bytes = audio.getvalue()
        if len(audio_bytes) < 2000:
            st.error("Recording too short — please record a real answer (at least a few seconds).")
        else:
            with st.spinner("Gemini is listening to your answer..."):
                try:
                    evaluation = evaluate_voice_answer(
                        audio_bytes=audio_bytes,
                        question=current["question"],
                        resume_text=st.session_state.resume_text,
                        jd_text=st.session_state.jd_text,
                    )
                except Exception as error:
                    evaluation = {
                        "available": False,
                        "tips": [f"Voice evaluation failed: {error}"],
                    }
                if not evaluation.get("available", True):
                    st.error(
                        "⚠️ Recording evaluation failed: "
                        f"{evaluation.get('tips', ['Please try again.'])[0]}"
                    )
                else:
                    history = st.session_state.setdefault("voice_evaluations", [])
                    history.append({
                        "question": current["question"],
                        "category": current["category"],
                        **evaluation,
                    })
                    st.session_state.voice_evaluation = evaluation
                    st.session_state.voice_evaluation_question = current["question"]

    # --- Latest result ----------------------------------------------------
    evaluation = st.session_state.get("voice_evaluation")
    if evaluation:
        st.markdown("---")
        _render_evaluation(evaluation)

    # --- History ------------------------------------------------------------
    history = st.session_state.get("voice_evaluations", [])
    if len(history) > 1:
        with st.expander(f"📈 Practice History ({len(history)} attempts)"):
            rows = [
                {
                    "Attempt": i + 1,
                    "Overall": h["overall"],
                    "Communication": h["communication"],
                    "Domain": h["technical_depth"],
                    "Clarity": h["clarity"],
                    "Relevance": h["relevance"],
                    "Question": h["question"][:60] + "...",
                }
                for i, h in enumerate(history)
            ]
            st.data_editor(rows, use_container_width=True, hide_index=True)


def _render_evaluation(ev: dict):
    """Render score radar + tips for one evaluation."""
    dims = {
        "Communication": ev.get("communication", 0),
        "Domain Depth": ev.get("technical_depth", 0),
        "Clarity": ev.get("clarity", 0),
        "Relevance": ev.get("relevance", 0),
    }

    overall = ev.get("overall", 0)
    band_color = "#00C853" if overall >= 7 else "#FFAB00" if overall >= 5 else "#D50000"

    c1, c2 = st.columns([2, 3])

    with c1:
        fig = go.Figure(
            data=go.Scatterpolar(
                r=list(dims.values()) + [list(dims.values())[0]],
                theta=list(dims.keys()) + [list(dims.keys())[0]],
                fill="toself",
                line=dict(color="#4F8BF9"),
            )
        )
        fig.update_layout(
            polar=dict(radialaxis=dict(range=[0, 10], showticklabels=False)),
            height=300,
            margin=dict(t=30, b=10, l=40, r=40),
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.markdown(
            f"<h1 style='color:{band_color};margin:0;'>{overall}<span style='font-size:1.2rem;color:#888;'>/10</span></h1>"
            f"<span style='color:#888;'>Overall Answer Score</span>",
            unsafe_allow_html=True,
        )
        m1, m2, m3, m4 = st.columns(4)
        for col, (label, val) in zip([m1, m2, m3, m4], dims.items()):
            col.metric(label, f"{val}/10")

    summary = ev.get("transcript_summary", "")
    if summary:
        st.info(f"**What the AI heard:** {summary}")

    tips = ev.get("tips", [])
    if tips:
        with st.expander("💡 Improvement Tips"):
            for t in tips:
                st.markdown(f"- {t}")
