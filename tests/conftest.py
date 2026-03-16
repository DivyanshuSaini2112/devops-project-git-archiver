"""
conftest.py — Shared pytest fixtures for unit and integration tests.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock


def make_mock_repo(
    name: str = "test-repo",
    full_name: str = "my-org/test-repo",
    html_url: str = "https://github.com/my-org/test-repo",
    clone_url: str = "https://github.com/my-org/test-repo.git",
    description: str = "A test repository",
    language: str = "Python",
    archived: bool = False,
) -> MagicMock:
    """Return a fully-configured mock Repository object."""
    repo = MagicMock()
    repo.name = name
    repo.full_name = full_name
    repo.html_url = html_url
    repo.clone_url = clone_url
    repo.description = description
    repo.language = language
    repo.archived = archived
    return repo


@pytest.fixture
def mock_repo():
    return make_mock_repo()


@pytest.fixture
def old_commit_date():
    """Return a datetime 200 days in the past (well beyond 90-day threshold)."""
    from datetime import timedelta

    return datetime.now(tz=timezone.utc) - timedelta(days=200)


@pytest.fixture
def recent_commit_date():
    """Return a datetime 10 days in the past (within threshold)."""
    from datetime import timedelta

    return datetime.now(tz=timezone.utc) - timedelta(days=10)
