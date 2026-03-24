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
# Logging formatters
# ---------------------------------------------------------------------------

# Level label widths for alignment
_LEVEL_COLORS = {
    "DEBUG": "DEBUG   ",
    "INFO": "INFO    ",
    "WARNING": "WARNING ",
    "ERROR": "ERROR   ",
    "CRITICAL": "CRITICAL",
}


class JSONFormatter(logging.Formatter):
    """Emit log records as single-line JSON for machine parsing (file logs)."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
            "repo": getattr(record, "repo", None),
            "logger": record.name,
        }
        return json.dumps(payload)


class PrettyFormatter(logging.Formatter):
    """Human-readable single-line formatter for interactive terminal use."""

    def format(self, record: logging.LogRecord) -> str:
        label = _LEVEL_COLORS.get(record.levelname, record.levelname)
        repo = getattr(record, "repo", None)
        msg = record.getMessage()
        if repo:
            return f"  [{label}]  ({repo})  {msg}"
        return f"  [{label}]  {msg}"


def setup_logging() -> None:
    """Configure root logger.

    * File target  → structured JSON (machine-readable, for CI / log aggregators)
    * Console only → clean PrettyFormatter (human-readable for interactive runs)
    """
    level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)

    if LOG_FILE:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        handler: logging.Handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
        handler.setFormatter(JSONFormatter())
    else:
        handler = logging.StreamHandler()
        handler.setFormatter(PrettyFormatter())

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
    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=stale_days)
    stale: List[Repository] = []

    # Create ONE client for all repos, not one per repo
    client = GitHubClient(token=GITHUB_TOKEN)

    for repo in repos:
        if repo.archived:
            logger.debug("Skipping already-archived repo: %s", repo.full_name)
            continue

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
        raise RuntimeError(f"git clone failed for {repo_url}:\n{result.stderr}")

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
    logger.info("Archive created: '%s' (%.2f MB)", archive_path, size_mb)
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
            clone_url = clone_url.replace("https://", f"https://{GITHUB_TOKEN}@")
        try:
            clone_repo(clone_url, clone_dest)
        except RuntimeError as exc:
            logger.error("Clone failed for '%s': %s", repo.full_name, exc, extra=extra)
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
        archive_filename = (
            f"{repo.name}_{datetime.now(tz=timezone.utc).strftime('%Y%m%d')}.{ext}"
        )
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


def _ask(prompt: str, default: str) -> str:
    """Prompt the user for input, returning default if Enter is pressed."""
    val = input(f"  {prompt} [{default}]: ").strip()
    return val if val else default


def main() -> None:
    # ------------------------------------------------------------------
    # Interactive CLI prompts (before logging so banner appears cleanly)
    # ------------------------------------------------------------------
    print("=" * 34)
    print("  === Git Repository Archiver ===")
    print("=" * 34)
    print()

    target_org = _ask("GitHub Organisation name", TARGET_ORG or "")
    stale_days_str = _ask("Stale threshold (days)", str(STALE_DAYS))
    archive_format = _ask("Archive format (tar.gz/zip)", ARCHIVE_FORMAT)
    dry_run_str = _ask("Dry run? (yes/no)", "yes" if DRY_RUN else "no")
    storage_dir = _ask("Storage directory", STORAGE_DIR)

    # Parse collected values
    try:
        stale_days = int(stale_days_str)
    except ValueError:
        stale_days = STALE_DAYS

    dry_run = dry_run_str.lower() in ("yes", "y", "true", "1")

    # Summary table
    print()
    print("+----------------------+----------------------------------------+")
    print("| Setting              | Value                                  |")
    print("+----------------------+----------------------------------------+")
    print(f"| Organisation         | {target_org:<38} |")
    print(f"| Stale threshold      | {str(stale_days) + ' days':<38} |")
    print(f"| Archive format       | {archive_format:<38} |")
    print(f"| Dry run              | {'Yes' if dry_run else 'No':<38} |")
    print(f"| Storage directory    | {storage_dir:<38} |")
    print("+----------------------+----------------------------------------+")
    print()

    proceed = input("  Proceed? (yes/no) [yes]: ").strip().lower()
    if proceed in ("no", "n"):
        print("  Aborted by user.")
        raise SystemExit(0)

    print()

    # ------------------------------------------------------------------
    # Logging + runtime — use the interactively collected values
    # ------------------------------------------------------------------
    setup_logging()
    logger.info("Git Repository Archiver started.")

    if not GITHUB_TOKEN:
        logger.error("API_KEY is not set. Aborting.")
        raise SystemExit(1)

    if not target_org:
        logger.error("TARGET_ORG is not set. Aborting.")
        raise SystemExit(1)

    client = GitHubClient(token=GITHUB_TOKEN)
    repos = client.get_all_repos(target_org)
    stale = identify_stale_repos(repos, stale_days=stale_days)

    if not stale:
        logger.info("No stale repositories found. Exiting.")
        return

    archived_count = 0
    for repo in stale:
        result = archive_repo(repo, storage_dir=storage_dir, client=client, dry_run=dry_run)
        if result:
            archived_count += 1

    logger.info(
        "Archiver completed. %d/%d stale repos successfully archived.",
        archived_count,
        len(stale),
    )


if __name__ == "__main__":
    main()
