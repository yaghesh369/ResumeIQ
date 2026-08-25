import os
import json
import re

from dotenv import load_dotenv

load_dotenv()

def _setting(name: str, default: str = "") -> str:
    """Read local environment settings or Streamlit Cloud secrets."""
    value = os.environ.get(name)
    if value:
        return value
    try:
        import streamlit as st

        return str(st.secrets.get(name, default))
    except Exception:
        return default


GEMINI_API_KEY = _setting("GEMINI_API_KEY")
GROQ_API_KEY = _setting("GROQ_API_KEY")
_configured_groq_model = _setting("GROQ_MODEL")
_configured_gemini_model = _setting("GEMINI_MODEL")
GROQ_MODEL = (
    "openai/gpt-oss-120b"
    if not _configured_groq_model or _configured_groq_model == "llama-3.3-70b-versatile"
    else _configured_groq_model
)
GEMINI_MODEL = (
    "gemini-3.6-flash"
    if not _configured_gemini_model or _configured_gemini_model == "gemini-2.0-flash"
    else _configured_gemini_model
)


def _gemini_client():
    if not GEMINI_API_KEY:
        return None
    try:
        from google import genai

        return genai.Client(api_key=GEMINI_API_KEY)
    except Exception as e:
        print(f"Gemini client init failed: {e}")
        return None


def _call_groq(system_prompt: str, user_prompt: str):
    """Fallback AI provider: Groq free API (OpenAI-compatible endpoint)."""
    if not GROQ_API_KEY:
        return None
    try:
        import requests

        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": GROQ_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.3,
                "response_format": {"type": "json_object"},
            },
            timeout=60,
        )
        if response.status_code == 200:
            content = response.json()["choices"][0]["message"]["content"]
            return _extract_json(content)
        print(f"Groq API error {response.status_code}: {response.text[:300]}")
        return None
    except Exception as e:
        print(f"Groq call failed: {e}")
        return None


def _extract_json(text):
    """Best-effort JSON extraction from an LLM response."""
    if not text:
        return None
    text = text.strip()
    # Strip markdown code fences if present
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        result = json.loads(text)
        return result if isinstance(result, dict) else None
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                result = json.loads(match.group(0))
                return result if isinstance(result, dict) else None
            except json.JSONDecodeError:
                return None
    return None


def call_gemini(system_prompt: str, user_prompt: str) -> dict:
    """Call Gemini AI with a JSON system prompt; fall back to Groq; then to defaults."""
    # 1) Try Gemini
    client = _gemini_client()
    if client is not None:
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=user_prompt,
                config={
                    "system_instruction": system_prompt,
                    "response_mime_type": "application/json",
                    "temperature": 0.3,
                },
            )
            result = _extract_json(response.text)
            if result:
                return result
        except Exception as e:
            print(f"Gemini API error: {e}")

    # 2) Fallback to Groq free model
    result = _call_groq(system_prompt, user_prompt)
    if result:
        return result

    # 3) Graceful degradation
    return {}


def _safe_list(value):
    return value if isinstance(value, list) else []


def analyze_resume_against_jd(resume_text: str, jd_text: str) -> dict:
    """Analyze resume against job description using Gemini."""
    system_prompt = (
        "You are a professional resume analysis engine. "
        "Analyze the candidate's resume against the target job description. "
        "Identify matched skills, partial skills and missing skills, weak sections "
        "and concrete recommendations. Do not invent information. "
        'Return ONLY structured JSON: {"summary": str, "job_match_score": int 0-100, '
        '"matched_skills": [str], "partial_skills": [str], "missing_skills": [str], '
        '"weak_sections": [str], "recommendations": [str], "critic_points": [str]}'
    )
    user_prompt = f"RESUME:\n{resume_text}\n\nJOB DESCRIPTION:\n{jd_text}\n\nReturn the structured analysis."

    result = call_gemini(system_prompt, user_prompt)
    if not isinstance(result, dict):
        result = {}

    # Validate / normalize
    score = result.get("job_match_score", 0)
    try:
        score = max(0, min(100, int(score)))
    except (ValueError, TypeError):
        score = 0

    return {
        "ai_available": bool(result),
        "summary": result.get("summary", ""),
        "job_match_score": score,
        "matched_skills": _safe_list(result.get("matched_skills")),
        "partial_skills": _safe_list(result.get("partial_skills")),
        "missing_skills": _safe_list(result.get("missing_skills")),
        "weak_sections": _safe_list(result.get("weak_sections")),
        "recommendations": _safe_list(result.get("recommendations")),
        "critic_points": _safe_list(result.get("critic_points")),
    }


