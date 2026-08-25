# ResumeIQ — Technical Design Document

## 1. Overview

ResumeIQ is a Streamlit application that scores how well a resume fits a job
description. It combines a **deterministic Python scoring engine** (reproducible,
explainable) with **Gemini-powered semantic analysis** (context-aware, natural
language). The AI never computes the ATS score and never invents candidate facts.

## 2. System Architecture

```text
┌────────────┐   ┌──────────────────────────────────────────────┐
│    User    │──▶│              Streamlit UI (app.py)            │
└────────────┘   │  9 pages · sidebar router · session_state     │
                 └───────┬───────────────────────────┬──────────┘
                         ▼                           ▼
              ┌─────────────────────┐     ┌─────────────────────┐
              │  parser/ package    │     │   ai/ package       │
              │ PyMuPDF · vision OCR│     │ Gemini + Groq fb    │
              └─────────┬───────────┘     └──────────┬──────────┘
                        ▼                            ▼
              ┌─────────────────────────────────────────────────┐
              │        analysis/ package (deterministic)        │
              │  ats_scorer · skill_matcher(DataFrames) · scoring│
              └─────────┬───────────────────────────┬───────────┘
                        ▼                           ▼
               st.session_state cache       Plotly / data_editor UI
```

## 3. Data Flow

1. **Ingest** — `validators.validate_file()` gates uploads (type + ≤10 MB).
2. **Extract** — PDF → PyMuPDF; TXT → decode with latin-1 fallback;
   DOCX → python-docx (paragraphs + tables); image →
   `extract_text_from_image()` (Gemini vision OCR, temperature 0).
3. **Clean** — `utils/text_cleaner.clean_text()`: whitespace collapse,
   blank-line squeeze; `extract_sections()` fuzzy-maps 6 canonical sections
   (decorated headers, inline values, unknown-header isolation);
   `extract_skills_list()` tokenizes skills with label/junk filtering.
4. **Score deterministically** (`analysis/ats_scorer.py`):

```text
ATS = keyword×0.25 + skill_relevance×0.25 + experience×0.20
    + projects×0.15 + education×0.10 + structure×0.05
```

**Multi-domain vocabulary** (`analysis/domains.py`): a shared professional
core + 9 curated profiles (Technology, Marketing, Sales, Finance, Healthcare,
HR, Design, Education, Operations). `detect_domains()` counts word-boundary
keyword hits in the JD; profiles with ≥3 hits (top 2) merge into the active
vocabulary. A sidebar override forces any profile manually — scoring stays
fully deterministic either way. A `Custom` mode also accepts user-provided
comma/newline-separated skills and tools, which are merged into ATS and skill-gap
matching for niche domains not covered by the curated profiles.

5. **Pandas pipeline** — `build_skill_gap_dataframe()` produces a tidy table
   (Skill | Requirement | Match | Priority), sorted Matched→Partial→Missing.
   Feeds `st.data_editor` and Plotly aggregations (`value_counts`).
6. **Semantic layer** — one JSON-mode Gemini call per task: match %, critic,
   rewriter, interview questions. Responses normalized in Python
   (`_safe_list`, score clamping) before touching the UI.
7. **Cache** — every result lands in `st.session_state`; reruns render from
   cache without new API calls.

## 4. API Integration Strategy

| Aspect | Decision |
|---|---|
| Single choke point | All calls through `ai/gemini_client.call_gemini()` |
| Output contract | `response_mime_type="application/json"`, temperature 0.0–0.3 |
| Validation | Regex JSON extraction (`_extract_json`) survives code fences |
| Fallback chain | Gemini → Groq OpenAI-compatible endpoint → empty defaults |
| Multimodal | Audio WAV bytes for interview evaluation; JPEG bytes for OCR |
| Cost control | Calls fire only on explicit button/form submits |

## 5. Module Logic

- **ats_scorer** — pure functions; `_clean_skill()` strips `Required:` labels;
  regex year extraction powers the experience curve (≥100% →100, ≥70% →80…).
- **skill_matcher** — exact set intersection = matched; substring-in-resume =
  partial; remainder = missing. Priority = JD occurrence count ≥2 → High.
- **experience_analyzer** — years delta verdicts + seniority banding +
  title heuristics.
- **scoring** — band colors, weight-normalized `weighted_score()`.
- **voice_interview** — audio bytes → multimodal prompt returning four
  0–10 dimension scores; history tracked per session.

## 6. Error Handling Matrix

| Failure | Behavior |
|---|---|
| Unsupported file | Inline ❌ message, pipeline halted |
| Image-only PDF | ValueError from parser → user-guided to camera scan |
| Empty upload | ValueError with actionable copy |
| Gemini quota/network | Groq fallback, else graceful defaults (never crash) |
| Malformed AI JSON | `_extract_json` salvage → normalized defaults |

## 7. Testing Strategy

73 unit tests across parser, scoring, domain, real-world parsing, AI client, and validator
modules: parsing/cleaning, scoring known-values and bounds, skill extraction,
DataFrame pipeline shape/ordering, and upload validation.
Run: `python -m unittest discover -s tests -v`.

## 8. Security

Keys load from `.env` (python-dotenv) locally and Streamlit Secrets in prod.
`.gitignore` excludes `.env`, `.streamlit/secrets.toml`, caches, venvs.
No user data leaves the session except the resume/JD text sent to the AI APIs.

## 9. Limitations & Roadmap

Estimate-only score · scanned PDFs need the vision path · free-tier quotas.
Roadmap: multi-JD compare, improved-resume PDF export, embedding matching.
