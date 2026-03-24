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
import json
import logging
from unittest.mock import MagicMock, patch

from src.main.archiver import (
    JSONFormatter,
    PrettyFormatter,
    setup_logging,
    archive_repo,
    generate_archive,
    identify_stale_repos,
    clone_repo,
    main,
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
# Logging and Formatters
# ---------------------------------------------------------------------------


def test_json_formatter():
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="fake.py",
        lineno=1,
        msg="Test message",
        args=(),
        exc_info=None,
    )
    record.repo = "org/my-repo"

    formatted = formatter.format(record)
    data = json.loads(formatted)

    assert data["level"] == "INFO"
    assert data["message"] == "Test message"
    assert data["repo"] == "org/my-repo"
    assert data["logger"] == "test_logger"
    assert "timestamp" in data


def test_pretty_formatter():
    formatter = PrettyFormatter()
    record = logging.LogRecord(
        name="test_logger",
        level=logging.WARNING,
        pathname="fake.py",
        lineno=1,
        msg="Warning message",
        args=(),
        exc_info=None,
    )

    formatted_no_repo = formatter.format(record)
    assert "WARNING " in formatted_no_repo
    assert "Warning message" in formatted_no_repo

    record.repo = "org/my-repo"
    formatted_repo = formatter.format(record)
    assert "(org/my-repo)" in formatted_repo


@patch("src.main.archiver.logging.getLogger")
@patch("src.main.archiver.logging.FileHandler")
@patch("src.main.archiver.LOG_FILE", "/tmp/fake.log")
def test_setup_logging_file(mock_file_handler, mock_get_logger):
    mock_root = MagicMock()
    mock_get_logger.return_value = mock_root
    setup_logging()
    mock_file_handler.assert_called_once()
    mock_root.addHandler.assert_called_once()


@patch("src.main.archiver.logging.getLogger")
@patch("src.main.archiver.logging.StreamHandler")
@patch("src.main.archiver.LOG_FILE", "")
def test_setup_logging_stream(mock_stream_handler, mock_get_logger):
    mock_root = MagicMock()
    mock_get_logger.return_value = mock_root
    setup_logging()
    mock_stream_handler.assert_called_once()
    mock_root.addHandler.assert_called_once()


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

    repos = [
        _make_repo("stale-repo-1"),
        _make_repo("active-repo"),
        _make_repo("stale-repo-2"),
    ]
    result = identify_stale_repos(repos, stale_days=90)

    assert len(result) == 2
    names = [r.name for r in result]
    assert "stale-repo-1" in names
    assert "stale-repo-2" in names
    assert "active-repo" not in names


# ---------------------------------------------------------------------------
# clone_repo
# ---------------------------------------------------------------------------


@patch("subprocess.run")
def test_clone_repo_success(mock_run):
    mock_run.return_value = MagicMock(returncode=0)

    with tempfile.TemporaryDirectory() as tmp:
        dest = os.path.join(tmp, "cloned")
        res = clone_repo("https://github.com/org/repo.git", dest)

        assert res == dest
        mock_run.assert_called_once()


@patch("subprocess.run")
def test_clone_repo_failure(mock_run):
    mock_run.return_value = MagicMock(returncode=1, stderr="clone failed")

    with tempfile.TemporaryDirectory() as tmp:
        dest = os.path.join(tmp, "cloned")
        with pytest.raises(RuntimeError, match="git clone failed"):
            clone_repo("https://github.com/org/repo.git", dest)


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
def test_archive_repo_full_pipeline(
    mock_shutil, mock_doc_cls, mock_gen_archive, mock_clone
):
    """Verify the full pipeline executes in the correct order."""
    repo = _make_repo("test-repo")

    mock_client = MagicMock()
    mock_client.get_contributor_stats.return_value = []
    mock_client.get_recent_commits.return_value = []
    mock_client.get_languages.return_value = {}
    mock_client.get_last_commit_date.return_value = datetime.now(
        tz=timezone.utc
    ) - timedelta(days=200)

    mock_clone.return_value = "/fake/clone/dir"
    mock_gen_archive.return_value = "/fake/archive.tar.gz"

    with tempfile.TemporaryDirectory() as storage:
        with patch("src.main.archiver.tempfile.TemporaryDirectory") as mock_tmp:
            mock_tmp.return_value.__enter__.return_value = storage

            # Should not raise, returns the final path
            result = archive_repo(
                repo, storage_dir=storage, client=mock_client, dry_run=False
            )
            assert result is not None
            assert "test-repo" in result
            assert result.endswith(".tar.gz")


@patch("src.main.archiver.clone_repo")
def test_archive_repo_clone_fails(mock_clone):
    repo = _make_repo("fail-repo")
    mock_client = MagicMock()
    mock_clone.side_effect = RuntimeError("git failed")

    result = archive_repo(repo, storage_dir="/tmp", client=mock_client, dry_run=False)
    assert result is None


# ---------------------------------------------------------------------------
# main CLI
# ---------------------------------------------------------------------------


@patch("builtins.input", side_effect=["org1", "60", "zip", "yes", "/tmp/store", "yes"])
@patch("src.main.archiver.setup_logging")
@patch("src.main.archiver.GitHubClient")
@patch("src.main.archiver.identify_stale_repos")
@patch("src.main.archiver.archive_repo")
@patch("src.main.archiver.GITHUB_TOKEN", "fake_token")
def test_main_cli_flow(
    mock_archive_repo, mock_identify, mock_github_client, mock_setup_logging, mock_input
):
    mock_client_instance = mock_github_client.return_value
    mock_client_instance.get_all_repos.return_value = [_make_repo("repo1")]
    mock_identify.return_value = [_make_repo("repo1")]
    mock_archive_repo.return_value = "/tmp/store/repo1.zip"

    main()

    mock_setup_logging.assert_called_once()
    mock_identify.assert_called_once()
    mock_archive_repo.assert_called_once()


@patch("builtins.input", side_effect=["org1", "60", "zip", "yes", "/tmp/store", "no"])
def test_main_cli_aborts(mock_input):
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 0


@patch("builtins.input", side_effect=["org1", "60", "zip", "yes", "/tmp/store", "yes"])
@patch("src.main.archiver.setup_logging")
@patch("src.main.archiver.GITHUB_TOKEN", "")
def test_main_cli_fails_no_token(mock_setup_logging, mock_input):
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 1


@patch("builtins.input", side_effect=["", "60", "zip", "yes", "/tmp/store", "yes"])
@patch("src.main.archiver.setup_logging")
@patch("src.main.archiver.GITHUB_TOKEN", "fake_token")
@patch("src.main.archiver.TARGET_ORG", "")
def test_main_cli_fails_no_org(mock_setup_logging, mock_input):
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 1