def generate_resume_critic(resume_text: str, jd_text: str) -> dict:
    """Generate ruthless resume criticism."""
    system_prompt = (
        "You are a senior recruiter and resume reviewer. "
        "Analyze the candidate's resume specifically against the target job description. "
        "Do NOT give generic career advice. For every criticism provide the problem, "
        "why it matters, and a specific improvement. Be direct but constructive. "
        "Do not invent achievements. Return ONLY structured JSON: "
        '{"overall_assessment": str, "weak_bullets": [{"original": str, "problem": str, '
        '"improved": str}], "missing_keywords": [str], "vague_claims": [str], '
        '"improvement_suggestions": [str]}'
    )
    user_prompt = f"RESUME:\n{resume_text}\n\nJOB DESCRIPTION:\n{jd_text}"

    result = call_gemini(system_prompt, user_prompt)
    if not isinstance(result, dict):
        result = {}

    return {
        "overall_assessment": result.get("overall_assessment", ""),
        "weak_bullets": result.get("weak_bullets") if isinstance(result.get("weak_bullets"), list) else [],
        "missing_keywords": _safe_list(result.get("missing_keywords")),
        "vague_claims": _safe_list(result.get("vague_claims")),
        "improvement_suggestions": _safe_list(result.get("improvement_suggestions")),
    }


def generate_resume_improvement(resume_text: str, jd_text: str) -> dict:
    """Generate improved resume sections. Never invent facts."""
    system_prompt = (
        "You are a professional resume editor. Improve the candidate's resume "
        "for the target job. IMPORTANT: never invent employment, projects, skills, "
        "metrics, certifications or achievements. Only improve wording using information "
        "actually provided. Use concise ATS-friendly language. Return ONLY structured JSON: "
        '{"summary": str, "experience_bullets": [str], "project_descriptions": [str], '
        '"skills_section": str, "change_notes": [str]}'
    )
    user_prompt = f"RESUME:\n{resume_text}\n\nJOB DESCRIPTION:\n{jd_text}"

    result = call_gemini(system_prompt, user_prompt)
    if not isinstance(result, dict):
        result = {}

    return {
        "summary": result.get("summary", ""),
        "experience_bullets": _safe_list(result.get("experience_bullets")),
        "project_descriptions": _safe_list(result.get("project_descriptions")),
        "skills_section": result.get("skills_section", ""),
        "change_notes": _safe_list(result.get("change_notes")),
    }


def generate_interview_questions(resume_data: dict, jd_data: dict) -> dict:
    """Generate interview questions based on resume and JD."""
    system_prompt = (
        "You are an interview coach preparing questions for a candidate based on their "
        "resume and a target job description, whatever the industry (tech, healthcare, "
        "finance, education, design...). Generate exactly: 5 domain-knowledge questions "
        "(the 'technical' key), 5 project questions, 3 HR questions, and 5 role-specific "
        "questions tailored to this profession. "
        "Return ONLY structured JSON: {\"technical\": [str], \"project\": [str], "
        "\"hr\": [str], \"role_specific\": [str]}"
    )
    user_prompt = (
        f"RESUME:\n{resume_data.get('clean_text', '')}\n\n"
        f"JOB DESCRIPTION:\n{jd_data.get('clean_text', '')}"
    )

    result = call_gemini(system_prompt, user_prompt)
    if not isinstance(result, dict):
        result = {}

    return {
        "technical": _safe_list(result.get("technical")),
        "project": _safe_list(result.get("project")),
        "hr": _safe_list(result.get("hr")),
        "role_specific": _safe_list(result.get("role_specific")),
    }


# ---------------------------------------------------------------------------
# Multimodal capabilities (audio + vision)
# ---------------------------------------------------------------------------

