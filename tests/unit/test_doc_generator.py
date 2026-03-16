"""
tests/unit/test_doc_generator.py

Unit tests for src/main/doc_generator.py.
"""

import os
import tempfile


from src.main.doc_generator import DocGenerator

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


SAMPLE_CONTEXT = dict(
    repo_name="my-org/my-repo",
    repo_url="https://github.com/my-org/my-repo",
    description="A sample repository for testing.",
    primary_language="Python",
    languages={"Python": 12000, "Shell": 800, "Dockerfile": 300},
    contributors=[
        {"login": "alice", "commits": 80},
        {"login": "bob", "commits": 45},
    ],
    recent_commits=[
        {
            "message": "feat: add archiver module",
            "date": "2023-06-01T10:00:00",
            "author": "alice",
        },
        {
            "message": "fix: handle empty repos",
            "date": "2023-05-15T08:30:00",
            "author": "bob",
        },
    ],
    last_commit_date="2023-06-01T10:00:00+00:00",
)


# ---------------------------------------------------------------------------
# generate_summary tests
# ---------------------------------------------------------------------------


def test_generate_summary_creates_file():
    with tempfile.TemporaryDirectory() as tmp:
        output = os.path.join(tmp, "summary.md")
        gen = DocGenerator()
        result = gen.generate_summary(**SAMPLE_CONTEXT, output_path=output)

        assert os.path.exists(result)


def test_generate_summary_contains_repo_name():
    with tempfile.TemporaryDirectory() as tmp:
        output = os.path.join(tmp, "summary.md")
        gen = DocGenerator()
        gen.generate_summary(**SAMPLE_CONTEXT, output_path=output)

        content = open(output).read()
        assert "my-org/my-repo" in content


def test_generate_summary_contains_repo_url():
    with tempfile.TemporaryDirectory() as tmp:
        output = os.path.join(tmp, "summary.md")
        gen = DocGenerator()
        gen.generate_summary(**SAMPLE_CONTEXT, output_path=output)

        content = open(output).read()
        assert "https://github.com/my-org/my-repo" in content


def test_generate_summary_contains_contributor_names():
    with tempfile.TemporaryDirectory() as tmp:
        output = os.path.join(tmp, "summary.md")
        gen = DocGenerator()
        gen.generate_summary(**SAMPLE_CONTEXT, output_path=output)

        content = open(output).read()
        assert "alice" in content
        assert "bob" in content


def test_generate_summary_contains_commit_messages():
    with tempfile.TemporaryDirectory() as tmp:
        output = os.path.join(tmp, "summary.md")
        gen = DocGenerator()
        gen.generate_summary(**SAMPLE_CONTEXT, output_path=output)

        content = open(output).read()
        assert "feat: add archiver module" in content


def test_generate_summary_contains_language():
    with tempfile.TemporaryDirectory() as tmp:
        output = os.path.join(tmp, "summary.md")
        gen = DocGenerator()
        gen.generate_summary(**SAMPLE_CONTEXT, output_path=output)

        content = open(output).read()
        assert "Python" in content


def test_generate_summary_contains_archive_date():
    with tempfile.TemporaryDirectory() as tmp:
        output = os.path.join(tmp, "summary.md")
        gen = DocGenerator()
        gen.generate_summary(**SAMPLE_CONTEXT, output_path=output)

        content = open(output).read()
        # Should contain current year at minimum
        import datetime

        assert str(datetime.datetime.now().year) in content


def test_generate_summary_returns_output_path():
    with tempfile.TemporaryDirectory() as tmp:
        output = os.path.join(tmp, "summary.md")
        gen = DocGenerator()
        result = gen.generate_summary(**SAMPLE_CONTEXT, output_path=output)

        assert result == output


def test_generate_summary_handles_empty_contributors():
    context = {**SAMPLE_CONTEXT, "contributors": []}
    with tempfile.TemporaryDirectory() as tmp:
        output = os.path.join(tmp, "summary.md")
        gen = DocGenerator()
        result = gen.generate_summary(**context, output_path=output)

        assert os.path.exists(result)


def test_generate_summary_handles_empty_languages():
    context = {**SAMPLE_CONTEXT, "languages": {}}
    with tempfile.TemporaryDirectory() as tmp:
        output = os.path.join(tmp, "summary.md")
        gen = DocGenerator()
        result = gen.generate_summary(**context, output_path=output)

        content = open(result).read()
        assert "No language data" in content


def test_generate_summary_creates_parent_directories():
    with tempfile.TemporaryDirectory() as tmp:
        output = os.path.join(tmp, "nested", "dir", "summary.md")
        gen = DocGenerator()
        result = gen.generate_summary(**SAMPLE_CONTEXT, output_path=output)

        assert os.path.exists(result)


def test_generate_summary_description_none():
    context = {**SAMPLE_CONTEXT, "description": None}
    with tempfile.TemporaryDirectory() as tmp:
        output = os.path.join(tmp, "summary.md")
        gen = DocGenerator()
        result = gen.generate_summary(**context, output_path=output)

        content = open(result).read()
        assert "No description" in content
