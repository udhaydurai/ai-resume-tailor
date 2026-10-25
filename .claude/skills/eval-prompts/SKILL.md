---
name: eval-prompts
description: Measure invented facts in generated resumes and cover letters before and after a change to a prompt, model or effort. Use for any change to src/ai_engine.py prompts or settings.
---

# Eval prompts

The eval runs the real generators on synthetic resume and job pairs in `evals/cases.json` and counts invented facts: numbers that aren't in the source resume, and skills the job wants that the resume lacks. It costs real money (a few cents per run on the default model), so tell the human the cost and get a yes first. Baselines are on Claude, the tested provider. `RESUME_TAILOR_PROVIDER=openai` runs it on another model for a one-off comparison, but those results are not a gate.

1. **Baseline.** On `master` (or before your change): `make eval`. Save the table.
2. **Change.** Make the prompt or setting change.
3. **Measure.** `make eval` again. To compare models or effort without code changes: `RESUME_TAILOR_MODEL=claude-sonnet-5-5 make eval`, `RESUME_TAILOR_EFFORT=low make eval`.
4. **Decide.** Read each flagged sentence first: a cover letter may name a missing skill honestly ("the role calls for Tableau, which I'm learning"), and a cover letter may quote numbers from the job posting. Count only real claims. The change may not add invented facts. A higher count than the baseline is a failed change, even if the text reads better. Run twice if results look noisy; outputs vary between runs.
5. **Record.** Put both tables in the PR.
6. **New cases.** When a bug shows a new way to invent facts, add a synthetic case to `evals/cases.json` (`@example.test` emails, `555-01xx` phones) that catches it.
