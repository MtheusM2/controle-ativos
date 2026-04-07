# Deploying controle-ativos to Render

> This guide covers deploying controle-ativos as a Web Service on Render, a modern cloud platform for Python/Flask applications.

---

## Overview

Render is a cloud platform that simplifies deployment of web applications. controle-ativos can run on Render with:

- **Compute**: Free or Starter Plan (Hobby tier)
- **Database**: External MySQL (PlanetScale, Railway, AWS RDS, etc.)
- **File Storage**: S3-compatible service (AWS S3, Cloudflare R2, Backblaze B2, etc.)
- **WSGI Server**: Gunicorn (native to Linux)

The existing Windows Server deployment path remains **unchanged**. This is an alternative deployment route.

---

## Key Differences from Windows Server

| Aspect | Windows Server | Render (Linux) |
|---|---|---|
| OS | Windows Server 2019+ | Linux (Ubuntu) |
| Process Manager | NSSM (Windows Service) | Render (managed) |
| WSGI Server | Waitress | Gunicorn |
| Reverse Proxy | IIS + ARR | Render (built-in HTTPS) |
| File Storage | Local filesystem (`static/uploads/`) | S3-compatible object storage |
| Startup | `deploy/nssm/install_service.ps1` | `Procfile` + `runtime.txt` |

**Critical**: Render uses **ephemeral filesystems**. Files uploaded to the local filesystem will be deleted on each deploy or restart. All file uploads must go to external object storage (S3-compatible).

---

## Prerequisites

1. A Render account (free tier works for small deployments)
   - https://render.com

2. External MySQL database (choose one):
   - **PlanetScale** (MySQL-compatible SaaS) — easiest option
   - **Railway** (all-in-one platform with MySQL)
   - **AWS RDS** (managed database)
   - **Any external MySQL 8.0+ provider**

3. S3-compatible object storage (choose one):
   - **AWS S3** — industry standard, pay-as-you-go
   - **Cloudflare R2** — cheaper than S3
   - **Backblaze B2** — very affordable
   - **MinIO** (self-hosted) — if you want to run your own

4. Environment variables ready:
   - Database credentials and host
   - S3 credentials and bucket name
   - Flask secrets (FLASK_SECRET_KEY, APP_PEPPER)

---

## Step 1: Prepare Your Repository

Ensure the repository contains these files (created during Render adaptation):

- ✅ `Procfile` — Gunicorn start command
- ✅ `runtime.txt` — Python version
- ✅ `render.yaml` — Optional, but recommended for full IaC
- ✅ `requirements.txt` — Updated with `gunicorn`, `boto3`, and all dependencies
- ✅ `config.py` — Updated with `STORAGE_TYPE`, S3 vars
- ✅ `.env.example` — Updated with S3 variables

**Verify file integrity:**
```bash
# Should exist:
ls -la Procfile runtime.txt requirements.txt render.yaml

# Should have gunicorn and boto3:
grep -E "gunicorn|boto3" requirements.txt
```

---

## Step 2: Set Up External Database

### Option A: PlanetScale (Recommended for simplicity)

1. Go to https://planetscale.com and create a free account
2. Create a new database called `controle_ativos`
3. Go to **Settings → Passwords** and create a new password
4. Copy the connection string:
   ```
   mysql://user:password@host/controle_ativos
   ```
   Parse this into:
   - `DB_HOST=host`
   - `DB_PORT=3306`
   - `DB_USER=user`
   - `DB_PASSWORD=password`
   - `DB_NAME=controle_ativos`

5. Apply the schema locally first (test it):
   ```bash
   mysql -h <DB_HOST> -u <DB_USER> -p<DB_PASSWORD> <DB_NAME> < database/schema.sql
   ```

### Option B: Railway

1. Go to https://railway.app and sign up
2. Create a new MySQL database
3. Copy the connection details from the dashboard
4. Apply schema (same as above)

### Option C: AWS RDS

1. Create an RDS MySQL instance (enable publicly accessible)
2. Update security groups to allow port 3306 inbound
3. Note the endpoint, username, password

---

## Step 3: Set Up Object Storage

### Option A: AWS S3 (Industry Standard)

1. Go to https://console.aws.amazon.com
2. Create a new S3 bucket (e.g., `controle-ativos-prod`)
3. Go to **IAM → Users** and create a new user with S3 programmatic access
4. Attach policy: `AmazonS3FullAccess` (or create a custom policy for that bucket only)
5. Copy credentials:
   - `S3_ACCESS_KEY_ID` (Access Key)
   - `S3_SECRET_ACCESS_KEY` (Secret Access Key)
