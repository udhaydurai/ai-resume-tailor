"""AI analysis engine powered by Claude API."""

from __future__ import annotations

import json
import re

import anthropic


def _client() -> anthropic.Anthropic:
    return anthropic.Anthropic()


def _call_claude(system: str, user: str, max_tokens: int = 4096) -> str:
    response = _client().messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return response.content[0].text


# ---------------------------------------------------------------------------
# Job description analysis
# ---------------------------------------------------------------------------

def analyze_job_description(job_description: str) -> dict:
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

    text = _call_claude(system, prompt)
    return _parse_json(text)


# ---------------------------------------------------------------------------
# Fit scoring
# ---------------------------------------------------------------------------

def score_fit(job_description: str, resume_text: str) -> dict:
    """Score how well a resume matches a job description (0-100).

    Returns a dict with keys: score, explanation, strengths,
    gaps, and suggestions.
    """
    system = (
        "You are a career advisor and ATS expert. "
        "Respond ONLY with valid JSON, no markdown fences."
    )
    prompt = f"""Compare the resume against the job description and return JSON with:
- "score": integer 0-100 representing alignment
- "explanation": 2-3 sentences explaining the score
- "strengths": list of matching strengths (list of strings, max 5)
- "gaps": list of gaps or missing qualifications (list of strings, max 5)
- "suggestions": list of actionable suggestions to improve fit (list of strings, max 5)

Job Description:
{job_description}

Resume:
{resume_text}"""

    text = _call_claude(system, prompt)
    return _parse_json(text)


# ---------------------------------------------------------------------------
# Keyword match report
# ---------------------------------------------------------------------------

def keyword_match_report(job_description: str, resume_text: str) -> dict:
    """Generate a keyword match report between job description and resume.

    Returns a dict with keys: matched, missing, and match_percentage.
    """
    system = (
        "You are an ATS optimization specialist. "
        "Respond ONLY with valid JSON, no markdown fences."
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

    text = _call_claude(system, prompt)
    return _parse_json(text)


# ---------------------------------------------------------------------------
# Tailored resume generation
# ---------------------------------------------------------------------------

def generate_tailored_resume(
    job_description: str,
    resume_text: str,
    user_profile: dict,
) -> str:
    """Generate a tailored resume in structured plain text.

    Returns the full tailored resume as a string.
    """
    system = (
        "You are a professional resume writer and ATS optimization expert. "
        "Write resumes that are concise, achievement-focused, and ATS-friendly."
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
4. Rewrite bullet points using strong action verbs and quantified achievements.
5. Incorporate keywords from the job description naturally.
6. Keep formatting simple and ATS-friendly (no tables, columns, or graphics).
7. Use consistent section headers: PROFESSIONAL SUMMARY, EXPERIENCE, SKILLS, EDUCATION, CERTIFICATIONS (if applicable).

Job Description:
{job_description}

Original Resume:
{resume_text}"""

    return _call_claude(system, prompt, max_tokens=4096)


# ---------------------------------------------------------------------------
# Cover letter generation
# ---------------------------------------------------------------------------

def generate_cover_letter(
    job_description: str,
    resume_text: str,
    user_profile: dict,
) -> str:
    """Generate a 4-paragraph cover letter.

    Returns the cover letter as a string.
    """
    system = (
        "You are an expert cover letter writer. "
        "Write compelling, personalized cover letters."
    )
    name = user_profile.get("name", "")
    email = user_profile.get("email", "")
    phone = user_profile.get("phone", "")

    prompt = f"""Write a professional cover letter for the job below using the candidate's resume.

Structure (4 paragraphs):
1. **Hook**: Open with an engaging statement about why you're excited about this specific role and company.
2. **Alignment**: Highlight how your background and values align with the company's mission.
3. **Technical Fit**: Provide 2-3 specific examples from your experience that demonstrate you can excel in this role.
4. **Closing**: Express enthusiasm, mention availability, and include a call to action.

Candidate: {name} | {email} | {phone}

Job Description:
{job_description}

Resume:
{resume_text}"""

    return _call_claude(system, prompt, max_tokens=2048)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_json(text: str) -> dict:
    """Extract and parse JSON from Claude's response."""
    # Strip markdown code fences if present
    cleaned = re.sub(r"```(?:json)?\s*", "", text)
    cleaned = re.sub(r"```", "", cleaned).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Try to find JSON object in the text
        match = re.search(r"\{[\s\S]*\}", cleaned)
        if match:
            return json.loads(match.group())
        return {"error": "Failed to parse AI response", "raw": text}
