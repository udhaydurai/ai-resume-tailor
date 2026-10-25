# Slice <id>: <name>

## Problem

Who is stuck today, and what happens to them. One paragraph.

## Acceptance criteria

Each one is observable and has a test that fails without the change.

1. Given …, when …, then ….

## Out of scope

## Risks

- **Personal data:** where resume text, tracker rows or keys go.
- **Truthfulness:** could this let Claude invent a fact? How the eval shows it can't.
- **Cost:** new or bigger Claude calls, with a rough cost per use.
- **Untrusted input:** job pages, uploaded files.

## Test plan

| Criterion | Test |
|---|---|
| 1 | `tests/…::test_…` |
