# Design Document — Git Repository Archiver

**Version:** 1.0 | **Date:** March 2026 | **Category:** Git & Agile / DevOps

---

## 1. Architecture Overview

The Git Repository Archiver is a Python-based batch tool that runs on a schedule (or on-demand) to detect, document, and compress stale GitHub repositories.

```
┌─────────────────────────────────────────────────────────────┐
│                    Git Repository Archiver                   │
│                                                             │
│  ┌──────────────┐     ┌──────────────┐    ┌─────────────┐  │
│  │  api_client  │────▶│   archiver   │───▶│doc_generator│  │
│  │  (PyGitHub)  │     │ (orchestrator│    │  (Jinja2)   │  │
│  └──────┬───────┘     │    logic)    │    └──────┬──────┘  │
│         │             └──────┬───────┘           │         │
│         │                   │                    │         │
│  ┌──────▼───────┐     ┌──────▼───────┐    ┌──────▼──────┐  │
│  │  GitHub API  │     │  git clone   │    │ summary.md  │  │
│  │  (REST v3)   │     │ (subprocess) │    │  (output)   │  │
│  └──────────────┘     └──────┬───────┘    └─────────────┘  │
│                              │                              │
│                       ┌──────▼───────┐                      │
│                       │  tarfile /   │                      │
│                       │  zipfile     │                      │
│                       └──────┬───────┘                      │
│                              │                              │
│                       ┌──────▼───────┐                      │
│                       │  STORAGE_DIR │                      │
│                       │  (archives/) │                      │
│                       └──────────────┘                      │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Component Descriptions

### 2.1 `config.py`
Single source of truth for all runtime configuration. Reads from `.env` via `python-dotenv`. Exposes typed constants (`STALE_DAYS: int`, `STORAGE_DIR: str`, etc.) consumed by all other modules. Never hard-codes credentials.

### 2.2 `api_client.py` — `GitHubClient`
Wraps `PyGitHub` to provide a stable, testable interface:

| Method | Returns | Purpose |
|--------|---------|---------|
| `get_all_repos(org)` | `List[Repository]` | Fetch all org repos |
| `get_last_commit_date(repo)` | `datetime \| None` | Most recent commit UTC datetime |
| `get_contributors(repo)` | `List[str]` | Login names sorted by contribution |
| `get_contributor_stats(repo)` | `List[Dict]` | Login + commit count (top 5) |
| `get_languages(repo)` | `Dict[str, int]` | Language → byte count |
| `get_recent_commits(repo, limit)` | `List[Dict]` | Last N commit messages, dates, authors |

All methods handle `GithubException` gracefully and return empty / `None` values rather than crashing the pipeline.

### 2.3 `archiver.py` — Core Orchestrator
Controls the full pipeline for each stale repository:

```
identify_stale_repos()
    └─▶ for each stale repo:
           archive_repo()
               ├─▶ clone_repo()          # git clone --depth 1
               ├─▶ DocGenerator.generate_summary()
               ├─▶ generate_archive()    # .tar.gz or .zip
               └─▶ shutil.move()         # → STORAGE_DIR
```

Also configures structured JSON logging via `JSONFormatter`.

### 2.4 `doc_generator.py` — `DocGenerator`
Uses Jinja2 to render `ARCHIVE_SUMMARY.md` from repo metadata. Falls back to an inline template if no template files are found on disk. Output includes repo metadata, language percentages, top contributors, and recent commit history.

---

## 3. Data Flow

```
GitHub REST API
      │
      ▼
get_all_repos(org)           # all org repos
      │
      ▼
identify_stale_repos()       # filter: last_commit < now - STALE_DAYS
      │
      ├── [active repos]  ──▶  skip
      │
      └── [stale repos]
              │
              ▼
         archive_repo()
              ├──▶ get_contributor_stats()  ─┐
              ├──▶ get_recent_commits()      │  metadata
              ├──▶ get_languages()           │  collection
              └──▶ get_last_commit_date()   ─┘
                       │
                       ▼
                 clone_repo()            # git clone --depth 1 to /tmp
                       │
                       ▼
              generate_summary()         # writes ARCHIVE_SUMMARY.md
                       │
                       ▼
              generate_archive()         # .tar.gz wrapping source + summary
                       │
                       ▼
              shutil.move()             # → STORAGE_DIR/repo-YYYYMMDD.tar.gz
