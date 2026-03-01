"""Tests for job tracker module."""

import os
import tempfile
from unittest.mock import patch

import pytest

from src import job_tracker


@pytest.fixture(autouse=True)
def _temp_db(tmp_path):
    """Use a temporary database for each test."""
    db_path = tmp_path / "test_tracker.db"
    with patch.object(job_tracker, "DB_PATH", db_path):
        job_tracker.init_db()
        yield


def test_add_and_get():
    app_id = job_tracker.add_application(
        company="Acme Corp",
        title="Software Engineer",
        status="Applied",
    )
    assert app_id is not None
    apps = job_tracker.get_all_applications()
    assert len(apps) == 1
    assert apps[0]["company"] == "Acme Corp"
    assert apps[0]["status"] == "Applied"


def test_update_status():
    app_id = job_tracker.add_application(
        company="Beta Inc", title="PM"
    )
    job_tracker.update_status(app_id, "Interview")
    apps = job_tracker.get_all_applications()
    assert apps[0]["status"] == "Interview"


def test_delete():
    app_id = job_tracker.add_application(
        company="Gamma LLC", title="Designer"
    )
    job_tracker.delete_application(app_id)
    apps = job_tracker.get_all_applications()
    assert len(apps) == 0


def test_export_csv():
    job_tracker.add_application(company="Delta Co", title="Analyst")
    csv_str = job_tracker.export_csv()
    assert "Delta Co" in csv_str
    assert "Analyst" in csv_str


def test_export_csv_empty():
    csv_str = job_tracker.export_csv()
    assert csv_str == ""
