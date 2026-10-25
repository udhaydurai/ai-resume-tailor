"""AI analysis engine. Claude by default; any OpenAI-compatible API as an untested option.

Tested with Claude only. Other providers go through the OpenAI chat-completions format,
which OpenAI, Gemini, Ollama, OpenRouter and many others accept. Prompts are tuned for
Claude, so another model may need prompt changes: fork and adapt this file.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Literal

import anthropic
import requests

PROVIDERS = ("anthropic", "openai")
DEFAULT_MODEL = "claude-opus-5-5"
DEFAULT_BASE_URL = "https://api.openai.com/v1"
Effort = Literal["low", "medium", "high", "xhigh", "max"]
EFFORTS: tuple[Effort, ...] = ("low", "medium", "high", "xhigh", "max")
DEFAULT_EFFORT: Effort = "medium"

TRUTHFULNESS_RULE = (
    "Use only facts stated in the candidate's original resume. Never invent or inflate "
    "employers, job titles, dates, degrees, certifications, skills, or numbers. If the job "
    "asks for something the resume does not show, leave it out rather than claim it."
)


class AIError(RuntimeError):
    """The model could not produce an answer (refusal, empty reply, provider error)."""


def _client() -> anthropic.Anthropic:
    return anthropic.Anthropic()


def provider() -> str:
    value = os.environ.get("RESUME_TAILOR_PROVIDER", "anthropic").strip().lower()
    return value if value in PROVIDERS else "anthropic"


def model() -> str:
    default = DEFAULT_MODEL if provider() == "anthropic" else ""
    return os.environ.get("RESUME_TAILOR_MODEL", default)


def effort() -> Effort:
    value = os.environ.get("RESUME_TAILOR_EFFORT", DEFAULT_EFFORT)
    return next((e for e in EFFORTS if e == value), DEFAULT_EFFORT)


def setup_problem() -> str | None:
    """What is missing before the app can call a model, in plain words."""
    if provider() == "anthropic":
        if not os.environ.get("ANTHROPIC_API_KEY"):
            return (
                "No ANTHROPIC_API_KEY found. Copy .env.example to .env and add your key, "
                "then restart the app."
            )
        return None
    if not model():
        return "RESUME_TAILOR_PROVIDER is openai: set RESUME_TAILOR_MODEL to a model it offers."
    return None


def _call_model(system: str, user: str, max_tokens: int = 16000) -> str:
    """The only place the app calls a model."""
    if provider() == "openai":
        problem = setup_problem()
        if problem:
            raise AIError(problem)
        return _call_openai_compatible(system, user)
    return _call_anthropic(system, user, max_tokens)


def _call_anthropic(system: str, user: str, max_tokens: int) -> str:
    response = _client().beta.messages.create(
        model=model(),
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
        output_config={"effort": effort()},
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
    )
    if response.stop_reason == "refusal":
        raise AIError("Claude declined this request. Try rewording the job description.")
    text = "".join(block.text for block in response.content if block.type == "text").strip()
    if not text:
        raise AIError("Claude returned an empty reply. Please try again.")
    return text


def _call_openai_compatible(system: str, user: str) -> str:
    """Untested by the maintainers: any endpoint that speaks OpenAI chat completions."""
    base_url = os.environ.get("RESUME_TAILOR_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
    key = os.environ.get("RESUME_TAILOR_API_KEY") or os.environ.get("OPENAI_API_KEY")
    headers = {"Authorization": f"Bearer {key}"} if key else {}
    body = {
        "model": model(),
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
    }
    try:
        resp = requests.post(
            f"{base_url}/chat/completions", json=body, headers=headers, timeout=300
        )
    except requests.RequestException as exc:
        raise AIError(f"Could not reach {base_url}. Check RESUME_TAILOR_BASE_URL.") from exc
    if resp.status_code in (401, 403):
        raise AIError("Your API key was rejected. Check RESUME_TAILOR_API_KEY in .env.")
    if resp.status_code == 429:
        raise AIError("The provider is rate-limiting this key. Wait a minute and try again.")
    if not resp.ok:
        raise AIError(f"The provider returned an error ({resp.status_code}). Please try again.")
    try:
        choice = resp.json()["choices"][0]
        text = str((choice.get("message") or {}).get("content") or "").strip()
        filtered = choice.get("finish_reason") == "content_filter"
    except (ValueError, KeyError, IndexError, TypeError, AttributeError) as exc:
        raise AIError("The provider sent a reply this app does not understand.") from exc
    if filtered:
        raise AIError("The model declined this request. Try rewording the job description.")
    if not text:
        raise AIError("The model returned an empty reply. Please try again.")
    return text


# ---------------------------------------------------------------------------
# Job description analysis
# ---------------------------------------------------------------------------


def analyze_job_description(job_description: str) -> dict[str, Any]:
    """Extract requirements, skills, and keywords from a job description.

    Returns a dict with keys: title, company, requirements, skills,
    keywords, experience_level, and summary.
    """
    system = (
        "You are an expert recruiter and ATS specialist. "
        "Respond ONLY with valid JSON, no markdown fences."
    )
    prompt = f"""Analyze this job description and return JSON with these exact keys:
