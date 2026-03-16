# Troubleshooting Guide — Git Repository Archiver

---

## Common Errors & Fixes

---

### 1. `.env` Accidentally Committed to Git

**Symptom:** `git status` or `git log` shows `src/config/.env` tracked by git.

**Root Cause:** The `.env` file was added before `.gitignore` was set up.

**Fix:**

```bash
# Remove from git tracking without deleting the file
git rm --cached src/config/.env

# Verify .gitignore contains the entry
grep ".env" .gitignore

# Commit the removal
git commit -m "chore: remove .env from tracking"
git push
```

**IMPORTANT:** Immediately rotate the GitHub token (`API_KEY`) via GitHub Settings → Developer Settings → Personal Access Tokens. Treat the leaked token as compromised even if the repository is private.

---

### 2. GitHub API Authentication Error (401 / 403)

**Symptom:**
```
GithubException: 401 {"message": "Bad credentials", ...}
```

**Root Cause:** `API_KEY` is missing, expired, or lacks the required scopes.

**Fix:**

1. Generate a new token at **GitHub → Settings → Developer settings → Personal access tokens**
2. Ensure these scopes are checked: `repo` (full), `read:org`
3. Update `src/config/.env`:
   ```ini
   API_KEY=ghp_your_new_token_here
   ```
4. Re-run: `python -m src.main.archiver`

---

### 3. GitHub API Rate Limit Exceeded (403 / 429)

**Symptom:**
```
GithubException: 403 {"message": "API rate limit exceeded for ..."}
```

**Root Cause:** GitHub's REST API allows 5,000 requests/hour for authenticated users. Large organisations with many repositories can exhaust this.

**Fix:**

- Check your current rate limit:
  ```python
  from github import Github
  g = Github("your_token")
  print(g.get_rate_limit().core)
  ```
- The rate limit resets every hour. Wait and retry, or use a service account token with higher limits.
- For very large organisations, consider filtering with `STALE_DAYS` set higher (e.g. `365`) to reduce API calls.

---

### 4. `pytest` Coverage Below 80%

**Symptom:**
```
FAIL Required test coverage of 80% not reached. Total coverage: 72.00%
```

**Root Cause:** Some methods in `api_client.py` or `archiver.py` lack unit test coverage.

**Fix:**

Run coverage with missing lines reported:
```bash
pytest tests/unit/ --cov=src/main --cov-report=term-missing
```

Look for uncovered lines in the `MISS` column, then add targeted tests. Common gaps:

- `get_last_commit_date()` IndexError branch (empty repo)
- `get_contributors()` exception branch
- `generate_archive()` zip branch

---

### 5. Docker Build Fails — `requirements.txt` Not Found

**Symptom:**
```
COPY failed: file not found in build context or excluded by .dockerignore: stat src/main/requirements.txt
```

**Root Cause:** Docker build context is not the project root, or the Dockerfile COPY path is wrong.

**Fix:**

Always build from the **project root**:
```bash
docker build -f infrastructure/docker/Dockerfile .
# or
cd infrastructure/docker && docker-compose up  # uses context: ../..
```

Verify the Dockerfile COPY line:
```dockerfile
COPY src/main/requirements.txt ./requirements.txt
```

---

### 6. Docker Container Exits Immediately (Missing `.env`)

**Symptom:** Container starts then exits with:
```
ValueError: GitHub token is required. Set API_KEY in your .env file.
```

**Root Cause:** The `env_file` in `docker-compose.yml` points to `../../src/config/.env` which doesn't exist.

**Fix:**
```bash
cp .env.example src/config/.env
# Fill in API_KEY and TARGET_ORG
docker-compose up
```

---

### 7. Trivy Scan Fails the Pipeline

**Symptom:** GitHub Actions job `security-scan` fails:
```
CRITICAL: 3
Total: 3 (CRITICAL: 3)
```

**Root Cause:** The base image (`python:3.11-slim`) has a known CRITICAL CVE that hasn't been patched yet.

