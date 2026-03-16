# =============================================================================
# Git Repository Archiver — Dockerfile
# Base: python:3.11-slim (minimal attack surface)
# =============================================================================

FROM python:3.11-slim

# --- Metadata ---
LABEL maintainer="your-team@example.com"
LABEL description="Automated Git repository archiver"
LABEL version="1.0"

# --- System dependencies ---
# git is needed for subprocess git clone inside archiver.py
RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends \
        git \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# --- Non-root user for security ---
RUN groupadd --gid 1001 archiver \
    && useradd --uid 1001 --gid archiver --shell /bin/bash --create-home archiver

# --- Working directory ---
WORKDIR /app

# --- Python dependencies (installed as root before switching user) ---
COPY src/main/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# --- Application source ---
COPY src/ ./src/

# --- Default env template (real values supplied via env_file or Secrets) ---
COPY .env.example .env

# --- Archive storage directory ---
RUN mkdir -p /app/archives \
    && chown -R archiver:archiver /app

# --- Switch to non-root user ---
USER archiver

# --- Health check: verify Python and core imports are available ---
HEALTHCHECK --interval=60s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "from src.main.archiver import main; print('ok')" || exit 1

# --- Entry point ---
CMD ["python", "-m", "src.main.archiver"]