- "title": the job title (string)
- "company": the company name (string, or "Unknown" if not found)
- "requirements": list of key requirements (list of strings)
- "skills": list of required/preferred skills (list of strings)
- "keywords": list of ATS keywords to include in a resume (list of strings)
- "experience_level": "Entry", "Mid", "Senior", or "Lead/Principal"
- "summary": 2-3 sentence summary of what the role involves

Job Description:
{job_description}"""

    text = _call_model(system, prompt)
    return _parse_json(text)


# ---------------------------------------------------------------------------
# Fit scoring
# ---------------------------------------------------------------------------


FIT_WEIGHTS = {"core": 3, "required": 2, "preferred": 1}
FIT_CREDIT = {"met": 1.0, "partial": 0.5, "missing": 0.0}


def _tier(row: dict[str, Any], key: str, allowed: dict[str, Any]) -> str | None:
    value = str(row.get(key, "")).strip().lower()
    return value if value in allowed else None


def _usable(requirements: Any) -> list[dict[str, Any]]:
    """Rows with a known weight and status; everything else is left out."""
    if not isinstance(requirements, list):
        return []
    rows = []
    for row in requirements:
        if not isinstance(row, dict):
            continue
        weight, status = _tier(row, "weight", FIT_WEIGHTS), _tier(row, "status", FIT_CREDIT)
        if weight and status:
            rows.append({**row, "weight": weight, "status": status})
    return rows


def fit_score_from(requirements: Any) -> int:
    """Score 0-100 from weighted requirements, computed in code so it is repeatable.

    The model only classifies each requirement; the arithmetic never varies between runs.
    """
    rows = _usable(requirements)
    possible = sum(FIT_WEIGHTS[r["weight"]] for r in rows)
    if not possible:
        return 0
    earned = sum(FIT_WEIGHTS[r["weight"]] * FIT_CREDIT[r["status"]] for r in rows)
    return int(earned * 100 / possible + 0.5)


def score_fit(job_description: str, resume_text: str) -> dict[str, Any]:
    """Score how well a resume matches a job description (0-100).

    The model lists every requirement with a weight, status and evidence; the score and
    the gap list are derived here. Returns score, explanation, impression, strengths,
    gaps, suggestions and requirements.
    """
    system = (
        "You are a career advisor and ATS expert. Respond ONLY with valid JSON, no markdown fences."
    )
    prompt = f"""Compare the resume against the job description and return JSON with:
- "requirements": EVERY requirement in the job description, with no limit on how many. \
Split compound items into separate requirements. Each item is an object with:
  - "requirement": short name of the requirement
  - "weight": "core" (the role is defined by it), "required", or "preferred"
  - "status": "met", "partial", or "missing", judged only from what the resume shows
  - "evidence": the resume phrase that supports it, or "" if missing
- "explanation": 2-3 sentences explaining the overall fit
- "impression": 2-3 sentences on how a hiring manager for this role would read the \
resume as a whole: what kind of candidate it makes the person look like
- "strengths": list of matching strengths (list of strings, max 5)
- "suggestions": list of actionable suggestions to improve fit (list of strings, max 5)

Job Description:
{job_description}

