# AI Resume Tailor

> Tailor your resume and cover letter for any job. Built and tested with Claude; works with other AI models too.

Paste a job posting, upload your resume, and get:

- **Job analysis**: requirements, skills and ATS keywords
- **Fit score** (0–100) with strengths, gaps and suggestions
- **Keyword match report**: which keywords you hit and miss
- **Tailored resume** as .docx or .pdf
- **Cover letter** as .docx
- **Job tracker** for your applications, with CSV export

**It won't make things up.** The prompts tell Claude to use only facts from your resume. The app also points out any number in the result that isn't in your original, so you can check it before you send anything.

## Quick start

You need Python 3.11+, [uv](https://docs.astral.sh/uv/getting-started/installation/) and an [Anthropic API key](https://console.anthropic.com/).

```bash
git clone https://github.com/udhaydurai/ai-resume-tailor.git
cd ai-resume-tailor
cp .env.example .env        # then put your key in .env: ANTHROPIC_API_KEY=sk-ant-...
uv sync
make run                    # opens http://localhost:8501
```

To try it out, use `demo/sample_resume.txt` and `demo/sample_job_description.txt`.

**Cost.** Each button press is one model call. With the default model, a full run (analysis, score, keywords, resume, cover letter) usually costs a few cents. For a cheaper run, use a smaller model (see Settings).

### Docker

```bash
docker build -t ai-resume-tailor .
docker run -p 8501:8501 --env-file .env ai-resume-tailor
```

## Settings

Put these in `.env` (all optional except the key):

| Variable | Default | What it does |
|---|---|---|
| `ANTHROPIC_API_KEY` | (required for Claude) | Your Anthropic API key |
| `RESUME_TAILOR_MODEL` | `claude-opus-5-5` | The model, for example `claude-sonnet-5-5` or `claude-haiku-5-5` for lower cost |
| `RESUME_TAILOR_EFFORT` | `medium` | Claude only: `low`, `medium`, `high`, `xhigh` or `max`. More effort is more thorough and costs more |
| `RESUME_TAILOR_PROVIDER` | `anthropic` | `anthropic`, or `openai` for any OpenAI-compatible API |
| `RESUME_TAILOR_BASE_URL` | `https://api.openai.com/v1` | With `openai`: the provider's endpoint |
| `RESUME_TAILOR_API_KEY` | (none) | With `openai`: the provider's key (`OPENAI_API_KEY` also works; local servers need none) |

## Models and providers

> **Tested with Claude only.** Claude is the default, and it's the only provider the maintainers test and evaluate. The prompts, the error handling and the truthfulness eval were all tuned on Claude.
>
> **Other models should work, but they aren't tested.** Anything that speaks the OpenAI chat-completions API can run the app: OpenAI, Google Gemini, local models through Ollama, OpenRouter and many more. Results vary by model. In particular, smaller models are more likely to invent facts, so check every output before you send it.
>
> **If it doesn't work for your model, fork the repo and adapt it.** Every model call goes through one function, `_call_model` in [`src/ai_engine.py`](src/ai_engine.py), so that's the place to change prompts or add a provider. Run `make eval` to measure invented facts on your model.

Example `.env` settings (untested by the maintainers):

```bash
# OpenAI
RESUME_TAILOR_PROVIDER=openai
RESUME_TAILOR_MODEL=<an OpenAI model name>
RESUME_TAILOR_API_KEY=sk-...

# Google Gemini (OpenAI-compatible endpoint)
RESUME_TAILOR_PROVIDER=openai
RESUME_TAILOR_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai
RESUME_TAILOR_MODEL=<a Gemini model name>
RESUME_TAILOR_API_KEY=<your Gemini key>

# Local model with Ollama (free, nothing leaves your machine)
RESUME_TAILOR_PROVIDER=openai
RESUME_TAILOR_BASE_URL=http://localhost:11434/v1
RESUME_TAILOR_MODEL=<a model you have pulled>
```

## Privacy

Your resume and the job posting go to the AI provider you configure (Anthropic by default). With a local model they never leave your machine. Nothing else does either. The job tracker is a local file that git ignores. See [docs/PRIVACY.md](docs/PRIVACY.md).

This app is built for running on your own machine. Don't host it for other people as it is: they would all share one job tracker.

## Architecture

```
┌────────────────────────── Streamlit UI (app.py) ──────────────────────────┐
│   Input    │   Analysis    │  Tailored Resume  │ Cover Letter │  Tracker  │
└─────┬──────┴───────┬───────┴─────────┬─────────┴──────┬───────┴─────┬─────┘
      │              │                 │                │             │
 resume_parser   ai_engine ──────► truthcheck     cover_letter   job_tracker
 utils (fetch)       │           resume_generator                 (SQLite)
                     ▼
     Claude (default) or any OpenAI-compatible API
```

| Module | Job |
|---|---|
| `src/ai_engine.py` | Every model call (one `_call_model`), providers, prompts, truthfulness rule |
| `src/truthcheck.py` | Flags numbers and skills that aren't in the original resume |
| `src/resume_parser.py` | Reads .pdf, .docx and .txt |
| `src/resume_generator.py`, `src/cover_letter.py` | .docx and .pdf output |
| `src/utils.py` | Fetches job postings from public URLs only |
| `src/job_tracker.py` | Local SQLite application tracker |

## Development

```bash
make setup        # dependencies and the pre-commit hook
make check-fast   # lint, types, tests (coverage ≥ 85%), personal-data scan
make check        # plus gitleaks and the dependency audit (what CI runs)
make eval         # live check for invented facts (costs a few cents)
```

### Working with Claude Code

The repo includes a [Claude Code](https://claude.com/claude-code) setup: rules in [AGENTS.md](AGENTS.md) and [CLAUDE.md](CLAUDE.md), skills for building and reviewing a slice, a review panel of read-only agents, and hooks that:

- keep your resumes, `.env` and the tracker database away from Claude. **Privacy mode** is strict by default; you can switch it to open so Claude can read your real resume (see [docs/PRIVACY.md](docs/PRIVACY.md)).
- stop Claude from editing its own guardrails
- stop Claude from finishing while the checks fail

`tests/hooks/` tests every hook. Next steps are in [docs/ROADMAP.md](docs/ROADMAP.md).

## License

MIT
