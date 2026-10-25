---
name: build-slice
description: Build the next roadmap slice spec-first and test-first, so it is built once. Use when starting any item from docs/ROADMAP.md.
---

# Build a slice

1. **Pick.** The first unchecked slice in `docs/ROADMAP.md`, unless the human named one. Branch `slice/<id>-<name>` from an up-to-date `master`.
2. **Spec.** Copy `docs/slices/TEMPLATE.md` to `docs/slices/<id>.md`. Keep it under a page. Every acceptance criterion must be something a test can assert.
3. **Critique.** Run the `spec-critic` agent on the spec. Fix every BLOCKER and MAJOR, or write down why not. Show the human the spec and wait for a go-ahead if the slice changes a prompt, adds a dependency or touches privacy.
4. **Tests first.** Write the failing tests from the spec's test plan. Run them and confirm they fail for the right reason.
5. **Code.** The smallest change that makes them pass. Follow `AGENTS.md`; model calls go only through `_call_model`.
6. **Prompts.** If a prompt, model or effort changed, run the `eval-prompts` skill and keep the before/after table for the PR.
7. **Gates.** `make check-fast` until green.
8. **Review.** Run the `review-panel` skill. Fix confirmed BLOCKERs, then MAJORs or list them in the PR.
9. **Hand over.** Tick the slice in `docs/ROADMAP.md`, commit with a Conventional Commit message, push, and open a **draft** PR with: the spec link, what changed, test evidence, the eval table if any, and the panel verdict. Mark it ready once. A human merges.
