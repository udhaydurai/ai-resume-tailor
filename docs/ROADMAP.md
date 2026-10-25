# Roadmap

One slice per branch (`slice/<id>-<name>`). Spec in `docs/slices/<id>.md` first.

## 0. Foundations

- [x] 0.1 Claude Code harness: AGENTS.md, privacy and guardrail hooks with tests, review panel, CI, repo scanner
- [x] 0.2 Working on current models: model and effort settings, thinking-safe replies, refusal handling, truthfulness rule and warning, safe URL fetch, PDF escaping, pypdf

## 1. Better tailoring

- [ ] 1.1 Structured outputs: `messages.parse` with Pydantic models instead of regex JSON parsing
- [ ] 1.2 Truthfulness baseline: grow `evals/cases.json` to 10 synthetic pairs and record the score per model and effort
- [ ] 1.3 Cost meter: show tokens and dollars per session in the sidebar; optional monthly cap setting
- [ ] 1.4 Prompt caching: send the resume and job description once as a cached prefix across the five calls
- [ ] 1.5 Hosted mode: one tracker per user, or turn the tracker off when hosted
- [ ] 1.6 Prompt-injection hardening for fetched job pages (wrap as data, strip instructions, test with hostile pages)
- [ ] 1.7 Keep edits: tailoring again shouldn't throw away the user's edits without asking
- [x] 1.8 Weighted fit score: every requirement tagged core, required or preferred; score computed in code from verified evidence; impression line
