# User Guide — Git Repository Archiver

---

## 1. Prerequisites

Before running the archiver, ensure you have:

- Python 3.11 or higher
- `git` installed and accessible on your `PATH`
- A GitHub Personal Access Token (PAT) with `repo` and `read:org` scopes
- Docker & docker-compose (for containerised runs)

---

## 2. Configuring `.env`

Copy the example file and fill in your credentials:

```bash
cp .env.example src/config/.env
```

Edit `src/config/.env`:

```ini
# Required
API_KEY=ghp_your_personal_access_token
TARGET_ORG=your-github-organisation-name

# Optional — change defaults if needed
STALE_DAYS=90
STORAGE_DIR=/app/archives
ARCHIVE_FORMAT=tar.gz
LOG_LEVEL=INFO
DRY_RUN=false
```

### Generating a GitHub PAT

1. Go to **GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)**
2. Click **Generate new token (classic)**
3. Enable scopes: `repo` (full) and `read:org`
4. Copy the token immediately — it is only shown once

> ⚠️ Never commit `src/config/.env` to version control. It is already listed in `.gitignore`.

---

## 3. Triggering Archiving

### Option A — Run locally (Python)

```bash
# Install dependencies
pip install -r src/main/requirements.txt

# Run the archiver
python -m src.main.archiver
```

### Option B — Run with Docker Compose

```bash
cd infrastructure/docker
docker-compose up
```

The container reads credentials from `src/config/.env` (via `env_file`) and writes archives to the `archives_data` named volume.

To see real-time logs:

```bash
docker-compose logs -f archiver
```

### Option C — Dry Run (no archives written)

Set `DRY_RUN=true` in your `.env`, then run normally. The tool will log which repositories *would* be archived but perform no cloning, compression, or file writes.

```bash
DRY_RUN=true python -m src.main.archiver
```

### Option D — Kubernetes (production)

```bash
# Create the secret (one-time setup)
kubectl create secret generic archiver-secrets \
  --from-literal=API_KEY=ghp_xxx \
  --from-literal=TARGET_ORG=your-org

# Apply all manifests
kubectl apply -f infrastructure/kubernetes/configmap.yaml
kubectl apply -f infrastructure/kubernetes/deployment.yaml
kubectl apply -f infrastructure/kubernetes/service.yaml

# Monitor the pod
kubectl get pods -l app=git-archiver
kubectl logs -l app=git-archiver -f
```

---

## 4. Viewing Archived Repositories

Archives are stored in `STORAGE_DIR` (default: `./archives` locally, `/app/archives` in Docker/K8s).

Each archive filename follows the pattern:

```
<repo-name>-<YYYYMMDD>.tar.gz
```

Example:

```
archives/
├── old-service-20240101.tar.gz
├── deprecated-api-20240215.tar.gz
└── legacy-frontend-20240301.tar.gz
```

### Extracting an archive

```bash
tar -xzf archives/old-service-20240101.tar.gz -C /tmp/extracted/
ls /tmp/extracted/old-service/
```

---

## 5. Interpreting `ARCHIVE_SUMMARY.md`

Every archive contains an `ARCHIVE_SUMMARY.md` at its root. It includes:

| Section | Description |
|---------|-------------|
| Repository metadata | Name, URL, description, primary language |
| Archive info | Date archived, inactivity threshold that triggered archiving |
| Language breakdown | Percentage of each language by bytes |
| Top contributors | Up to 5 contributors with commit counts |
| Recent commit history | Last 10 commit messages, dates, and authors |

### Example summary snippet

```markdown
# Repository Archive Summary

| Field | Value |
|-------|-------|
| **Repository** | my-org/old-service |
| **URL** | https://github.com/my-org/old-service |
| **Primary Language** | Python |
| **Archive Date** | 2024-03-01 14:30 UTC |
| **Reason** | Inactive for more than 90 days |
| **Last Commit** | 2023-10-15T09:22:00+00:00 |
```

---

## 6. Adjusting the Stale Threshold

The default threshold is **90 days**. To change it, update `STALE_DAYS` in your `.env`:

```ini
STALE_DAYS=180   # Flag repos inactive for 6 months
```

Or override at runtime (without modifying `.env`):

```bash
STALE_DAYS=60 python -m src.main.archiver
```

---

## 7. Changing the Archive Format

The tool supports both `.tar.gz` (default) and `.zip`:

```ini
ARCHIVE_FORMAT=zip
```

`.tar.gz` is recommended for Linux/macOS environments. Use `.zip` when the archives will be shared with Windows users.

---

## 8. Log Output

The archiver emits **structured JSON logs** to stdout (or to `LOG_FILE` if set):

```json
{"timestamp": "2024-03-01 14:30:01,123", "level": "INFO", "message": "Stale repo detected: my-org/old-service (inactive 152 days)", "repo": "my-org/old-service", "logger": "src.main.archiver"}
{"timestamp": "2024-03-01 14:30:15,456", "level": "INFO", "message": "Archive complete for 'my-org/old-service': '/app/archives/old-service-20240301.tar.gz'", "repo": "my-org/old-service", "logger": "src.main.archiver"}
```

To write logs to a file:

```ini
LOG_FILE=/var/log/git-archiver/archiver.log
```

To increase verbosity for debugging:

```ini
LOG_LEVEL=DEBUG
```
