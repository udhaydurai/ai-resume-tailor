"""Tests for the unsupported-claims check."""

from src.truthcheck import unsupported_numbers, unsupported_terms

ORIGINAL = "Cut deploy time by 60%. Served 50,000+ users. Mentored 2 engineers. 2021-2024."


def test_numbers_from_the_original_pass():
    generated = "Reduced deployment time 60% for 50,000+ users; mentored 2 engineers (2021-2024)."
    assert unsupported_numbers(ORIGINAL, generated) == []


def test_invented_metrics_are_flagged_once():
    generated = "Cut costs 35% and grew revenue 35%. Led 12 engineers."
    assert unsupported_numbers(ORIGINAL, generated) == ["35%", "12"]


def test_formatting_differences_are_not_flagged():
    assert unsupported_numbers("Served 50000 users", "Served 50,000+ users.") == []


def test_terms_the_job_wants_but_resume_lacks():
    terms = ["Kubernetes", "Python", "Terraform"]
    generated = "Expert in Python and Kubernetes."
    assert unsupported_terms("Python developer", generated, terms) == ["Kubernetes"]
