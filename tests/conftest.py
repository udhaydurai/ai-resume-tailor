"""Shared test setup."""

import os

import pytest


@pytest.fixture(autouse=True)
def _clean_model_settings(monkeypatch):
    """Tests never inherit the developer's provider, model or key settings."""
    for name in list(os.environ):
        if name.startswith("RESUME_TAILOR_") or name == "OPENAI_API_KEY":
            monkeypatch.delenv(name)
