# Privacy

Your resume, your job tracker and your API key are yours. This page says where they go and how Claude Code is kept away from them.

## Where your data goes

| Data | Where it lives | Leaves your machine? |
|---|---|---|
| Uploaded resume | In memory while the app runs | Sent to Anthropic's API with each request |
| Job description | In memory while the app runs | Sent to Anthropic's API |
| Job tracker | `job_tracker` database file in the repo folder (git-ignored) | No |
| API key | `.env` (git-ignored) | Only to Anthropic |

The tracker is one file for whoever runs the app. Don't host this app for other people as it is: everyone would share one tracker. (Roadmap slice 1.5.)

## Keeping personal data out of git

- `.gitignore` covers `.env`, the tracker database, `private/` and local Claude settings.
- `scripts/scan_repo.py` runs before every commit and in CI. It rejects resume documents outside `demo/` and `tests/fixtures/`, data exports, `.env` files, anything in `private/`, real-looking emails (use `@example.test`) and real-looking phone numbers (use `555-01xx`). It reports the file and line, never the matched text.
- gitleaks checks for secrets.

## Privacy mode for Claude Code

If you use Claude Code in this repo, a hook decides what Claude may touch.

**Strict (the default).** Claude can't read or search:
- `~/Documents/Personal/` and the repo's `private/` folder
- any `.pdf`, `.docx`, `.doc`, `.pages` or `.rtf` outside `demo/` and `tests/fixtures/`
- `.env` files and the tracker database

Upload resumes through the app instead.

**Open.** For when you want Claude to tailor your real resume in the terminal. Create `.claude/privacy.local.json` yourself (it is git-ignored, and Claude is not allowed to write it):

```json
{
  "mode": "open",
  "private_dirs": ["~/Documents/Personal/Resumes"]
}
```

In open mode Claude may **read** the private folders and resume documents, and **write** drafts into the repo's `private/` folder. Some things stay blocked in every mode:
- `.env` and the tracker database
- any Bash command that touches a private folder (no copying, no `git add`)
- the commit scanner, which still rejects private files

`private_dirs` adds folders to the private list in either mode. Delete the file, or set `"mode": "strict"`, to go back. The session banner shows the current mode.