**Fix:**

Option A — Update to the latest patch of the base image:
```dockerfile
FROM python:3.11-slim
# This will pull the latest 3.11 slim build when the image is rebuilt
```

Option B — Pin to a specific digest known to be clean:
```dockerfile
FROM python:3.11-slim@sha256:<latest-clean-digest>
```

Option C — Suppress known false-positives by creating `.trivyignore`:
```
# .trivyignore — only suppress after reviewing the CVE manually
CVE-2023-XXXXX
```

> Never use `exit-code: 0` in the pipeline to silence Trivy — this defeats the purpose of the scan.

---

### 8. Kubernetes Pod CrashLoopBackOff

**Symptom:**
```
NAME                          READY   STATUS             RESTARTS
git-archiver-xxx-yyy          0/1     CrashLoopBackOff   5
```

**Debug commands:**

```bash
# Check pod logs
kubectl logs -l app=git-archiver -n default --previous

# Describe pod for events
kubectl describe pod -l app=git-archiver -n default

# Verify environment variables are set from ConfigMap and Secret
kubectl exec -it <pod-name> -- env | grep -E "API_KEY|TARGET_ORG|STALE_DAYS"
```

**Common causes:**

| Root Cause | Fix |
|-----------|-----|
| ConfigMap key names don't match `config.py` | Verify `configmap.yaml` keys match `os.getenv()` names in `config.py` |
| Secret `archiver-secrets` not created | Run `kubectl create secret generic archiver-secrets ...` |
| PVC not bound | Check `kubectl get pvc archiver-pvc` — must be `Bound` |
| Wrong image reference | Ensure `deployment.yaml` image tag matches what was pushed to GHCR |

---

### 9. `git clone` Subprocess Fails

**Symptom:**
```
RuntimeError: git clone failed for https://github.com/...:
remote: Repository not found.
```

**Root Cause:** The token lacks `repo` scope for private repositories, or the repository URL is incorrect.

**Fix:**

- Verify `API_KEY` has `repo` (full) scope
- Test manually:
  ```bash
  git clone https://<TOKEN>@github.com/org/repo.git /tmp/test-clone
  ```

---

### 10. Nagios Check Returns `UNKNOWN`

**Symptom:**
```
SERVICE STATUS: UNKNOWN - /usr/lib64/nagios/plugins/check_load: No such file or directory
```

**Root Cause:** Plugin path in `commands.cfg` doesn't match the actual path on the host.

**Fix:**

Find the correct plugin path:
```bash
which check_load
# or
find /usr -name check_load 2>/dev/null
```

Update `monitoring/nagios/commands.cfg`:
```
command_line    /usr/lib/nagios/plugins/check_load -w 5,4,3 -c 10,8,6
```

---

## Debug Commands Reference

```bash
# Check what repos would be archived (dry run)
DRY_RUN=true python -m src.main.archiver

# Run with DEBUG logging
LOG_LEVEL=DEBUG python -m src.main.archiver

# Test GitHub API connection
python -c "
from src.main.api_client import GitHubClient
from src.main.config import GITHUB_TOKEN, TARGET_ORG
c = GitHubClient(GITHUB_TOKEN)
repos = c.get_all_repos(TARGET_ORG)
print(f'Found {len(repos)} repositories in {TARGET_ORG}')
"

# Check Docker volume contents
docker run --rm -v git-archiver_archives_data:/data alpine ls -la /data

# Tail Kubernetes logs live
kubectl logs -l app=git-archiver -n default -f

# Force Kubernetes pod restart
kubectl rollout restart deployment/git-archiver -n default
```

---

## Log File Locations

| Environment | Log Location |
|-------------|-------------|
| Local Python | stdout (or `LOG_FILE` if set) |
| Docker | `docker-compose logs archiver` |
| Kubernetes | `kubectl logs -l app=git-archiver` |
| Nagios | `/var/log/nagios/nagios.log` |
