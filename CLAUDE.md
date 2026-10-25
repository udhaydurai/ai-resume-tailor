@AGENTS.md

# Claude Code specifics

## Skills (`.claude/skills/`)

| Skill | Use it when |
|---|---|
| `build-slice` | Starting any roadmap slice: spec, spec critique, tests first, code, gates, review |
| `review-panel` | Before calling a slice done: parallel adversarial reviewers, then a judge |
| `eval-prompts` | Any change to a prompt, model or effort: measure invented facts before and after |

## Subagents (`.claude/agents/`)

- **Reviewers are read-only.** Their tools are Read, Grep, Glob and Bash, and a per-agent hook blocks any Bash command that changes files, git, packages or the network.
- **Lenses:** `reviewer-security` (personal data, secrets, SSRF, prompt injection, output escaping), `reviewer-correctness` (criteria, truthfulness, model replies, documents), `red-team` (should this exist, or be simpler?).
- **Judge:** `review-judge` merges the findings, re-runs every proof, and issues the verdict.
- **Spec critic:** `spec-critic` attacks a slice spec before any code exists.
- **Output format:** every reviewer returns the JSON in `docs/review/finding.schema.json`; `make validate-review` rejects anything else.

## Guardrail hooks (`.claude/settings.json`)

These apply to subagents too, and `tests/hooks/` tests every one of them:
- `block_private_data.py`: keeps resumes, private folders, the tracker database and `.env` away from Claude. **Privacy mode** is strict by default; a human can switch to open mode (see `docs/PRIVACY.md`).
- `protect_guardrails.py`: Claude can't edit settings, hooks, agents, the privacy config, scanners, CI, pre-commit or `.gitignore`. Reading and running them is fine.
- `format_python.sh`: ruff formats each Python file after it is edited.
- `gate_on_stop.sh`: Claude can't finish while `make check-fast` fails on changed code.

## Working style

- Keep context small: read `AGENTS.md` and the module you touch, not the whole repo.
- When unsure about a rule, ask. Don't guess.
