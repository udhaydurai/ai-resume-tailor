---
name: review-panel
description: Multi-agent adversarial review of the current branch before a slice is called done. Runs the lens reviewers in parallel with fresh context, then the judge verifies every proof and issues one verdict.
---

# Review panel

**Precondition:** `make check-fast` is green. LLM review never replaces the deterministic gates; it runs after them.

1. **Collect the inputs.** The slice id, `docs/slices/<id>.md`, `git diff master...HEAD --stat` and the full diff. Pass only these. The reviewers must not see your reasoning.
2. **Choose the panel by size of change:**
   - **Full panel** (any prompt, model call, URL fetch, file parsing, export or hook change): `reviewer-security`, `reviewer-correctness` and `red-team`.
   - **Quick panel** (docs, tests only, or a refactor of fewer than about 50 lines): `reviewer-security` and `reviewer-correctness`.
3. **Run the reviewers in parallel**, in a single message with several Agent calls. Each one returns exactly one JSON report.
4. **Validate.** Save each report to `.review/<lens>.json` and run `make validate-review`. Send an invalid report back to the same reviewer once, with the validator output. If it's still invalid, record it as a process failure.
5. **Judge.** Start `review-judge` with the reports. It deduplicates, re-runs proofs and decides the verdict.
6. **Act on the verdict:**
   - Fix every confirmed BLOCKER, adding a regression test for each, then run steps 3–5 again with only the lenses that raised it. Allow at most 2 rounds, then escalate to the human.
   - Fix confirmed MAJORs, or list them in the PR with the reason.
   - Show the red-team's alternatives to the human as decisions. Don't act on them silently.
7. **Record.** Paste the judge's block into the PR under "Review panel verdict". Delete `.review/`.
