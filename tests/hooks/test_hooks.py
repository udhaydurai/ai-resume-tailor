"""Every guardrail hook, run the way Claude Code runs it: JSON on stdin, exit 2 blocks.

Each case is a past or likely bypass. Loosening a hook means changing a case here.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
HOOKS = Path(os.environ.get("HOOKS_DIR", REPO / ".claude" / "hooks"))
DB = "job_tracker." + "db"


@pytest.fixture
def env(tmp_path):
    home = tmp_path / "home"
    root = tmp_path / "repo"
    (home / "Documents" / "Personal" / "Resumes").mkdir(parents=True)
    (root / ".claude").mkdir(parents=True)
    (root / "private").mkdir()
    return {"HOME": str(home), "CLAUDE_PROJECT_DIR": str(root), "PATH": os.environ["PATH"]}


def run(hook: str, env: dict[str, str], tool: str, **tool_input: str) -> int:
    payload = json.dumps({"tool_name": tool, "tool_input": tool_input})
    result = subprocess.run(
        ["python3", str(HOOKS / hook)], input=payload, env=env, capture_output=True, text=True
    )
    return result.returncode


def privacy(env, tool, **tool_input):
    return run("block_private_data.py", env, tool, **tool_input)


def open_mode(env, **extra):
    config = {"mode": "open", **extra}
    Path(env["CLAUDE_PROJECT_DIR"], ".claude", "privacy.local.json").write_text(json.dumps(config))


def paths(env):
    return Path(env["HOME"]), Path(env["CLAUDE_PROJECT_DIR"])


# --- block_private_data: strict mode (the default) -----------------------------------


@pytest.mark.parametrize(
    ("tool", "key", "value"),
    [
        ("Read", "file_path", "{home}/Documents/Personal/Resumes/me.pdf"),
        ("Glob", "path", "{home}/Documents/Personal"),
        ("Grep", "path", "~/Documents/Personal"),
        ("Bash", "command", "cat ~/Documents/Personal/Resumes/me.txt"),
        ("Bash", "command", "cat $HOME/Documents/Personal/me.txt"),
        ("Bash", "command", 'cat "${{HOME}}/Documents/Personal/me.txt"'),
        ("Bash", "command", "cd ~/Documents && cat Personal/Resumes/me.txt"),
        ("Bash", "command", "cat ~/Documents/Pers*/Resumes/me.txt"),
        ("Bash", "command", "ls ~/Documents/*/Resumes"),
        ("Bash", "command", "python3 -c \"open('{home}/Documents/Personal/x').read()\""),
        ("Read", "file_path", "{root}/private/notes.txt"),
        ("Bash", "command", "ls private"),
        ("Bash", "command", "git add -f private/draft.txt"),
        ("Read", "file_path", "{root}/.env"),
        ("Bash", "command", "cat .env"),
        ("Bash", "command", "cp .env.example .env"),
        ("Read", "file_path", "{root}/.env.local"),
        ("Read", "file_path", "{root}/" + DB),
        ("Bash", "command", "sqlite3 " + DB + " 'select * from applications'"),
        ("Read", "file_path", "{home}/Downloads/resume.pdf"),
        ("Read", "file_path", "{home}/Downloads/resume.docx"),
        ("Glob", "pattern", "**/*.pdf"),
    ],
)
def test_strict_blocks(env, tool, key, value):
    home, root = paths(env)
    assert privacy(env, tool, **{key: value.format(home=home, root=root)}) == 2


@pytest.mark.parametrize(
    ("tool", "key", "value"),
    [
        ("Read", "file_path", "{root}/.env.example"),
        ("Read", "file_path", "{root}/demo/sample_resume.txt"),
        ("Read", "file_path", "{root}/demo/sample.pdf"),
        ("Read", "file_path", "{root}/tests/fixtures/resume.docx"),
        ("Read", "file_path", "{root}/src/job_tracker.py"),
        ("Bash", "command", 'git commit -m "keep the private folder out of git"'),
        ("Bash", "command", "uv run pytest -q tests/test_job_tracker.py"),
        ("Bash", "command", "git status --short"),
        ("Read", "file_path", "/private/tmp/scratch/notes.txt"),
        ("Grep", "pattern", "load_dotenv"),
        ("Read", "file_path", "{home}/Documents/Taxes/2024.txt"),
    ],
)
def test_strict_allows(env, tool, key, value):
    home, root = paths(env)
    assert privacy(env, tool, **{key: value.format(home=home, root=root)}) == 0


def test_content_being_written_is_not_scanned(env):
    _, root = paths(env)
    code = f'DB_PATH = "{DB}"  # and ~/Documents/Personal in a comment'
    assert privacy(env, "Write", file_path=f"{root}/src/x.py", content=code) == 0


def test_symlink_into_private_folder_is_blocked(env):
    home, root = paths(env)
    (root / "link").symlink_to(home / "Documents" / "Personal")
    assert privacy(env, "Read", file_path=f"{root}/link/Resumes/me.txt") == 2


def test_dot_dot_into_private_folder_is_blocked(env):
    home, root = paths(env)
    assert privacy(env, "Read", file_path=f"{root}/../home/Documents/Personal/x") == 2


def test_extra_private_dirs_are_blocked_in_strict(env):
    home, root = paths(env)
    Path(root, ".claude", "privacy.local.json").write_text(
        json.dumps({"mode": "strict", "private_dirs": ["~/JobHunt"]})
    )
    assert privacy(env, "Read", file_path=f"{home}/JobHunt/notes.txt") == 2


@pytest.mark.parametrize("config", ["not json", '["open"]', '{"mode": "OPEN"}', '{"mode": 1}'])
def test_broken_config_means_strict(env, config):
    home, root = paths(env)
    Path(root, ".claude", "privacy.local.json").write_text(config)
    assert privacy(env, "Read", file_path=f"{home}/Documents/Personal/Resumes/me.pdf") == 2


def test_bad_input_blocks(env):
    result = subprocess.run(
        ["python3", str(HOOKS / "block_private_data.py")], input="nope", env=env, text=True
    )
    assert result.returncode == 2


# --- block_private_data: open mode ---------------------------------------------------


def test_open_mode_lets_claude_read_resumes(env):
    home, root = paths(env)
    open_mode(env)
    assert privacy(env, "Read", file_path=f"{home}/Documents/Personal/Resumes/me.pdf") == 0
    assert privacy(env, "Read", file_path=f"{home}/Downloads/resume.pdf") == 0
    assert privacy(env, "Grep", path=f"{root}/private", pattern="Python") == 0


def test_open_mode_writes_drafts_only_into_repo_private(env):
    home, root = paths(env)
    open_mode(env)
    assert privacy(env, "Write", file_path=f"{root}/private/draft.txt") == 0
    assert privacy(env, "Write", file_path=f"{home}/Documents/Personal/x.txt") == 2


@pytest.mark.parametrize(
    "command",
    ["cat ~/Documents/Personal/Resumes/me.txt", "cp private/draft.txt demo/", "git add private"],
)
def test_open_mode_still_blocks_bash(env, command):
    open_mode(env)
    assert privacy(env, "Bash", command=command) == 2


def test_open_mode_still_blocks_secrets_and_tracker(env):
    _, root = paths(env)
    open_mode(env)
    assert privacy(env, "Read", file_path=f"{root}/.env") == 2
    assert privacy(env, "Read", file_path=f"{root}/{DB}") == 2


def test_open_mode_reads_extra_private_dirs(env):
    home, _ = paths(env)
    open_mode(env, private_dirs=["~/JobHunt"])
    assert privacy(env, "Read", file_path=f"{home}/JobHunt/notes.txt") == 0


# --- protect_guardrails ---------------------------------------------------------------


def guard(env, tool, **tool_input):
    return run("protect_guardrails.py", env, tool, **tool_input)


@pytest.mark.parametrize(
    "rel",
    [
        ".claude/settings.json",
        ".claude/settings.local.json",
        ".claude/privacy.local.json",
        ".claude/hooks/block_private_data.py",
        ".claude/agents/red-team.md",
        ".gitignore",
        ".pre-commit-config.yaml",
        ".github/workflows/ci.yml",
        "scripts/scan_repo.py",
        "scripts/validate_review.py",
        "docs/review/finding.schema.json",
    ],
)
def test_guardrail_files_cannot_be_edited(env, rel):
    _, root = paths(env)
    assert guard(env, "Write", file_path=f"{root}/{rel}") == 2
    assert guard(env, "Edit", file_path=rel) == 2


@pytest.mark.parametrize(
    "command",
    [
        "echo '!*.pdf' >> .gitignore",
        "sed -i '' 's/strict/open/' .claude/privacy.local.json",
        "python3 -c \"open('.claude/settings.json','w').write('{}')\"",
        "rm -rf .claude/hooks",
        "git checkout -- .claude/hooks/protect_guardrails.py",
        "cp /tmp/x.md .claude/agents/red-team.md",
        "tee .claude/settings.local.json < /tmp/x",
        "printf '{}' > {root}/.claude/settings.local.json",
        "git commit --no-verify -m x",
        "SKIP=scan-repo git commit -m x",
        "git push --force origin setup/x",
        "git push -f origin setup/x",
        "git push origin +setup/x",
        "git -c core.hooksPath=/dev/null commit -m x",
        "echo '{\"disableAllHooks\": true}'",
    ],
)
def test_bash_cannot_change_guardrails(env, command):
    _, root = paths(env)
    assert guard(env, "Bash", command=command.replace("{root}", str(root))) == 2


@pytest.mark.parametrize(
    "command",
    [
        "cat .claude/settings.json",
        "grep -n mode .claude/hooks/block_private_data.py 2>/dev/null",
        "uv run python scripts/validate_review.py .review/security.json",
        "uv run python scripts/scan_repo.py",
        "make check 2>&1 | tail -20",
        "git push -u origin setup/claude-harness",
        "git diff master...HEAD -- .gitignore",
    ],
)
def test_bash_may_read_and_run_guardrails(env, command):
    assert guard(env, "Bash", command=command) == 0


def test_other_files_and_other_repos_are_not_guarded(env, tmp_path):
    _, root = paths(env)
    assert guard(env, "Write", file_path=f"{root}/src/app.py") == 0
    assert guard(env, "Write", file_path=f"{tmp_path}/other/.claude/settings.json") == 0


def test_symlink_to_guardrail_is_guarded(env):
    _, root = paths(env)
    (root / ".claude" / "settings.json").write_text("{}")
    (root / "innocent.json").symlink_to(root / ".claude" / "settings.json")
    assert guard(env, "Write", file_path=f"{root}/innocent.json") == 2


# --- reviewer hooks ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "command",
    [
        "rm src/utils.py",
        "git commit -am x",
        "echo x > src/x.py",
        "uv add requests",
        "gh pr merge 3",
        "python3 -c 'import os; os.remove(\"x\")'",
        "curl https://example.com",
    ],
)
def test_reviewers_cannot_change_things(env, command):
    assert run("readonly_bash.py", env, "Bash", command=command) == 2


@pytest.mark.parametrize(
    "command",
    [
        "uv run pytest --no-cov .review/proofs/test_x.py",
        "git diff master...HEAD",
        "grep -rn TRUTH src 2>/dev/null",
        "make validate-review",
    ],
)
def test_reviewers_can_read_and_test(env, command):
    assert run("readonly_bash.py", env, "Bash", command=command) == 0


def test_judge_writes_only_under_review(env):
    _, root = paths(env)
    hook = "review_scratch_only.py"
    assert run(hook, env, "Write", file_path=f"{root}/.review/proofs/test_x.py") == 0
    assert run(hook, env, "Write", file_path=f"{root}/src/x.py") == 2
    assert run(hook, env, "Write", file_path=f"{root}/.review/../src/x.py") == 2


def test_session_start_reports_privacy_mode(env):
    _, root = paths(env)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    (root / "docs").mkdir()
    (root / "docs" / "ROADMAP.md").write_text("- [ ] 1.1 Next thing\n")
    out = subprocess.run(
        [str(HOOKS / "session_start.sh")], env=env, capture_output=True, text=True
    ).stdout
    assert "Privacy mode: strict" in out
    assert "1.1 Next thing" in out
    open_mode(env)
    out = subprocess.run(
        [str(HOOKS / "session_start.sh")], env=env, capture_output=True, text=True
    ).stdout
    assert "Privacy mode: open" in out
