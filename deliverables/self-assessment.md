# Self-Assessment — Git Repository Archiver

**Student/Engineer:** _Your Name_
**Date Submitted:** _YYYY-MM-DD_
**Repository:** https://github.com/your-org/devops-project-git-archiver

---

## Assessment Table

| Assessment Area | Max Marks | Your Score | Evidence / Justification |
|----------------|-----------|-----------|--------------------------|
| Repository Structure | 10 | _/10 | Link to repo + directory tree screenshot. All 11 required directories present with `.gitkeep` files. Named branches (`main`, `develop`, `feature/*`) created and protected. |
| Code Quality | 10 | _/10 | `pytest` coverage report (>80%). `flake8` output showing 0 errors. Modular Python with clear separation: `config.py`, `api_client.py`, `archiver.py`, `doc_generator.py`. |
| DevOps Implementation | 10 | _/10 | Docker build log showing successful image build from `python:3.11-slim`. K8s manifests: `configmap.yaml`, `deployment.yaml`, `service.yaml` all present and applied. |
| CI/CD Pipeline | 10 | _/10 | GitHub Actions run screenshot showing all 6 stages passing: lint → test → build → Trivy scan → push → deploy. |
| Documentation | 10 | _/10 | Links to `README.md` (with CI badge), `docs/design-document.md` (architecture + data flow), `docs/user-guide.md`, `docs/troubleshooting-guide.md`. |
| Presentation | 10 | _/10 | Link to `deliverables/demo-video.mp4` (5–10 min demo showing pipeline, Docker, archiving, and Nagios). |
| **TOTAL** | **60** | **_/60** | |

---

## Phase Completion Summary

| Phase | Description | Status | Notes |
|-------|-------------|--------|-------|
| Phase 1 | Repository setup & Agile planning | ✅ Complete | All directories scaffolded, GitHub Project board created, branch protection on `main`. |
| Phase 2 | Core application development | ✅ Complete | `api_client.py`, `archiver.py`, `doc_generator.py`, `config.py` all implemented with full docstrings. |
| Phase 3 | Testing & Infrastructure (Docker / K8s) | ✅ Complete | Unit tests >80% coverage. Dockerfile, docker-compose, and all 3 K8s manifests present. |
| Phase 4 | CI/CD Pipeline & Security | ✅ Complete | 6-stage GitHub Actions pipeline. Trivy scan with `exit-code: 1`. Secrets managed via GitHub Encrypted Secrets. |
| Phase 5 | Monitoring & Documentation | ✅ Complete | Nagios `commands.cfg` + `check_archiver.cfg`. JSON logging. All 4 docs files complete. |
| Phase 6 | Final Deliverables & Presentation | ⏳ Pending | Demo video to be recorded. Self-assessment scores to be filled in post-review. |

---

## Key Design Decisions

1. **Non-root Docker user** — Image runs as UID 1001 (`archiver`) to follow least-privilege principles.
2. **Trivy exit-code: 1** — Pipeline fails on CRITICAL CVEs; never bypassed with exit-code 0.
3. **Dry-run mode** — `DRY_RUN=true` allows safe validation in staging without writing archives.
4. **Structured JSON logging** — All archive events emit machine-parseable JSON for log aggregators.
5. **Modular Python** — Each concern is isolated; `api_client.py` can be swapped for a GitLab client without touching `archiver.py`.

---

## Challenges & Lessons Learned

_To be completed after finishing the project._

- _e.g., Trivy scan failures required pinning the base image to a specific digest..._
- _e.g., K8s CrashLoopBackOff resolved by correcting Secret key names..._

---

## Links

- **Repository:** https://github.com/your-org/devops-project-git-archiver
- **GitHub Actions:** https://github.com/your-org/devops-project-git-archiver/actions
- **Design Document:** [docs/design-document.md](../docs/design-document.md)
- **Demo Video:** [deliverables/demo-video.mp4](demo-video.mp4) _(to be added)_