Resume:
{resume_text}"""

    result = _parse_json(_call_model(system, prompt))
    if "error" in result:
        return result
    rows = _usable(result.get("requirements"))
    if not rows:
        return {"error": "Couldn't read the requirements from the reply. Please try again."}
    order = list(FIT_WEIGHTS)
    gaps = sorted(
        (r for r in rows if r["status"] != "met"),
        key=lambda r: (order.index(r["weight"]), r["status"] != "missing"),
    )
    return {
        **result,
        "requirements": rows,
        "score": fit_score_from(rows),
        "gaps": [
            f"[{r['weight']}, {r['status']}] {r.get('requirement', '')}".rstrip() for r in gaps
        ],
    }


# ---------------------------------------------------------------------------
# Keyword match report
# ---------------------------------------------------------------------------


def keyword_match_report(job_description: str, resume_text: str) -> dict[str, Any]:
    """Generate a keyword match report between job description and resume.

    Returns a dict with keys: matched, missing, and match_percentage.
    """
    system = (
        "You are an ATS optimization specialist. Respond ONLY with valid JSON, no markdown fences."
    )
    prompt = f"""Identify ATS keywords from the job description and check which appear in the resume.
Return JSON with:
- "matched": list of keywords found in the resume (list of strings)
- "missing": list of important keywords NOT in the resume (list of strings)
- "match_percentage": integer 0-100

Job Description:
{job_description}

Resume:
{resume_text}"""

    text = _call_model(system, prompt)
    return _parse_json(text)


# ---------------------------------------------------------------------------
# Tailored resume generation
# ---------------------------------------------------------------------------


def generate_tailored_resume(
    job_description: str,
    resume_text: str,
    user_profile: dict[str, str],
) -> str:
    """Generate a tailored resume in structured plain text.

    Returns the full tailored resume as a string.
    """
    system = (
        "You are a professional resume writer and ATS optimization expert. "
        "Write resumes that are concise, achievement-focused, and ATS-friendly. "
        + TRUTHFULNESS_RULE
    )
    name = user_profile.get("name", "")
    email = user_profile.get("email", "")
    phone = user_profile.get("phone", "")
    linkedin = user_profile.get("linkedin", "")

    prompt = f"""Rewrite the resume below to be tailored for the target job description.

Rules:
1. Start with the candidate's contact info: {name} | {email} | {phone} | {linkedin}
2. Write a 2-3 sentence professional summary tailored to the role.
3. Reorder sections and bullet points to emphasize the most relevant experience.
4. Rewrite bullet points using strong action verbs. Keep every number from the original; add none.
5. Incorporate keywords from the job description naturally.
6. Keep formatting simple and ATS-friendly (no tables, columns, or graphics).
7. Use consistent section headers: PROFESSIONAL SUMMARY, EXPERIENCE, SKILLS, EDUCATION, CERTIFICATIONS (if applicable).
8. Output plain text only: no markdown, no commentary before or after the resume.

Job Description:
{job_description}

Original Resume:
{resume_text}"""

    return _call_model(system, prompt)


# ---------------------------------------------------------------------------
# Cover letter generation
# ---------------------------------------------------------------------------


def generate_cover_letter(
    job_description: str,
    resume_text: str,
    user_profile: dict[str, str],
) -> str:
    """Generate a 4-paragraph cover letter.

    Returns the cover letter as a string.
    """
    system = (
        "You are an expert cover letter writer. "
        "Write compelling, personalized cover letters. " + TRUTHFULNESS_RULE
    )
    name = user_profile.get("name", "")
    email = user_profile.get("email", "")
    phone = user_profile.get("phone", "")

    prompt = f"""Write a professional cover letter for the job below using the candidate's resume.

Structure (4 paragraphs):
1. Hook: Open with an engaging statement about why you're excited about this specific role and company.
2. Alignment: Highlight how your background and values align with the company's mission.
3. Technical fit: Provide 2-3 specific examples from your experience that demonstrate you can excel in this role.
4. Closing: Express enthusiasm, mention availability, and include a call to action.

Output plain text only, with no markdown and no commentary.

Candidate: {name} | {email} | {phone}

Job Description:
{job_description}

Resume:
{resume_text}"""

    return _call_model(system, prompt)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_json(text: str) -> dict[str, Any]:
    """Extract and parse JSON from Claude's response."""
    # Strip markdown code fences if present
    cleaned = re.sub(r"```(?:json)?\s*", "", text)
    cleaned = re.sub(r"```", "", cleaned).strip()
    for candidate in (cleaned, *re.findall(r"\{[\s\S]*\}", cleaned)):
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    return {"error": "Failed to parse AI response", "raw": text}
