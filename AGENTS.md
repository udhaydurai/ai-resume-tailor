# AI Resume Tailor: rules for AI coding agents

A small Streamlit app that tailors a resume and cover letter to a job posting with Claude. People run it on their own laptop with their own API key, and they paste their real resume into it. Treat every resume as private.

Before writing code, read `docs/ROADMAP.md` and `docs/PRIVACY.md`. If a task conflicts with them, stop and say so.

## Non-negotiables

1. **No real personal data in git.** Fixtures and demo files are synthetic: `@example.test` or `@example.com` emails, `555-01xx` phone numbers. No resumes, tracker databases or `.env` files. `scripts/scan_repo.py`, gitleaks and `.gitignore` enforce this. Never weaken them.
2. **Never invent facts.** Generated resumes and cover letters use only what the original resume says. Every generation prompt includes `TRUTHFULNESS_RULE`, and the app shows `warn_unsupported` on the result. A prompt change ships with a `make eval` result in the PR.
3. **One door to Claude.** All model calls go through `src.ai_engine._call_claude`. The model and effort come from settings (`RESUME_TAILOR_MODEL`, `RESUME_TAILOR_EFFORT`), never hard-coded at a call site. Always check `stop_reason` and read only `text` blocks.
4. **Untrusted input stays data.** Job postings and resumes go in the user message, never the system prompt. URL fetches go through `src.utils.fetch_job_description` (public addresses only, redirects re-checked, size and time limits).
5. **Escape on output.** No `unsafe_allow_html`. Text placed in ReportLab `Paragraph` goes through `escape`. SQL uses parameters.
6. **Friendly failures.** A missing key, refusal, rate limit or network error shows a plain message in the app, not a stack trace.
7. **Small and boring.** Plain functions and modules. A new dependency needs a one-line reason in the PR.

## Layout

```
app.py               Streamlit UI only: no business logic
src/                 ai_engine, truthcheck, resume_parser, resume_generator, cover_letter, job_tracker, utils
tests/               mirrors src/; tests/hooks/ covers the guardrail hooks
evals/               live truthfulness eval (make eval, costs money)
scripts/             repo scanner and review validator (guardrails)
docs/                ROADMAP, PRIVACY, slices/, review/
```

## Workflow

1. Take the next unchecked slice in `docs/ROADMAP.md`. One branch per slice: `slice/<id>-<name>`.
2. Write the spec first (`docs/slices/TEMPLATE.md`), then failing tests, then the smallest code that makes them pass.
3. `make check-fast` must pass before you hand anything over. CI runs `make check`.
4. Run the review panel (see `CLAUDE.md`). No open BLOCKERs.
5. Conventional Commits (`feat(engine): use structured outputs`). Never commit to `master`. A human merges.

## Commands

| Command | What it does |
|---|---|
| `make setup` | Install dependencies (uv) and the pre-commit hook |
| `make run` | Start the app at http://localhost:8501 |
| `make fmt` | Format and auto-fix |
| `make check-fast` | Lint, types (mypy strict), tests (coverage ≥ 85%), personal-data scan |
| `make check` | The above plus gitleaks and the dependency audit |
| `make eval` | Live truthfulness eval against Claude (a few cents) |

## Definition of done

- Every acceptance criterion has a test that fails without the change.
- Prompt changes have a `make eval` result in the PR, with no new invented facts.
- The review panel's verdict has no open BLOCKERs.
