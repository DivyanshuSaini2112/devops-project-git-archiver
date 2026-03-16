# devops-project-git-archiver

![CI/CD Pipeline](https://github.com/your-org/devops-project-git-archiver/actions/workflows/ci-cd.yml/badge.svg)
![Coverage](https://img.shields.io/badge/coverage-%3E80%25-brightgreen)
![Python](https://img.shields.io/badge/python-3.11-blue)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

> **Automated detection, archiving & documentation of stale GitHub repositories.**

---

## Problem Statement

Organizations accumulate abandoned or completed repositories over time, creating:

- **Security risks** — stale repos may contain outdated dependencies with known CVEs, exposed secrets, or deprecated credentials.
- **Operational clutter** — teams lose time navigating irrelevant repositories.
- **Storage overhead** — inactive code consumes storage and increases backup costs without business value.

This tool solves all three by automatically identifying stale repos, generating human-readable summaries, and packaging them into compressed archives for long-term storage.

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Language | Python 3.11 | Core archiver logic, API calls, file operations |
| API Integration | PyGitHub | Fetch repo metadata, commits, contributors |
| Packaging | tarfile / zipfile (stdlib) | Compress cloned repos |
| Documentation Gen | Jinja2 templates | Auto-generate `ARCHIVE_SUMMARY.md` |
| Testing | pytest + pytest-cov | Unit & integration tests (>80% coverage) |
| Containerisation | Docker + docker-compose | Portable, reproducible runtime |
| Orchestration | Kubernetes manifests | Production cluster deployment |
| CI/CD | GitHub Actions | Lint, test, build, scan, deploy pipeline |
| Security Scanning | Trivy | Container image vulnerability scanning |
| Monitoring | Nagios + JSON logging | System health checks, structured logs |
| Environment Config | .env + python-dotenv | Secure API key management |
| Linting | flake8 / black | Code quality enforcement |

---

## Prerequisites

- Python 3.11+
- Git (for subprocess clone operations)
- Docker & docker-compose (for containerised runs)
- kubectl (for Kubernetes deployment)
- A GitHub Personal Access Token with `repo` and `read:org` scopes

---

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/your-org/devops-project-git-archiver.git
cd devops-project-git-archiver
```

### 2. Configure environment

```bash
cp .env.example src/config/.env
# Edit src/config/.env with your GitHub token and org name
nano src/config/.env
```

### 3. Install dependencies

```bash
pip install -r src/main/requirements.txt
```

### 4. Run locally

```bash
python -m src.main.archiver
```

### 5. Run with Docker

```bash
cd infrastructure/docker
docker-compose up
```

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `API_KEY` | ✅ Yes | — | GitHub Personal Access Token |
| `TARGET_ORG` | ✅ Yes | — | GitHub organisation login name |
| `STALE_DAYS` | No | `90` | Days of inactivity before a repo is considered stale |
| `STORAGE_DIR` | No | `./archives` | Directory where final archives are stored |
| `ARCHIVE_FORMAT` | No | `tar.gz` | Archive format: `tar.gz` or `zip` |
| `LOG_LEVEL` | No | `INFO` | Logging verbosity: `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `LOG_FILE` | No | *(stdout)* | Write structured JSON logs to a file path |
| `DRY_RUN` | No | `false` | Set to `true` to simulate without writing archives |

---

## Repository Structure

```
devops-project-git-archiver/
├── src/
│   ├── main/
│   │   ├── archiver.py          # Core orchestration logic
│   │   ├── api_client.py        # GitHub API wrapper (PyGitHub)
│   │   ├── doc_generator.py     # Jinja2-based summary.md generator
│   │   ├── config.py            # Centralised config from .env
│   │   └── requirements.txt     # Python dependencies
│   └── config/
│       └── .env                 # (gitignored) real credentials
├── docs/
│   ├── design-document.md
│   ├── user-guide.md
│   └── troubleshooting-guide.md
├── infrastructure/
│   ├── docker/
│   │   ├── Dockerfile
│   │   ├── docker-compose.yml
│   │   └── .dockerignore
│   └── kubernetes/
│       ├── configmap.yaml
│       ├── deployment.yaml
│       └── service.yaml
├── pipelines/
│   └── ci-cd.yml                # Copy of GitHub Actions workflow
├── tests/
│   ├── unit/
│   │   ├── test_api_client.py
│   │   ├── test_archiver.py
│   │   └── test_doc_generator.py
│   ├── integration/
│   │   └── test_end_to_end.py
│   └── conftest.py
├── monitoring/
│   └── nagios/
│       ├── commands.cfg
│       └── check_archiver.cfg
├── deliverables/
│   ├── final-report.md
│   └── self-assessment.md
├── .github/
│   └── workflows/
│       └── ci-cd.yml
├── .env.example
├── .gitignore
└── README.md
```

---

## Running Tests

```bash
# Unit tests with coverage
pytest tests/unit/ --cov=src/main --cov-report=term-missing --cov-fail-under=80

# Integration tests
pytest tests/integration/ -v

# All tests
pytest --cov=src/main --cov-fail-under=80
```

---

## CI/CD Pipeline

Every push to `develop` or `main` triggers a 6-stage GitHub Actions pipeline:

1. **Lint & Format** — `flake8` + `black --check`
2. **Unit Tests** — `pytest` with coverage ≥ 80%
3. **Build** — `docker build` with layer caching
4. **Security Scan** — `Trivy` image scan; fails on `CRITICAL` CVEs
5. **Push to GHCR** — image tagged and pushed *(main branch only)*
6. **Deploy to Staging** — `kubectl apply` *(main branch only)*

See [`.github/workflows/ci-cd.yml`](.github/workflows/ci-cd.yml) and [`docs/design-document.md`](docs/design-document.md) for full details.

---

## Branching Strategy

| Branch | Purpose |
|--------|---------|
| `main` | Production-ready, protected. Merges only from `develop` via PR. |
| `develop` | Integration branch. All feature branches merge here first. |
| `feature/phase-*` | Per-phase feature branches cut from `develop`. |

---

## Documentation

- [Design Document](docs/design-document.md) — Architecture, data flow, tech decisions
- [User Guide](docs/user-guide.md) — Configuration, usage, interpreting output
- [Troubleshooting Guide](docs/troubleshooting-guide.md) — Common errors and fixes

---

## License

MIT — see [LICENSE](LICENSE) for details.