6. Bucket settings:
   - `S3_BUCKET=controle-ativos-prod`
   - `S3_REGION=us-east-1` (or your region)
   - `S3_ENDPOINT_URL=` (leave empty for AWS)

### Option B: Cloudflare R2 (Cheaper)

1. Go to https://dash.cloudflare.com and enable R2
2. Create a new bucket
3. Create an API token with R2 access
4. Copy credentials and endpoint:
   ```
   S3_ACCESS_KEY_ID=...
   S3_SECRET_ACCESS_KEY=...
   S3_ENDPOINT_URL=https://<account-id>.r2.cloudflarestorage.com
   S3_BUCKET=your-bucket-name
   S3_REGION=auto
   ```

### Option C: Backblaze B2 (Very Affordable)

1. Go to https://www.backblaze.com/b2/cloud-storage.html
2. Create a bucket
3. Create an application key
4. Copy:
   ```
   S3_ACCESS_KEY_ID=<applicationKeyId>
   S3_SECRET_ACCESS_KEY=<applicationKey>
   S3_ENDPOINT_URL=https://s3.us-west-000.backblazeb2.com
   S3_BUCKET=your-bucket-name
   S3_REGION=us-west-000
   ```

---

## Step 4: Create Render Web Service

### Via Render Dashboard (Easiest)

1. Go to https://dashboard.render.com
2. Click **"New +"** → **"Web Service"**
3. Connect your repository (GitHub, GitLab, etc.)
4. Fill in the form:
   - **Name**: `controle-ativos`
   - **Environment**: `Python 3`
   - **Region**: Choose closest to your users
   - **Plan**: Free or Starter (Hobby tier recommended)
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 60 wsgi:application`

5. Click **"Advanced"** and add environment variables (see Step 5)

### Via `render.yaml` (Infrastructure as Code)

1. Push `render.yaml` to your repository
2. In Render dashboard: **Settings → Blueprint**
3. Enter your GitHub repository URL
4. Render will auto-detect and deploy from `render.yaml`

---

## Step 5: Configure Environment Variables

### Critical Variables (Must Set)

In the Render dashboard, go to **Settings → Environment** and add:

```
FLASK_SECRET_KEY=<generate-with: python -c "import secrets; print(secrets.token_hex(32))">
APP_PEPPER=<generate-with: python -c "import secrets; print(secrets.token_hex(32))">
SESSION_COOKIE_SECURE=1

DB_HOST=<from PlanetScale/Railway/RDS>
DB_PORT=3306
DB_USER=<from database setup>
DB_PASSWORD=<from database setup>
DB_NAME=controle_ativos

STORAGE_TYPE=s3
S3_BUCKET=<your bucket name>
S3_REGION=<your region>
S3_ACCESS_KEY_ID=<from S3/R2/B2>
S3_SECRET_ACCESS_KEY=<from S3/R2/B2>
S3_ENDPOINT_URL=<empty for AWS; URL for R2/B2>
```

### Optional Variables (Recommended)

```
FLASK_DEBUG=0
LOG_LEVEL=INFO
DB_CONNECTION_TIMEOUT=30
PBKDF2_ITERATIONS=600000
AUTH_MAX_FAILED_ATTEMPTS=5
AUTH_LOCKOUT_MINUTES=15
SESSION_LIFETIME_MINUTES=120
```

**Tip**: Use Render's built-in secret management. Never commit `.env` with real credentials.

---

## Step 6: Deploy

### First Deploy

1. Ensure all env vars are set (Step 5)
2. Render will automatically build and start your service
3. Watch logs in **Logs** tab
4. Service should be live at `https://<your-service-name>.onrender.com`

### Health Check

Test that the application is healthy:

```bash
curl https://<your-service-name>.onrender.com/health

# Expected response:
# {"ok":true,"status":"healthy"}
```

### Redeploy After Code Changes

```bash
# Option 1: Push to main branch (auto-redeploy if enabled)
git push origin main

# Option 2: Manual redeploy from dashboard
# Dashboard → Service → Manual Deploy
```

---

## Step 7: Test the Application

### Login Flow

1. Open https://<your-service-name>.onrender.com
2. Register a new user or login
3. Verify authentication works

### File Upload

