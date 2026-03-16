"""
tests/integration/test_end_to_end.py

End-to-end integration tests.
These tests simulate the full archiver pipeline using a local git repo
(no real GitHub API calls) to verify the components work together.
"""

import os
import subprocess
import tarfile
import tempfile


from src.main.archiver import generate_archive
from src.main.doc_generator import DocGenerator

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _init_local_repo(path: str) -> None:
    """Create a minimal local git repository with one commit."""
    os.makedirs(path, exist_ok=True)
    subprocess.run(["git", "init", path], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", path, "config", "user.email", "test@example.com"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", path, "config", "user.name", "Test User"],
        check=True,
        capture_output=True,
    )
    readme = os.path.join(path, "README.md")
    with open(readme, "w") as f:
        f.write("# Test Repo\n")
    subprocess.run(["git", "-C", path, "add", "."], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", path, "commit", "-m", "Initial commit"],
        check=True,
        capture_output=True,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_doc_generator_and_archive_pipeline():
    """
    Verify that DocGenerator + generate_archive work together end-to-end:
    1. Create a temp directory simulating a cloned repo.
    2. Generate summary.md into it.
    3. Create a .tar.gz archive containing both the source and summary.
    4. Assert the archive exists and contains summary.md.
    """
    with tempfile.TemporaryDirectory() as tmp:
        source_dir = os.path.join(tmp, "my-repo")
        os.makedirs(source_dir)

        # Write a dummy source file
        with open(os.path.join(source_dir, "app.py"), "w") as f:
            f.write('print("hello")\n')

        # Generate summary.md
        summary_path = os.path.join(source_dir, "ARCHIVE_SUMMARY.md")
        gen = DocGenerator()
        gen.generate_summary(
            repo_name="org/my-repo",
            repo_url="https://github.com/org/my-repo",
            description="Integration test repo",
            primary_language="Python",
            languages={"Python": 5000},
            contributors=[{"login": "tester", "commits": 1}],
            recent_commits=[
                {
                    "message": "Initial commit",
                    "date": "2023-01-01T00:00:00",
                    "author": "tester",
                }
            ],
            last_commit_date="2023-01-01T00:00:00+00:00",
            output_path=summary_path,
        )
        assert os.path.exists(summary_path)

        # Create archive
        archive_path = os.path.join(tmp, "my-repo-20230101.tar.gz")
        result = generate_archive(source_dir, archive_path)

        assert os.path.exists(result)
        assert tarfile.is_tarfile(result)

        # Verify summary.md is inside the archive
        with tarfile.open(result) as tar:
            names = tar.getnames()
        summary_in_archive = any("ARCHIVE_SUMMARY.md" in n for n in names)
        assert (
            summary_in_archive
        ), f"ARCHIVE_SUMMARY.md not found in archive. Members: {names}"


def test_archive_contains_source_files():
    """Verify all source files are included in the archive."""
    with tempfile.TemporaryDirectory() as tmp:
        source_dir = os.path.join(tmp, "repo")
        os.makedirs(source_dir)
        files = ["main.py", "utils.py", "README.md"]
        for f in files:
            open(os.path.join(source_dir, f), "w").close()

        archive_path = os.path.join(tmp, "repo.tar.gz")
        generate_archive(source_dir, archive_path)

        with tarfile.open(archive_path) as tar:
            names = tar.getnames()

        for f in files:
            assert any(f in n for n in names), f"{f} not found in archive"


def test_summary_md_is_valid_markdown():
    """Verify generated summary.md starts with a Markdown heading."""
    with tempfile.TemporaryDirectory() as tmp:
        output = os.path.join(tmp, "summary.md")
        gen = DocGenerator()
        gen.generate_summary(
            repo_name="org/valid-md-repo",
            repo_url="https://github.com/org/valid-md-repo",
            description="Testing markdown validity",
            primary_language="Go",
            languages={"Go": 8000, "Makefile": 200},
            contributors=[],
            recent_commits=[],
            last_commit_date=None,
            output_path=output,
        )

        content = open(output).read()
        assert content.startswith(
            "#"
        ), "summary.md should start with a Markdown heading"
