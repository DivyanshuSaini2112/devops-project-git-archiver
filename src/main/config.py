"""
config.py - Centralised configuration loading from .env via python-dotenv.
Single source of truth for all environment-driven settings.
"""

import os
from dotenv import load_dotenv

# Load .env from src/config/.env (relative to project root)
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "config", ".env"))
# Also attempt to load from current working directory
load_dotenv()

# --- GitHub / GitLab API ---
GITHUB_TOKEN: str = os.getenv("API_KEY", "")
TARGET_ORG: str = os.getenv("TARGET_ORG", "")
GITLAB_TOKEN: str = os.getenv("GITLAB_TOKEN", "")
GITLAB_URL: str = os.getenv("GITLAB_URL", "https://gitlab.com")

# --- Archiving thresholds ---
STALE_DAYS: int = int(os.getenv("STALE_DAYS", "90"))

# --- Storage ---
STORAGE_DIR: str = os.getenv("STORAGE_DIR", "./archives")
ARCHIVE_FORMAT: str = os.getenv("ARCHIVE_FORMAT", "tar.gz")  # tar.gz | zip

# --- Logging ---
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE: str = os.getenv("LOG_FILE", "")  # Empty = stdout only

# --- Dry run mode (no destructive actions) ---
DRY_RUN: bool = os.getenv("DRY_RUN", "false").lower() == "true"

# --- Summary template path ---
TEMPLATE_DIR: str = os.path.join(os.path.dirname(__file__), "..", "..", "templates")
