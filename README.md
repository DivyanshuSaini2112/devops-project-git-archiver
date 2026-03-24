# devops-project-git-archiver

![CI/CD Pipeline](https://github.com/your-org/devops-project-git-archiver/actions/workflows/ci-cd.yml/badge.svg)
![Coverage](https://img.shields.io/badge/coverage-%3E80%25-brightgreen)
![Python](https://img.shields.io/badge/python-3.11-blue)
![License](https://img.shields.io/badge/license-MIT-lightgrey)
![Pipeline Status](https://img.shields.io/badge/pipeline-passing-brightgreen)

> **Automated detection, archiving & documentation of stale GitHub repositories.**

---

**Student Name:** Divyanshu Saini
**Registration No:** 23FE10CSE00278
**Course:** CSE3253 DevOps [PE6]
**Semester:** VI (2025-2026)
**Project Type:** Git & Agile
**Difficulty:** Intermediate

---

## Problem Statement

Organizations accumulate abandoned or completed repositories over time, creating:

- **Security risks** — stale repos may contain outdated dependencies with known CVEs, exposed secrets, or deprecated credentials.
- **Operational clutter** — teams lose time navigating irrelevant repositories.
- **Storage overhead** — inactive code consumes storage and increases backup costs without business value.

This tool solves all three by automatically identifying stale repos, generating human-readable summaries, and packaging them into compressed archives for long-term storage.

---

## Objectives

- [x] Detect stale GitHub repositories based on configurable inactivity thresholds
- [x] Auto-generate `ARCHIVE_SUMMARY.md` documentation using Jinja2 templates
- [x] Package and compress identified repositories into `tar.gz` or `zip` archives
- [x] Integrate a full CI/CD pipeline with linting, testing, security scanning, and deployment
- [x] Containerise the solution with Docker and deploy via Kubernetes manifests
- [x] Monitor system health using Nagios and structured JSON logging

---

## Key Features

- Configurable staleness threshold (default: 90 days of inactivity)
- Dry-run mode for safe simulation without writing archives
- Dual archive format support: `tar.gz` and `zip`
- Auto-generated per-repository documentation
- >80% test coverage enforced via CI
- Trivy security scanning on every build
- Kubernetes-ready deployment manifests

---

## Technology Stack

### Core Technologies

- **Programming Language:** Python 3.11
- **Framework:** N/A (pure Python CLI tool)
- **Database:** None

### DevOps Tools

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Language | Python 3.11 | Core archiver logic, API calls, file operations |
| API Integration | PyGitHub | Fetch repo metadata, commits, contributors |
| Packaging | tarfile / zipfile (stdlib) | Compress cloned repos |
| Documentation Gen | Jinja2 templates | Auto-generate `ARCHIVE_SUMMARY.md` |
| Version Control | Git | Branching strategy, Agile workflow |
| Testing | pytest + pytest-cov | Unit & integration tests (>80% coverage) |
| Containerisation | Docker + docker-compose | Portable, reproducible runtime |
| Orchestration | Kubernetes manifests | Production cluster deployment |
| CI/CD | GitHub Actions | Lint, test, build, scan, deploy pipeline |
| Security Scanning | Trivy | Container image vulnerability scanning |
| Monitoring | Nagios + JSON logging | System health checks, structured logs |
| Environment Config | .env + python-dotenv | Secure API key management |
| Linting | flake8 / black | Code quality enforcement |

---

## Getting Started

### Prerequisites

- [x] Python 3.11+
- [x] Git 2.30+ (for subprocess clone operations)
- [x] Docker Desktop v20.10+ & docker-compose
- [x] kubectl (for Kubernetes deployment)
- [x] A GitHub Personal Access Token with `repo` and `read:org` scopes

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-org/devops-project-git-archiver.git
   cd devops-project-git-archiver
   ```

2. **Configure environment:**
   ```bash
   cp .env.example src/config/.env
   # Edit src/config/.env with your GitHub token and org name
   nano src/config/.env
   ```

3. **Install dependencies:**
   ```bash
   pip install -r src/main/requirements.txt
   ```

4. **Run locally:**
   ```bash
   python -m src.main.archiver
   ```

### Alternative Installation (with Docker)

```bash
cd infrastructure/docker
docker-compose up --build
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

Create a `.env` file in `src/config/` based on the provided example:

```env
API_KEY=your_github_token_here
TARGET_ORG=your_org_name
STALE_DAYS=90
STORAGE_DIR=./archives
ARCHIVE_FORMAT=tar.gz
LOG_LEVEL=INFO
DRY_RUN=false
```

---

## Project Structure

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

## Testing

### Test Types

- **Unit Tests:** `pytest tests/unit/`
- **Integration Tests:** `pytest tests/integration/`
- **Coverage enforcement:** ≥ 80% required

### Running Tests

```bash
# Unit tests with coverage
pytest tests/unit/ --cov=src/main --cov-report=term-missing --cov-fail-under=80

# Integration tests
pytest tests/integration/ -v

# All tests
pytest --cov=src/main --cov-fail-under=80
```

### Performance Metrics

| Metric | Target | Current |
|--------|--------|---------|
| Build Time | < 5 min | ~3 min |
| Test Coverage | > 80% | >80% |
| Deployment Frequency | Per push to main | On merge |
| Mean Time to Recovery | < 1 hour | < 1 hour |

---

## Docker & Kubernetes

### Docker

```bash
# Build image
docker build -t devops-project-git-archiver:latest .

# Run container
docker run --env-file src/config/.env devops-project-git-archiver:latest

# Run with docker-compose
cd infrastructure/docker
docker-compose up
```

### Kubernetes Deployment

```bash
# Apply K8s manifests
kubectl apply -f infrastructure/kubernetes/

# Check deployment status
kubectl get pods,svc,deploy
```

---

## Monitoring & Logging

### Monitoring Setup

- **Nagios:** Configured for system health checks via `monitoring/nagios/`
- **Custom Checks:** `check_archiver.cfg` validates archiver process status
- **Alerts:** Configurable via Nagios contacts

### Logging

- Structured JSON logging throughout
- Configurable log level via `LOG_LEVEL` env variable
- Optional file output via `LOG_FILE` env variable
- Log retention managed at the infrastructure level

---

## Git Branching Strategy (Agile Workflow)

| Branch | Purpose |
|--------|---------|
| `main` | Production-ready, protected. Merges only from `develop` via PR. |
| `develop` | Integration branch. All feature branches merge here first. |
| `feature/phase-*` | Per-phase feature branches cut from `develop`. |

```
main
└── develop
    ├── feature/phase-1-api-client
    ├── feature/phase-2-archiver-core
    ├── feature/phase-3-doc-generator
    └── feature/phase-4-ci-cd
```

### Commit Convention

- `feat:` — New feature
- `fix:` — Bug fix
- `docs:` — Documentation updates
- `test:` — Test-related changes
- `refactor:` — Code refactoring
- `chore:` — Maintenance tasks

---

## Security

### Security Measures Implemented

- [x] Environment-based configuration (no secrets in code)
- [x] `.env` file gitignored by default
- [x] Trivy container image vulnerability scanning in CI
- [x] Pipeline fails automatically on `CRITICAL` CVEs
- [x] GitHub PAT scoped to minimum required permissions (`repo`, `read:org`)

### Running a Security Scan

```bash
trivy image devops-project-git-archiver:latest
```

---

## Documentation

- [Design Document](docs/design-document.md) — Architecture, data flow, tech decisions
- [User Guide](docs/user-guide.md) — Configuration, usage, interpreting output
- [Troubleshooting Guide](docs/troubleshooting-guide.md) — Common errors and fixes

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'feat: Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request to `develop`

---

## License

MIT — see [LICENSE](LICENSE) for details.