```

---

## 4. Containerisation

### Docker
- Base image: `python:3.11-slim` (minimal OS footprint, reduced CVE surface)
- Non-root user `archiver` (UID 1001) for least-privilege execution
- Credentials never baked into the image — supplied via `env_file` or Kubernetes Secrets
- Archive output stored in `/app/archives`, mounted as a named Docker volume

### Kubernetes
- **Deployment** with `replicas: 1` (batch job pattern — no horizontal scaling needed)
- Non-secret config loaded from `ConfigMap`; secrets from a `Secret` object
- `PersistentVolumeClaim` (`10Gi`) for archive storage
- Resource limits: 1 CPU / 512 MiB RAM; requests: 0.25 CPU / 128 MiB RAM

---

## 5. CI/CD Pipeline Design

```
Push to develop/main
        │
        ▼
┌──────────────────┐
│ 1. Lint & Format  │  flake8 + black --check  (fails fast)
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 2. Unit Tests     │  pytest --cov --cov-fail-under=80
└────────┬─────────┘
         │
         ▼  (push only — not PRs)
┌──────────────────┐
│ 3. Docker Build   │  docker build → saved as artifact
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 4. Trivy Scan     │  exit-code: 1 on CRITICAL CVEs
└────────┬─────────┘
         │
         ▼  (main only)
┌──────────────────┐
│ 5. Push to GHCR   │  tagged with git SHA + latest
└────────┬─────────┘
         │
         ▼  (main only)
┌──────────────────┐
│ 6. Deploy Staging │  kubectl apply → rollout status
└──────────────────┘
```

**Security posture:**
- Secrets (`API_KEY`, `KUBE_CONFIG_DATA`) stored as GitHub Encrypted Secrets — never in YAML
- All action versions pinned (e.g. `actions/checkout@v4`) to prevent supply-chain attacks
- Trivy SARIF results uploaded to GitHub Security tab
- `concurrency` group cancels stale runs on the same branch

---

## 6. Monitoring Design

Nagios monitors four service checks on the archiver host:

| Check | Plugin | Warning | Critical |
|-------|--------|---------|---------|
| CPU Load | `check_load` | 5,4,3 | 10,8,6 |
| Disk `/app/archives` | `check_disk` | <20% free | <10% free |
| Memory | `check_mem` | >80% used | >95% used |
| Archiver process | `check_procs` | <1 proc | <1 proc |

Structured JSON log output (written to stdout or `LOG_FILE`) enables log aggregators (ELK, Loki, CloudWatch) to parse and alert on archive events.

---

## 7. Technology Decisions & Rationale

| Decision | Alternative Considered | Rationale |
|----------|----------------------|-----------|
| `python:3.11-slim` base | `python:3.11-alpine` | `slim` avoids musl libc compatibility issues with compiled Python packages |
| `PyGitHub` | Raw `requests` | Higher-level abstraction reduces boilerplate and handles rate limiting gracefully |
| `tarfile` stdlib | `zipfile` stdlib | `.tar.gz` is the standard for Unix/Linux deployments; both are supported via `ARCHIVE_FORMAT` |
| Jinja2 templates | f-strings | Separates presentation from logic; allows swapping templates without changing Python code |
| GitHub Actions | Jenkins / GitLab CI | Native GitHub integration; no additional infrastructure to maintain |
| Trivy | Snyk / Grype | Fully open-source; no API key required; excellent GHCR/SARIF integration |
| Nagios | Prometheus + Grafana | Matches the PRD specification; lower operational overhead for a single-host tool |

---

## 8. Security Considerations

- `.env` is explicitly excluded from git via `.gitignore`; committed secrets require immediate token rotation
- Docker image runs as UID 1001 (non-root)
- Kubernetes Secrets (not ConfigMap) hold `API_KEY` and `TARGET_ORG`
- GitHub token embedded in clone URL is never logged (log messages use `repo.full_name`, not the URL)
- Trivy pipeline gate prevents deployment of images with known CRITICAL vulnerabilities
- All GitHub Actions use pinned SHA/tag versions to prevent supply-chain attacks
