"""Flag claims in generated text that the original resume does not support."""

from __future__ import annotations

import re

NUMBER = re.compile(r"\d[\d,.]*\+?%?")


def _normalise(token: str) -> str:
    return token.rstrip(".,").replace(",", "")


def unsupported_numbers(original: str, generated: str) -> list[str]:
    """Numbers (metrics, years, counts) in `generated` that never appear in `original`."""
    known = {_normalise(n).rstrip("+%") for n in NUMBER.findall(original)}
    flagged: list[str] = []
    for raw in NUMBER.findall(generated):
        token = _normalise(raw)
        if token.rstrip("+%") not in known and token not in flagged:
            flagged.append(token)
    return flagged


def unsupported_terms(original: str, generated: str, terms: list[str]) -> list[str]:
    """Terms (such as skills the job asks for) in `generated` but absent from `original`."""

    def mentions(text: str, term: str) -> bool:
        return re.search(rf"(?<!\w){re.escape(term)}(?!\w)", text, re.IGNORECASE) is not None

    return [t for t in terms if mentions(generated, t) and not mentions(original, t)]
