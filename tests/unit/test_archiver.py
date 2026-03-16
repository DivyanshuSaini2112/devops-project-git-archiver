"""
tests/unit/test_archiver.py

Unit tests for src/main/archiver.py.
Filesystem and subprocess calls are mocked throughout.
"""

import os
import tarfile
import tempfile
import zipfile
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch, call

from src.main.archiver import (
    archive_repo,
    generate_archive,
    identify_stale_repos,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_repo(name: str, archived: bool = False) -> MagicMock:
    repo = MagicMock()
    repo.name = name
    repo.full_name = f"org/{name}"
    repo.html_url = f"https://github.com/org/{name}"
    repo.clone_url = f"https://github.com/org/{name}.git"
    repo.description = f"Description for {name}"
    repo.language = "Python"
    repo.archived = archived
    return repo


# ---------------------------------------------------------------------------
# identify_stale_repos
# ---------------------------------------------------------------------------


@patch("src.main.archiver.GitHubClient")
def test_identify_stale_repos_returns_stale(mock_client_cls):
    old_date = datetime.now(tz=timezone.utc) - timedelta(days=200)
    mock_client = mock_client_cls.return_value
    mock_client.get_last_commit_date.return_value = old_date

    repos = [_make_repo("stale-repo")]
    result = identify_stale_repos(repos, stale_days=90)

    assert len(result) == 1
    assert result[0].name == "stale-repo"


@patch("src.main.archiver.GitHubClient")
def test_identify_stale_repos_excludes_recent(mock_client_cls):
    recent_date = datetime.now(tz=timezone.utc) - timedelta(days=10)
    mock_client = mock_client_cls.return_value
    mock_client.get_last_commit_date.return_value = recent_date

    repos = [_make_repo("active-repo")]
    result = identify_stale_repos(repos, stale_days=90)

    assert len(result) == 0


@patch("src.main.archiver.GitHubClient")
def test_identify_stale_repos_skips_already_archived(mock_client_cls):
    repos = [_make_repo("already-archived", archived=True)]
    result = identify_stale_repos(repos, stale_days=90)

    assert len(result) == 0
    # get_last_commit_date should never be called for already-archived repos
    mock_client_cls.return_value.get_last_commit_date.assert_not_called()


@patch("src.main.archiver.GitHubClient")
def test_identify_stale_repos_treats_empty_repo_as_stale(mock_client_cls):
    mock_client = mock_client_cls.return_value
    mock_client.get_last_commit_date.return_value = None  # empty repo

    repos = [_make_repo("empty-repo")]
    result = identify_stale_repos(repos, stale_days=90)

    assert len(result) == 1


@patch("src.main.archiver.GitHubClient")
def test_identify_stale_repos_mixed_list(mock_client_cls):
    old_date = datetime.now(tz=timezone.utc) - timedelta(days=120)
    recent_date = datetime.now(tz=timezone.utc) - timedelta(days=5)

    def fake_last_commit(repo):
        return old_date if "stale" in repo.name else recent_date

    mock_client = mock_client_cls.return_value
    mock_client.get_last_commit_date.side_effect = fake_last_commit

    repos = [_make_repo("stale-repo-1"), _make_repo("active-repo"), _make_repo("stale-repo-2")]
    result = identify_stale_repos(repos, stale_days=90)

    assert len(result) == 2
    names = [r.name for r in result]
    assert "stale-repo-1" in names
    assert "stale-repo-2" in names
    assert "active-repo" not in names


# ---------------------------------------------------------------------------
# generate_archive
# ---------------------------------------------------------------------------


def test_generate_archive_creates_tar_gz():
    with tempfile.TemporaryDirectory() as tmp:
        # Create dummy source content
        src = os.path.join(tmp, "source")
        os.makedirs(src)
        with open(os.path.join(src, "file.txt"), "w") as f:
            f.write("hello")

        archive_path = os.path.join(tmp, "output.tar.gz")
        result = generate_archive(src, archive_path)

        assert os.path.exists(result)
        assert tarfile.is_tarfile(result)


def test_generate_archive_creates_zip():
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, "source")
        os.makedirs(src)
        with open(os.path.join(src, "file.txt"), "w") as f:
            f.write("world")

        archive_path = os.path.join(tmp, "output.zip")
        result = generate_archive(src, archive_path)

        assert os.path.exists(result)
        assert zipfile.is_zipfile(result)


def test_generate_archive_raises_for_unknown_format():
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, "source")
        os.makedirs(src)

        with pytest.raises(ValueError, match="Unsupported archive format"):
            generate_archive(src, os.path.join(tmp, "output.rar"))


def test_generate_archive_returns_correct_path():
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, "source")
        os.makedirs(src)

        archive_path = os.path.join(tmp, "test.tar.gz")
        result = generate_archive(src, archive_path)

        assert result == archive_path


# ---------------------------------------------------------------------------
# archive_repo (dry run)
# ---------------------------------------------------------------------------


@patch("src.main.archiver.GitHubClient")
def test_archive_repo_dry_run_returns_none(mock_client_cls):
    repo = _make_repo("test-repo")
    result = archive_repo(repo, storage_dir="/tmp/test_storage", dry_run=True)
    assert result is None


@patch("src.main.archiver.clone_repo")
@patch("src.main.archiver.generate_archive")
@patch("src.main.archiver.DocGenerator")
@patch("src.main.archiver.shutil")
def test_archive_repo_full_pipeline(mock_shutil, mock_doc_cls, mock_gen_archive, mock_clone):
    """Verify the full pipeline executes in the correct order."""
    repo = _make_repo("test-repo")

    mock_client = MagicMock()
    mock_client.get_contributor_stats.return_value = []
    mock_client.get_recent_commits.return_value = []
    mock_client.get_languages.return_value = {}
    mock_client.get_last_commit_date.return_value = datetime.now(tz=timezone.utc) - timedelta(days=200)

    mock_clone.return_value = "/fake/clone/dir"
    mock_gen_archive.return_value = "/fake/archive.tar.gz"

    with tempfile.TemporaryDirectory() as storage:
        with patch("src.main.archiver.tempfile.TemporaryDirectory") as mock_tmp:
            mock_tmp.return_value.__enter__.return_value = storage

            # Should not raise
            archive_repo(repo, storage_dir=storage, client=mock_client, dry_run=False)
