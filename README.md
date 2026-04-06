# Opus Assets - Asset Management System

[![Python](https://img.shields.io/badge/Python-3.8+-blue?logo=python)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.x-black?logo=flask)](https://flask.palletsprojects.com/)
[![MySQL](https://img.shields.io/badge/MySQL-8.0+-orange?logo=mysql)](https://www.mysql.com/)
[![License](https://img.shields.io/badge/License-Proprietary-red)]()

> **Internal platform for centralized asset management, user authentication, and operational traceability. Built with Python, Flask, and MySQL using a modular, production-oriented architecture.**

---

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [API Overview](#api-overview)
- [Security](#security)
- [Development](#development)
- [Deployment](#deployment)
- [Contributing](#contributing)
- [License and Internal Usage](#license-and-internal-usage)

---

## Features

- User authentication with login, registration, logout, and password recovery
- Asset lifecycle management (create, list, details, update, delete)
- Attachment workflow for invoice and warranty documents
- Asset export in CSV, XLSX, and PDF formats
- CSV import workflow for controlled batch updates
- Company-aware access scope with profile-based authorization
- Dashboard and settings pages for operational visibility
- Modular service layer with centralized validation and business rules

### Current Status

- Stable Flask web application with active authentication and asset modules
- Migrations and deploy artifacts maintained in repository
- Production-ready WSGI path and local production simulation scripts available

### Product and Repository Naming

- Product name: **Opus Assets**
- Repository directory name: **controle_ativos**
- This distinction is intentional: product branding remains in English while repository naming preserves operational continuity.

---

## Architecture

The project follows a layered architecture designed for maintainability and controlled growth:

```
Web Layer (Flask routes, templates, session handling)
    -> Services Layer (business rules, authorization, orchestration)
    -> Models Layer (domain entities)
    -> Database Layer (schema, connection, migrations)
    -> Utilities (crypto, validators, logging)
```

### Core Principles

- Separation of concerns across route, service, and persistence boundaries
- Authorization based on authenticated user profile and company scope
- Reusable validation and normalization rules in shared utility modules
- Compatibility routes preserved for legacy navigation without breaking clients

---

## Quick Start

### Prerequisites

- Python 3.8+ (recommended 3.9+)
- MySQL 8.0+
- pip

### Main Development Flow

1. Clone and enter repository:
   ```bash
   git clone <repository-url>
   cd controle_ativos
   ```
2. Create and activate virtual environment:
   ```bash
   # Linux/macOS
   python -m venv .venv
   source .venv/bin/activate

   # Windows PowerShell
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure environment variables:
   ```bash
   # Linux/macOS
   cp .env.example .env

   # Windows PowerShell
   Copy-Item .env.example .env
   ```
5. Initialize schema and migrations:
   ```bash
   python database/init_db.py
   ```
6. Start the web application (primary development entrypoint):
   ```bash
   python web_app/app.py
   ```

### Entrypoints

- Primary local web entrypoint: `python web_app/app.py`
- Compatibility entrypoint: `python app.py`
- CLI workflow entrypoint: `python main.py`
- Production WSGI entrypoint: `wsgi:application` (alias `wsgi:app`)

### Essential Environment Variables

| Variable | Purpose |
|---|---|
| `DB_HOST` | MySQL host |
| `DB_PORT` | MySQL port |
| `DB_USER` | Application database user |
| `DB_PASSWORD` | Database password |
| `DB_NAME` | Application database name |
| `FLASK_SECRET_KEY` | Session and cookie signing secret |
| `APP_PEPPER` | Additional secret for security flows |
| `FLASK_DEBUG` | Local debug toggle (0 or 1) |
| `LOG_LEVEL` | Runtime log level |
| `LOG_DIR` | Log directory path |

---

## Project Structure

```
controle_ativos/
|-- app.py
|-- main.py
|-- wsgi.py
|-- config.py
|-- requirements.txt
|-- pytest.ini
|-- .env.example
|-- .gitignore
|-- README.md
|-- database/
|   |-- connection.py
|   |-- init_db.py
|   |-- schema.sql
|   |-- migrations/
|   `-- security/
|-- models/
|-- services/
|-- utils/
|-- web_app/
|   |-- app.py
|   |-- routes/
|   |-- templates/
|   `-- static/
|-- tests/
|-- scripts/
|-- deploy/
`-- docs/
```

Notes:
- Internal private notes are kept in local-only `docs_interno_local/`, ignored by Git.
- Runtime-generated files (uploads, logs, cache, virtualenv) are excluded by `.gitignore`.

---

## API Overview

### Authentication and Session

- `GET /`, `GET /login` - login page
- `POST /login` - authenticate user
- `GET /register`, `POST /register` - registration flow
- `GET /recovery`, `POST /forgot-password` - password recovery flow
- `POST /logout`, `GET /logout` - session termination
- `GET /session` - active session context

### Assets

- `GET /dashboard` - authenticated dashboard
- `GET /ativos` - asset list
- `POST /ativos` - create asset
- `GET /ativos/<id_ativo>` - asset details
- `PUT /ativos/<id_ativo>` - update asset
- `DELETE /ativos/<id_ativo>` - delete asset

### Attachments and Export

- `POST /ativos/<id_ativo>/anexos` - upload attachment
- `GET /ativos/<id_ativo>/anexos` - list attachments by asset
- `GET /anexos/<arquivo_id>/download` - download attachment
- `DELETE /anexos/<arquivo_id>` - remove attachment
- `GET /ativos/export/csv|xlsx|pdf` - export filtered asset data
- `POST /ativos/import/csv` - import CSV

### Profiles and Permissions

- `usuario` profile: restricted to assets from the authenticated company scope
- `adm` and `admin` profiles: broader visibility and administrative configuration capabilities
- Access checks are enforced in services and applied consistently across list/detail/update/delete and attachment operations

For deeper endpoint and deployment details, see `docs/DEPLOYMENT.md`.

---

## Security

Implemented controls:

- Password hashing with PBKDF2-SHA256
- Recovery answer hashing and verification
- Session hardening with HTTPOnly and SameSite cookies
- Company-aware authorization and permission checks
- Centralized input validation and controlled data normalization
- Environment-based secrets with `.env` excluded from repository

Security operations reference:
- `docs/SECURITY_DB_ROTATION_GUIDE.md`
- `database/security/001_create_opus_app.sql`

---

## Development

### Tests

```bash
pytest
pytest -v
```

### Migrations

```bash
python database/init_db.py
```

### Local Debug

```bash
# Linux/macOS
export FLASK_DEBUG=1
python web_app/app.py

# Windows PowerShell
$env:FLASK_DEBUG=1
python web_app/app.py
```

### Quality Guidelines

- Follow PEP 8 conventions
- Keep services focused on business logic
- Keep HTTP serialization concerns in route layer
- Preserve backward-compatible routes intentionally documented in route modules

---

## Deployment

### Main Production Flow

1. Prepare host and secrets (`.env` from `.env.example`)
2. Install dependencies and initialize database (`python database/init_db.py`)
3. Configure Nginx and systemd from `deploy/`
4. Run Gunicorn with WSGI target:
   ```bash
   gunicorn -c gunicorn.conf.py wsgi:application
   ```

### Local Production Simulation

- Windows: `scripts/simulate_production.ps1`
- Linux/macOS: `scripts/simulate_production.sh`

### Deployment Artifacts

- `wsgi.py`
- `gunicorn.conf.py`
- `deploy/nginx/controle_ativos.conf`
- `deploy/systemd/controle_ativos.service`
- `docs/DEPLOYMENT.md`

---

## Contributing

This is a proprietary internal system for Opus Medical.

Internal contribution flow:

1. Create branch:
   ```bash
   git checkout -b feature/short-description
   ```
2. Commit with objective messages:
   ```bash
   git commit -m "feat: describe change"
   ```
3. Open pull request and require review before merge.

External public contributions are not accepted.

---

## License and Internal Usage

Status: Proprietary - All rights reserved.

This software is confidential and intended for authorized internal use. Unauthorized distribution or reproduction is prohibited.

---

**Last Updated:** April 6, 2026
