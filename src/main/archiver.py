"""
archiver.py - Core orchestration logic for the Git Repository Archiver.

Pipeline per stale repository:
    1. identify_stale_repos()  -> filter by last commit date
    2. clone_repo()            -> git clone to temp directory
    3. DocGenerator            -> generate summary.md alongside source
    4. generate_archive()      -> compress to .tar.gz (or .zip)
    5. move archive            -> to STORAGE_DIR

Structured JSON logging is emitted at each stage for Nagios / log aggregators.
"""

import json
import logging
import os
import shutil
import subprocess
import tarfile
import tempfile
import zipfile
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from github.Repository import Repository

from src.main.api_client import GitHubClient
from src.main.config import (
    ARCHIVE_FORMAT,
    DRY_RUN,
    GITHUB_TOKEN,
    LOG_FILE,
    LOG_LEVEL,
    STALE_DAYS,
    STORAGE_DIR,
    TARGET_ORG,
)
from src.main.doc_generator import DocGenerator

# ---------------------------------------------------------------------------
# Structured JSON logging
# ---------------------------------------------------------------------------


class JSONFormatter(logging.Formatter):
    """Emit log records as single-line JSON for machine parsing."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
            "repo": getattr(record, "repo", None),
            "logger": record.name,
        }
        return json.dumps(payload)


def setup_logging() -> None:
    """Configure root logger with JSON formatter."""
    level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)
    handler: logging.Handler

    if LOG_FILE:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    else:
        handler = logging.StreamHandler()

    handler.setFormatter(JSONFormatter())

    root = logging.getLogger()
    root.setLevel(level)
    root.addHandler(handler)


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------


def identify_stale_repos(
    repos: List[Repository], stale_days: int = STALE_DAYS
) -> List[Repository]:
    """
    Filter repositories that have had no commits for *stale_days* days.

    Args:
        repos:      Full list of Repository objects from the GitHub API.
        stale_days: Inactivity threshold in days.

    Returns:
        Subset of repos considered stale.
    """
    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=stale_days)
    stale: List[Repository] = []

    for repo in repos:
        if repo.archived:
            logger.debug("Skipping already-archived repo: %s", repo.full_name)
            continue

        client = GitHubClient(token=GITHUB_TOKEN)
        last_commit = client.get_last_commit_date(repo)

        if last_commit is None:
            logger.warning(
                "Treating empty repo as stale: %s",
                repo.full_name,
                extra={"repo": repo.full_name},
            )
            stale.append(repo)
            continue

        if last_commit < cutoff:
            days_inactive = (datetime.now(tz=timezone.utc) - last_commit).days
            logger.info(
                "Stale repo detected: %s (inactive %d days)",
                repo.full_name,
                days_inactive,
                extra={"repo": repo.full_name},
            )
            stale.append(repo)

    logger.info(
        "Identified %d stale repositories (threshold: %d days).",
        len(stale),
        stale_days,
    )
    return stale


def clone_repo(repo_url: str, dest_dir: str) -> str:
    """
    Clone a repository to dest_dir using subprocess git.

    Args:
        repo_url:  HTTPS clone URL (token may be embedded).
        dest_dir:  Directory where the clone will be created.

    Returns:
        Path to the cloned repository directory.

    Raises:
        RuntimeError: if git clone exits with a non-zero code.
    """
    os.makedirs(dest_dir, exist_ok=True)
    cmd = ["git", "clone", "--depth", "1", repo_url, dest_dir]
    logger.info("Cloning '%s' → '%s'", repo_url, dest_dir)

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=300,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"git clone failed for {repo_url}:\n{result.stderr}"
        )

    logger.info("Clone complete: '%s'", dest_dir)
    return dest_dir


def generate_archive(source_dir: str, archive_path: str) -> str:
    """
    Compress source_dir into a .tar.gz or .zip archive.

    Args:
        source_dir:   Path to the directory to compress.
        archive_path: Desired output archive path (including extension).

    Returns:
        Path to the created archive file.
    """
    os.makedirs(os.path.dirname(archive_path) or ".", exist_ok=True)

    if archive_path.endswith(".tar.gz") or archive_path.endswith(".tgz"):
        with tarfile.open(archive_path, "w:gz") as tar:
            tar.add(source_dir, arcname=os.path.basename(source_dir))
    elif archive_path.endswith(".zip"):
        with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, _dirs, files in os.walk(source_dir):
                for file in files:
                    abs_path = os.path.join(root, file)
                    rel_path = os.path.relpath(abs_path, os.path.dirname(source_dir))
                    zf.write(abs_path, rel_path)
    else:
        raise ValueError(
            f"Unsupported archive format for path: {archive_path}. "
            "Use .tar.gz or .zip"
        )

    size_mb = os.path.getsize(archive_path) / (1024 * 1024)
    logger.info(
        "Archive created: '%s' (%.2f MB)", archive_path, size_mb
    )
    return archive_path


def archive_repo(
    repo: Repository,
    storage_dir: str = STORAGE_DIR,
    client: Optional[GitHubClient] = None,
    dry_run: bool = DRY_RUN,
) -> Optional[str]:
    """
    Full pipeline for a single repository:
        clone → generate docs → compress → move to storage.

    Args:
        repo:        PyGitHub Repository object.
        storage_dir: Directory where the final archive is stored.
        client:      Pre-initialised GitHubClient (created if None).
        dry_run:     When True, simulate the run without writing archives.

    Returns:
        Path to the final archive, or None on failure.
    """
    extra = {"repo": repo.full_name}
    logger.info("Starting archive pipeline for '%s'.", repo.full_name, extra=extra)

    if dry_run:
        logger.info(
            "[DRY RUN] Would archive '%s' – skipping.", repo.full_name, extra=extra
        )
        return None

    if client is None:
        client = GitHubClient(token=GITHUB_TOKEN)

    # Gather metadata
    contributors = client.get_contributor_stats(repo)
    recent_commits = client.get_recent_commits(repo)
    languages = client.get_languages(repo)
    last_commit = client.get_last_commit_date(repo)
    last_commit_str = last_commit.isoformat() if last_commit else None

    with tempfile.TemporaryDirectory(prefix=f"archiver_{repo.name}_") as tmp_dir:
        clone_dest = os.path.join(tmp_dir, repo.name)

        # 1. Clone
        clone_url = repo.clone_url
        # Embed token for private repositories
        if GITHUB_TOKEN:
            clone_url = clone_url.replace(
                "https://", f"https://{GITHUB_TOKEN}@"
            )
        try:
            clone_repo(clone_url, clone_dest)
        except RuntimeError as exc:
            logger.error(
                "Clone failed for '%s': %s", repo.full_name, exc, extra=extra
            )
            return None

        # 2. Generate summary.md
        summary_path = os.path.join(clone_dest, "ARCHIVE_SUMMARY.md")
        doc_gen = DocGenerator()
        doc_gen.generate_summary(
            repo_name=repo.full_name,
            repo_url=repo.html_url,
            description=repo.description,
            primary_language=repo.language,
            languages=languages,
            contributors=contributors,
            recent_commits=recent_commits,
            last_commit_date=last_commit_str,
            output_path=summary_path,
        )

        # 3. Compress
        ext = "zip" if ARCHIVE_FORMAT == "zip" else "tar.gz"
        archive_filename = f"{repo.name}_{datetime.now(tz=timezone.utc).strftime('%Y%m%d')}.{ext}"
        archive_tmp = os.path.join(tmp_dir, archive_filename)
        generate_archive(clone_dest, archive_tmp)

        # 4. Move to storage
        os.makedirs(storage_dir, exist_ok=True)
        final_path = os.path.join(storage_dir, archive_filename)
        shutil.move(archive_tmp, final_path)

    logger.info(
        "Archive complete for '%s': '%s'.", repo.full_name, final_path, extra=extra
    )
    return final_path


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    setup_logging()
    logger.info("Git Repository Archiver started.")

    if not GITHUB_TOKEN:
        logger.error("API_KEY is not set. Aborting.")
        raise SystemExit(1)

    if not TARGET_ORG:
        logger.error("TARGET_ORG is not set. Aborting.")
        raise SystemExit(1)

    client = GitHubClient(token=GITHUB_TOKEN)
    repos = client.get_all_repos(TARGET_ORG)
    stale = identify_stale_repos(repos)

    if not stale:
        logger.info("No stale repositories found. Exiting.")
        return

    archived_count = 0
    for repo in stale:
        result = archive_repo(repo, client=client)
        if result:
            archived_count += 1

    logger.info(
        "Archiver completed. %d/%d stale repos successfully archived.",
        archived_count,
        len(stale),
    )


if __name__ == "__main__":
    main()
