"""
tests/unit/test_api_client.py

Unit tests for src/main/api_client.py.
All GitHub API calls are mocked — no network access required.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from src.main.api_client import GitHubClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_commit(
    date: datetime, message: str = "feat: initial commit", author: str = "alice"
):
    commit = MagicMock()
    commit.commit.author.date = date
    commit.commit.author.name = author
    commit.commit.message = message
    return commit


def _make_contributor(login: str, contributions: int):
    c = MagicMock()
    c.login = login
    c.contributions = contributions
    return c


# ---------------------------------------------------------------------------
# GitHubClient.__init__
# ---------------------------------------------------------------------------


def test_init_raises_without_token():
    with pytest.raises(ValueError, match="GitHub token is required"):
        GitHubClient(token="")


@patch("src.main.api_client.Github")
def test_init_succeeds_with_token(mock_github):
    client = GitHubClient(token="ghp_fake_token")
    assert client is not None
    mock_github.assert_called_once_with("ghp_fake_token")


# ---------------------------------------------------------------------------
# get_all_repos
# ---------------------------------------------------------------------------


@patch("src.main.api_client.Github")
def test_get_all_repos_returns_list(mock_github_cls):
    mock_github = mock_github_cls.return_value
    fake_org = MagicMock()
    fake_repos = [MagicMock(full_name=f"org/repo-{i}") for i in range(3)]
    fake_org.get_repos.return_value = fake_repos
    mock_github.get_organization.return_value = fake_org

    client = GitHubClient(token="ghp_fake")
    result = client.get_all_repos("my-org")

    assert len(result) == 3
    mock_github.get_organization.assert_called_once_with("my-org")


@patch("src.main.api_client.Github")
def test_get_all_repos_raises_on_api_error(mock_github_cls):
    from github import GithubException

    mock_github = mock_github_cls.return_value
    mock_github.get_organization.side_effect = GithubException(404, "Not Found")

    client = GitHubClient(token="ghp_fake")
    with pytest.raises(GithubException):
        client.get_all_repos("nonexistent-org")


# ---------------------------------------------------------------------------
# get_last_commit_date
# ---------------------------------------------------------------------------


@patch("src.main.api_client.Github")
def test_get_last_commit_date_returns_datetime(mock_github_cls):
    expected_date = datetime(2023, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

    mock_repo = MagicMock()
    mock_repo.full_name = "org/repo"
    mock_repo.pushed_at = expected_date

    client = GitHubClient(token="ghp_fake")
    result = client.get_last_commit_date(mock_repo)

    assert result == expected_date

@patch("src.main.api_client.Github")
def test_get_last_commit_date_makes_timezone_aware(mock_github_cls):
    """Naive datetime should be converted to UTC-aware."""
    naive_date = datetime(2023, 6, 1, 0, 0, 0)  # no tzinfo
    mock_commit = _make_commit(naive_date)

    mock_repo = MagicMock()
    mock_repo.full_name = "org/repo"
    mock_repo.get_commits.return_value = [mock_commit]

    client = GitHubClient(token="ghp_fake")
    result = client.get_last_commit_date(mock_repo)

    assert result.tzinfo is not None


@patch("src.main.api_client.Github")
def test_get_last_commit_date_empty_repo_returns_none(mock_github_cls):
    mock_repo = MagicMock()
    mock_repo.full_name = "org/empty-repo"
    mock_repo.pushed_at = None

    client = GitHubClient(token="ghp_fake")
    result = client.get_last_commit_date(mock_repo)

    assert result is None


# ---------------------------------------------------------------------------
# get_contributors
# ---------------------------------------------------------------------------


@patch("src.main.api_client.Github")
def test_get_contributors_returns_login_list(mock_github_cls):
    contributors = [
        _make_contributor("alice", 50),
        _make_contributor("bob", 30),
    ]
    mock_repo = MagicMock()
    mock_repo.full_name = "org/repo"
    mock_repo.get_contributors.return_value = contributors

    client = GitHubClient(token="ghp_fake")
    result = client.get_contributors(mock_repo)

    assert result == ["alice", "bob"]


@patch("src.main.api_client.Github")
def test_get_contributors_returns_empty_on_error(mock_github_cls):
    from github import GithubException

    mock_repo = MagicMock()
    mock_repo.full_name = "org/repo"
    mock_repo.get_contributors.side_effect = GithubException(403, "Forbidden")

    client = GitHubClient(token="ghp_fake")
    result = client.get_contributors(mock_repo)

    assert result == []


# ---------------------------------------------------------------------------
# get_languages
# ---------------------------------------------------------------------------


@patch("src.main.api_client.Github")
def test_get_languages_returns_dict(mock_github_cls):
    mock_repo = MagicMock()
    mock_repo.full_name = "org/repo"
    mock_repo.get_languages.return_value = {"Python": 12000, "Shell": 500}

    client = GitHubClient(token="ghp_fake")
    result = client.get_languages(mock_repo)

    assert result == {"Python": 12000, "Shell": 500}


@patch("src.main.api_client.Github")
def test_get_languages_returns_empty_on_error(mock_github_cls):
    from github import GithubException

    mock_repo = MagicMock()
    mock_repo.full_name = "org/repo"
    mock_repo.get_languages.side_effect = GithubException(500, "Server Error")

    client = GitHubClient(token="ghp_fake")
    result = client.get_languages(mock_repo)

    assert result == {}


# ---------------------------------------------------------------------------
# get_recent_commits
# ---------------------------------------------------------------------------


@patch("src.main.api_client.Github")
def test_get_recent_commits_returns_list_of_dicts(mock_github_cls):
    date = datetime(2024, 3, 1, tzinfo=timezone.utc)
    commits = [_make_commit(date, f"commit {i}", "alice") for i in range(5)]

    mock_repo = MagicMock()
    mock_repo.full_name = "org/repo"

    # Slice-able mock
    commits_mock = MagicMock()
    commits_mock.__getitem__ = MagicMock(return_value=commits)
    mock_repo.get_commits.return_value = commits_mock

    client = GitHubClient(token="ghp_fake")
    result = client.get_recent_commits(mock_repo, limit=5)

    assert isinstance(result, list)
    for item in result:
        assert "message" in item
        assert "date" in item
        assert "author" in item