def evaluate_voice_answer(audio_bytes: bytes, question: str, resume_text: str, jd_text: str) -> dict:
    """Multimodal evaluation of a recorded interview answer.

    Sends the raw audio to Gemini (which transcribes it internally) together
    with the question context and returns scored feedback.
    """
    system_prompt = (
        "You are an expert interview coach. The user recorded a spoken answer to an "
        "interview question. Listen to the audio, transcribe it mentally, and evaluate "
        "the ANSWER QUALITY in the context of their resume and the target job. "
        "Score each dimension 0-10: communication (clarity, pacing, structure), "
        "technical_depth (depth of correct domain knowledge for this profession), "
        "clarity (focus, no rambling), "
        "relevance (answers the actual question). Also give overall 0-10, a one-line "
        "transcript summary, and 2-3 concrete improvement tips. Do not invent facts the "
        "candidate did not say. Return ONLY JSON: "
        '{"communication": int, "technical_depth": int, "clarity": int, '
        '"relevance": int, "overall": float, "transcript_summary": str, "tips": [str]}'
    )
    user_text = (
        f"INTERVIEW QUESTION:\n{question}\n\n"
        f"CANDIDATE RESUME (context):\n{resume_text[:2000]}\n\n"
        f"TARGET JOB DESCRIPTION (context):\n{jd_text[:1500]}\n\n"
        "The attached audio is the candidate's spoken answer."
    )

    if not audio_bytes:
        return _voice_unavailable("No audio data was received. Please record again.")

    client = _gemini_client()
    if client is not None:
        try:
            from google.genai import types

            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=[
                    types.Content(
                        role="user",
                        parts=[
                            types.Part.from_bytes(data=audio_bytes, mime_type="audio/wav"),
                            types.Part.from_text(text=user_text),
                        ],
                    )
                ],
                config={
                    "system_instruction": system_prompt,
                    "response_mime_type": "application/json",
                    "temperature": 0.3,
                },
            )
            result = _extract_json(response.text if response else "")
            if result:
                return _normalize_voice_eval(result)
        except Exception as e:
            print(f"Gemini audio evaluation error: {e}")

    return _voice_unavailable("AI service unavailable or the recording could not be understood.")


def _voice_unavailable(message: str) -> dict:
    """Return a consistent non-success result for the voice UI."""
    return {
        "communication": 0, "technical_depth": 0, "clarity": 0,
        "relevance": 0, "overall": 0.0,
        "transcript_summary": "",
        "tips": [message],
        "available": False,
    }


def _normalize_voice_eval(result: dict) -> dict:
    def _score(key):
        try:
            return max(0, min(10, int(float(result.get(key, 0)))))
        except (TypeError, ValueError):
            return 0

    overall = result.get("overall", 0)
    try:
        overall = round(max(0.0, min(10.0, float(overall))), 1)
    except (TypeError, ValueError):
        overall = 0.0

    return {
        "communication": _score("communication"),
        "technical_depth": _score("technical_depth"),
        "clarity": _score("clarity"),
        "relevance": _score("relevance"),
        "overall": overall,
        "transcript_summary": str(result.get("transcript_summary", "")),
        "tips": _safe_list(result.get("tips")),
        "available": True,
    }


def extract_text_from_image(image_bytes: bytes, mime_type: str = "image/jpeg") -> str:
    """Multimodal OCR: extract raw text from a photo/scan of a resume."""
    system_prompt = (
        "You are a high-accuracy document OCR engine. The attached image is a photo or "
        "scan of a resume/CV. Transcribe ALL visible text exactly as written, preserving "
        "line breaks and section headers (SUMMARY, SKILLS, EXPERIENCE, PROJECTS, "
        "EDUCATION, CERTIFICATIONS). Output ONLY the transcribed text — no commentary, "
        "no markdown fences."
    )

    client = _gemini_client()
    if client is not None:
        try:
            from google.genai import types

            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=[
                    types.Content(
                        role="user",
                        parts=[
                            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                            types.Part.from_text(text="Transcribe this resume image."),
                        ],
                    )
                ],
                config={
                    "system_instruction": system_prompt,
                    "temperature": 0.0,
                },
            )
            if response and response.text:
                return response.text.strip()
        except Exception as e:
            print(f"Gemini vision extraction error: {e}")

    return ""
