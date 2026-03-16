"""
api_client.py - GitHub API wrapper using PyGitHub.
Provides all methods needed to fetch repository metadata, commits,
contributors, and language statistics.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

from github import Github, GithubException
from github.Repository import Repository

from src.main.config import GITHUB_TOKEN, STALE_DAYS

logger = logging.getLogger(__name__)


class GitHubClient:
    """Wrapper around PyGitHub for repository metadata retrieval."""

    def __init__(self, token: str = GITHUB_TOKEN):
        if not token:
            raise ValueError(
                "GitHub token is required. Set API_KEY in your .env file."
            )
        self._client = Github(token)
        logger.info("GitHubClient initialised successfully.")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_all_repos(self, org: str) -> List[Repository]:
        """
        Fetch all repositories in a GitHub organisation.

        Args:
            org: GitHub organisation login name.

        Returns:
            List of Repository objects.
        """
        try:
            organisation = self._client.get_organization(org)
            repos = list(organisation.get_repos())
            logger.info(
                "Fetched %d repositories from organisation '%s'.", len(repos), org
            )
            return repos
        except GithubException as exc:
            logger.error("Failed to fetch repos for org '%s': %s", org, exc)
            raise

    def get_last_commit_date(self, repo: Repository) -> Optional[datetime]:
        """
        Return the UTC datetime of the most recent commit on the default branch.

        Args:
            repo: A PyGitHub Repository object.

        Returns:
            datetime (UTC) or None if the repository has no commits.
        """
        try:
            commits = repo.get_commits()
            latest = commits[0]
            commit_date = latest.commit.author.date
            # Ensure timezone-aware
            if commit_date.tzinfo is None:
                commit_date = commit_date.replace(tzinfo=timezone.utc)
            logger.debug(
                "Last commit for '%s': %s", repo.full_name, commit_date.isoformat()
            )
            return commit_date
        except GithubException as exc:
            logger.warning(
                "Could not fetch commits for '%s': %s", repo.full_name, exc
            )
            return None
        except IndexError:
            logger.warning("Repository '%s' appears to be empty.", repo.full_name)
            return None

    def get_contributors(self, repo: Repository) -> List[str]:
        """
        Return a list of contributor login names (top contributors first).

        Args:
            repo: A PyGitHub Repository object.

        Returns:
            List of GitHub login strings.
        """
        try:
            contributors = list(repo.get_contributors())
            logins = [c.login for c in contributors]
            logger.debug(
                "Found %d contributors for '%s'.", len(logins), repo.full_name
            )
            return logins
        except GithubException as exc:
            logger.warning(
                "Could not fetch contributors for '%s': %s", repo.full_name, exc
            )
            return []

    def get_contributor_stats(self, repo: Repository) -> List[Dict]:
        """
        Return contributor login names with commit counts.

        Returns:
            List of dicts: [{"login": str, "commits": int}, ...]
        """
        try:
            contributors = list(repo.get_contributors())
            stats = [
                {"login": c.login, "commits": c.contributions}
                for c in contributors[:5]
            ]
            return stats
        except GithubException as exc:
            logger.warning(
                "Could not fetch contributor stats for '%s': %s", repo.full_name, exc
            )
            return []

    def get_languages(self, repo: Repository) -> Dict[str, int]:
        """
        Return language breakdown as reported by GitHub (bytes per language).

        Args:
            repo: A PyGitHub Repository object.

        Returns:
            Dict mapping language name -> byte count.
        """
        try:
            langs = repo.get_languages()
            logger.debug("Languages for '%s': %s", repo.full_name, langs)
            return langs
        except GithubException as exc:
            logger.warning(
                "Could not fetch languages for '%s': %s", repo.full_name, exc
            )
            return {}

    def get_recent_commits(self, repo: Repository, limit: int = 10) -> List[Dict]:
        """
        Return the most recent commit messages and dates.

        Args:
            repo: A PyGitHub Repository object.
            limit: Maximum number of commits to return (default 10).

        Returns:
            List of dicts: [{"message": str, "date": str, "author": str}, ...]
        """
        try:
            commits = repo.get_commits()
            results = []
            for commit in list(commits[:limit]):
                results.append(
                    {
                        "message": commit.commit.message.split("\n")[0],
                        "date": commit.commit.author.date.isoformat(),
                        "author": commit.commit.author.name,
                    }
                )
            return results
        except GithubException as exc:
            logger.warning(
                "Could not fetch commits for '%s': %s", repo.full_name, exc
            )
            return []

    def close(self) -> None:
        """Release the underlying HTTP connection pool."""
        self._client.close()
        logger.info("GitHubClient connection closed.")