1. Go to **Dashboard → Create Asset**
2. Upload an attachment (PDF, PNG, JPG, etc.)
3. Verify file is uploaded to S3 (check S3 bucket)
4. Download the file
5. Verify S3 presigned URL works (for S3 storage)

### Export

1. Go to **Assets → Export (CSV/XLSX/PDF)**
2. Verify export works (files generated in memory)
3. Download file and inspect

### Database

1. Add several assets
2. Verify data persists in MySQL
3. Logout and login to a different user
4. Verify user sees only their company's assets

---

## Limitations & Known Issues

### 1. Ephemeral Filesystem

⚠️ **All local files are deleted on restart or new deploy.**

**Solution**: Use `STORAGE_TYPE=s3` to store files in S3-compatible storage.

**If you must use local storage** (development only):
```
STORAGE_TYPE=local
```
This will store files in `/tmp/uploads/` (ephemeral). Files will disappear on restart. **Not recommended for production**.

### 2. Cold Starts

First request after a long idle period (free tier) may take 10-30 seconds.

**Solution**: Render's free tier spins down after 15 min of inactivity. Use Starter Plan for always-on.

### 3. Database Connection Timeout

If database is slow to respond:

```
DB_CONNECTION_TIMEOUT=60  # Increase from default 30
```

### 4. Free Tier Limitations

| Limit | Render Free | Starter |
|---|---|---|
| Memory | 512 MB | 2+ GB |
| Disk | None (ephemeral) | 2+ GB |
| Idle auto-stop | Yes (15 min) | No |
| Restart frequency | Multiple times/hour | Stable |

**Recommendation**: Use Starter Plan for production. Free tier is good for testing.

---

## Troubleshooting

### Service fails to start (`503 Bad Gateway`)

1. Check logs:
   ```
   Dashboard → Logs
   ```

2. Common causes:
   - Missing environment variables → Check `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`
   - S3 misconfiguration → Check `S3_BUCKET`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`
   - Missing dependencies → Verify `requirements.txt` has `gunicorn`, `boto3`
   - Python version mismatch → Check `runtime.txt` (should be `python-3.11.8`)

### `/health` endpoint returns 500

1. Database likely misconfigured
2. Test connection locally:
   ```bash
   python scripts/test_db_connection.py
   ```
3. Ensure env vars match database credentials

### File upload fails with S3 error

1. Check S3 credentials in env vars
2. Verify bucket exists and is accessible
3. Check IAM policy allows `s3:PutObject` on the bucket
4. Common error: Wrong `S3_REGION` — match your bucket region

### 413 Payload Too Large

1. Check that `MAX_CONTENT_LENGTH` is set to 10 MB (default)
2. Render allows larger uploads; issue is likely in config

---

## Maintenance

### View Logs

```bash
# Render dashboard → Logs (live tail)
# Or via CLI:
render logs --service-id <service-id> --follow
```

### Restart Service

```
Dashboard → Settings → Restart Instance
```

### Update Code

```bash
git push origin main
# Auto-redeploy if enabled, or:
# Dashboard → Manual Deploy
```

### Update Dependencies

```bash
pip install -r requirements.txt --upgrade
# Update requirements.txt with new pins
git commit -m "chore: update dependencies"
git push origin main
```

### Backup Database

Use your database provider's backup features (PlanetScale, Railway, etc.).

---

## Reverting to Windows Server

The Render deployment path is **completely independent** of Windows Server. If Render doesn't work out:

1. Windows Server deploy remains in `deploy/nssm/`, `deploy/iis/`, `docs/DEPLOYMENT.md`
2. All Windows Server scripts unchanged
3. Simply revert to Windows Server without touching Git history

---

## Next Steps

- [ ] Set up PlanetScale/Railway database
- [ ] Set up S3/R2/B2 storage bucket
- [ ] Create Render account and Web Service
- [ ] Configure all env vars
- [ ] Deploy and test `/health`
- [ ] Test login, asset creation, file upload
- [ ] Monitor logs and performance
- [ ] Set up alerts if needed

---

## Support & Documentation

- **Render Docs**: https://render.com/docs
- **Gunicorn Docs**: https://docs.gunicorn.org/
- **PlanetScale Docs**: https://planetscale.com/docs
- **AWS S3 Docs**: https://docs.aws.amazon.com/s3/
- **Cloudflare R2 Docs**: https://developers.cloudflare.com/r2/

---

**Last Updated:** April 7, 2026
