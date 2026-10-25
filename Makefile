.PHONY: setup run fmt lint types test scan gitleaks audit check-fast check eval validate-review requirements

setup:
	uv sync
	uv run pre-commit install

run:
	uv run streamlit run app.py

fmt:
	uv run ruff format .
	uv run ruff check --fix .

lint:
	uv run ruff format --check .
	uv run ruff check .

types:
	uv run mypy

test:
	uv run pytest -q

scan:
	uv run python scripts/scan_repo.py

gitleaks:
	gitleaks git --redact --no-banner

audit:
	uv export --no-dev --no-hashes --no-emit-project -q | uv run pip-audit -r /dev/stdin --progress-spinner off

check-fast: lint types test scan

check: check-fast gitleaks audit

# Calls the real Claude API: costs a few cents per run. Needs ANTHROPIC_API_KEY.
eval:
	uv run python evals/run_eval.py

validate-review:
	uv run python scripts/validate_review.py $(REVIEWS)

requirements:
	uv export --no-dev --no-hashes --no-emit-project -q -o requirements.txt
