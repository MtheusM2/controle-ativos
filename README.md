# Opus Assets — Asset Management System

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![Flask](https://img.shields.io/badge/Flask-2.x-black?logo=flask)
![MySQL](https://img.shields.io/badge/MySQL-8.0-orange?logo=mysql)
![Tests](https://img.shields.io/badge/Tests-356%20passing-brightgreen)
![Coverage](https://img.shields.io/badge/Coverage-60.88%25-yellow)
![Status](https://img.shields.io/badge/Status-Internal%20Testing-blue)
![License](https://img.shields.io/badge/License-Proprietary-red)

> Internal platform for centralized asset management, user authentication, operational traceability, document control, CSV import/export, and controlled validation workflows.

---

## Table of Contents

- [Overview](#overview)
- [Project Status](#project-status)
- [Features](#features)
- [Architecture](#architecture)
- [Technology Stack](#technology-stack)
- [Quick Start](#quick-start)
- [Environment Variables](#environment-variables)
- [Project Structure](#project-structure)
- [Import and Export Workflow](#import-and-export-workflow)
- [Testing](#testing)
- [Coverage](#coverage)
- [API Overview](#api-overview)
- [Security](#security)
- [Deployment](#deployment)
- [Repository Organization](#repository-organization)
- [Contributing](#contributing)
- [License and Internal Usage](#license-and-internal-usage)

---

## Overview

**Opus Assets** is an internal asset management system developed for operational control, traceability, and documentation of corporate assets.

The system centralizes asset registration, lifecycle management, movement tracking, attachments, filtered exports, and controlled CSV import workflows.

The application was built with a modular backend architecture using **Python**, **Flask**, and **MySQL**, with separated layers for routes, services, models, database access, validation, and utilities.

---

## Project Status

Current phase: **Internal Testing and Validation**

The system is under active internal validation and should not yet be considered a final production release.

### Current validated state

- Core asset CRUD implemented and tested
- User authentication and session handling implemented
- Role-based and company-aware access control implemented
- CSV export and import workflow validated
- CSV export → import round-trip fixed and tested
- Import preview and confirmation flow validated
- Asset movement preview and confirmation implemented
- Attachments workflow implemented
- Export formats available: CSV, XLSX, and PDF
- Automated tests passing
- Repository cleanup and documentation audit completed

### Current metrics

| Metric | Value |
|---|---:|
| Automated tests | 356 passing |
| Skipped tests | 19 |
| Test failures | 0 |
| Coverage | 60.88% |
| Python version used in audit | 3.11.9 |
| Last validation date | 2026-04-28 |

### Pending before final production use

- Security review
- Production deployment validation
- Performance and stress testing
- Final data governance review
- Controlled homologation with real internal users

---

## Features

### Authentication and access

- Login and logout
- User registration flow
- Password recovery flow
- Session validation
- Profile-based access control
- Company-aware data scope

### Asset management

- Asset creation
- Asset listing
- Asset detail view
- Asset editing
- Asset deletion
- Dynamic asset fields by asset type
- Status control
- Sector and location control
- Technical specifications by equipment type

### Movement and traceability

- Backend-driven movement preview
- Confirmation flow before final persistence
- Automatic timestamp handling
- Movement-related status validation
- Operational audit support

### Attachments

- Invoice attachment workflow
- Warranty attachment workflow
- Attachment listing
- Attachment download
- Attachment deletion

### Import and export

- CSV export
- XLSX export
- PDF export
- CSV import preview
- Column mapping
- Value normalization
- Validation by line
- Import with warning control
- Export → import round-trip support

---

## Architecture

The project follows a layered architecture:

```text
Web Layer
Flask routes, templates, sessions, request/response handling

Services Layer
Business rules, orchestration, authorization, import/export workflow

Models Layer
Domain entities and structured data objects

Database Layer
Connection, schema, migrations, persistence

Utilities Layer
Validators, normalization, permissions, security helpers, logging
```

### Core principles

- Separation of concerns between route, service, model, and persistence layers
- Business rules concentrated in services
- Validation and normalization centralized in utility modules
- Route layer focused on HTTP contracts
- Import/export workflow protected by tests
- Sensitive configuration excluded from version control

---

## Technology Stack

| Area | Technology |
|---|---|
| Language | Python 3.11 |
| Web framework | Flask |
| Database | MySQL |
| WSGI server | Waitress |
| Frontend | HTML, CSS, Jinja2, JavaScript |
| Tests | Pytest |
| Coverage | pytest-cov |
| Excel export | openpyxl |
| PDF export | ReportLab |
| Deployment target | Windows Server / IIS / NSSM / Waitress |

---

## Quick Start

### Prerequisites

- Python 3.11 recommended
- MySQL 8.0+
- pip
- Git

### Clone repository

```bash
git clone <repository-url>
cd controle_ativos
```

### Create virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Linux/macOS:

```bash
python -m venv .venv
source .venv/bin/activate
```

### Install dependencies

```bash
pip install -r requirements.txt
```

### Configure environment

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Linux/macOS:

```bash
cp .env.example .env
```

Then edit `.env` with the correct local database and application settings.

### Initialize database

```bash
python database/init_db.py
```

### Run application locally

```bash
python web_app/app.py
```

Default local address:

```text
http://127.0.0.1:5000
```

---

## Environment Variables

| Variable | Purpose |
|---|---|
| `DB_HOST` | MySQL host |
| `DB_PORT` | MySQL port |
| `DB_USER` | Database user |
| `DB_PASSWORD` | Database password |
| `DB_NAME` | Database name |
| `FLASK_SECRET_KEY` | Flask session secret |
| `APP_PEPPER` | Additional application secret |
| `FLASK_DEBUG` | Debug mode flag |
| `LOG_LEVEL` | Application log level |
| `LOG_DIR` | Log directory path |

`.env` must never be committed.

`.env.example` must remain versioned with safe placeholder values only.

---

## Project Structure

```text
controle_ativos/
├── app.py
├── config.py
├── main.py
├── requirements.txt
├── pytest.ini
├── .coveragerc
├── .env.example
├── .gitignore
├── README.md
├── wsgi.py
├── waitress_conf.py
│
├── database/
│   ├── connection.py
│   ├── init_db.py
│   ├── schema.sql
│   ├── migrations/
│   └── security/
│
├── deploy/
│   ├── iis/
│   └── nssm/
│
├── docs/
│   ├── audits/
│   ├── guides/
│   └── security/
│
├── models/
├── scripts/
├── services/
├── tests/
├── utils/
└── web_app/
    ├── app.py
    ├── routes/
    ├── static/
    └── templates/
```

---

## Import and Export Workflow

### Export workflow

The system can export asset data in:

- CSV
- XLSX
- PDF

CSV export uses canonical field names to improve compatibility with the import workflow.

### Import workflow

The CSV import process follows these steps:

1. Upload CSV file
2. Detect and map columns
3. Normalize values
4. Validate each line
5. Show preview with errors and warnings
6. Confirm import mode
7. Persist valid records

### Supported import behaviors

- Automatic column recognition
- Canonical field mapping
- `tipo` → `tipo_ativo`
- `departamento` → `setor`
- Status normalization
- Sector normalization
- Asset type normalization
- Warnings separated from blocking errors
- Import of valid lines with warnings when allowed

### Validated round-trip

The system now supports:

```text
Export CSV → Import same CSV → Validate → Confirm import
```

This flow is covered by automated tests.

---

## Testing

### Run all tests

```bash
pytest -v
```

Expected result from the latest audit:

```text
356 passed, 19 skipped
```

### Run import/export tests

```bash
pytest tests/test_importacao_massa.py -v
pytest tests/test_importacao_exportacao_roundtrip.py -v
pytest tests/test_roundtrip_preview_seguro.py -v
pytest tests/test_importacao_confirmacao_mapeamento.py -v
pytest tests/test_importacao_preview_rota_real.py -v
```

### Run asset tests

```bash
pytest tests/test_ativos_crud.py -v
pytest tests/test_ativos_validacao.py -v
pytest tests/test_ativos_arquivo.py -v
```

### Run authentication and permissions tests

```bash
pytest tests/test_app.py -v
pytest tests/test_permissions.py -v
pytest tests/test_csrf_hardening.py -v
```

---

## Coverage

### Generate terminal coverage report

```bash
pytest --cov=. --cov-report=term-missing
```

### Generate HTML coverage report

```bash
pytest --cov=. --cov-report=html
```

Open the generated report:

Windows PowerShell:

```powershell
start htmlcov/index.html
```

Linux/macOS:

```bash
open htmlcov/index.html
```

### Latest measured coverage

| Metric | Value |
|---|---:|
| Total coverage | 60.88% |
| Covered statements | 2,895 |
| Total statements | 4,755 |
| Missing statements | 1,860 |

### High-coverage modules

| Module | Coverage |
|---|---:|
| `utils/email_inference.py` | 100% |
| `utils/normalizador_valores_importacao.py` | 97.30% |
| `utils/csrf.py` | 95.83% |
| `utils/auth.py` | 90.91% |
| `utils/import_validators.py` | 89.60% |
| `models/ativos.py` | 100% |

### Areas for future test expansion

| Module | Current coverage | Priority |
|---|---:|---|
| `services/auth_service.py` | 17.67% | High |
| `services/storage_backend.py` | 32.05% | Medium |
| `services/auditoria_importacao_service.py` | 31.62% | Medium |
| `services/ativos_arquivo_service.py` | 51.52% | Medium |

---

## API Overview

### Authentication

| Method | Route | Description |
|---|---|---|
| GET | `/` | Redirect/login entry |
| GET | `/login` | Login page |
| POST | `/login` | Authenticate user |
| GET | `/register` | Registration page |
| POST | `/register` | Register user |
| GET | `/recovery` | Recovery page |
| POST | `/forgot-password` | Password recovery |
| GET/POST | `/logout` | End session |
| GET | `/session` | Session context |

### Assets

| Method | Route | Description |
|---|---|---|
| GET | `/dashboard` | Dashboard |
| GET | `/ativos` | Asset list |
| POST | `/ativos` | Create asset |
| GET | `/ativos/<id_ativo>` | Asset detail |
| PUT | `/ativos/<id_ativo>` | Update asset |
| DELETE | `/ativos/<id_ativo>` | Delete asset |
| POST | `/ativos/<id_ativo>/movimentacao/preview` | Movement preview |
| POST | `/ativos/<id_ativo>/movimentacao/confirmar` | Confirm movement |

### Attachments

| Method | Route | Description |
|---|---|---|
| POST | `/ativos/<id_ativo>/anexos` | Upload attachment |
| GET | `/ativos/<id_ativo>/anexos` | List attachments |
| GET | `/anexos/<arquivo_id>/download` | Download attachment |
| DELETE | `/anexos/<arquivo_id>` | Delete attachment |

### Export and import

| Method | Route | Description |
|---|---|---|
| GET | `/ativos/export/csv` | Export CSV |
| GET | `/ativos/export/xlsx` | Export XLSX |
| GET | `/ativos/export/pdf` | Export PDF |
| GET | `/ativos/importacao` | Import page |
| POST | `/ativos/importar/preview` | Import preview |
| POST | `/ativos/importar/confirmar` | Confirm import |

---

## Security

Implemented controls:

- Password hashing with PBKDF2-SHA256
- Recovery answer hashing
- Session cookies with HTTPOnly and SameSite controls
- CSRF hardening for protected operations
- Profile-based permission checks
- Company-aware access scope
- Centralized input validation
- CSV import validation and normalization
- Environment-based secrets
- `.env` excluded from version control

Security references:

```text
docs/SECURITY_DB_ROTATION_GUIDE.md
database/security/001_create_opus_app.sql
```

### Important security note

If any real password, token, certificate, private key, or sensitive company data is accidentally committed, it must be rotated immediately.

Removing the file from the current branch does not automatically remove it from Git history.

---

## Deployment

### Production-oriented stack

| Component | Technology |
|---|---|
| Operating system | Windows Server |
| WSGI server | Waitress |
| Service manager | NSSM |
| Reverse proxy | IIS |
| Database | MySQL |
| TLS | IIS certificate binding |

### WSGI entrypoint

```text
wsgi:application
```

### Main deployment references

```text
deploy/iis/
deploy/nssm/
docs/DEPLOYMENT.md
docs/SETUP_SERVIDOR_ZERADO.md
```

### Local production simulation

```powershell
scripts\simulate_production.ps1
```

---

## Repository Organization

The repository was cleaned and reorganized to separate source code, tests, deployment files, and documentation.

### Documentation folders

```text
docs/audits/   Technical audit reports
docs/guides/   Operational guides
docs/security/ Security and database hardening notes
```

### Ignored local artifacts

The `.gitignore` excludes:

- Virtual environments
- `.env` files
- Logs
- CSV exports
- Upload folders
- Cache folders
- Temporary debug files
- Local Claude configuration
- Certificates and private keys
- Database dumps

---

## Contributing

This is a proprietary internal system.

Recommended internal flow:

```bash
git checkout -b feature/short-description
git add .
git commit -m "feat: describe change"
git push origin feature/short-description
```

Then open a pull request for review before merging into `main`.

### Commit message examples

```text
feat: adiciona nova funcionalidade
fix: corrige falha de validação
test: adiciona cobertura automatizada
docs: atualiza documentação
chore: organiza estrutura do repositório
refactor: melhora arquitetura sem alterar comportamento
```

---

## License and Internal Usage

Status: **Proprietary — All rights reserved**

This software is confidential and intended for authorized internal use only.

Unauthorized distribution, publication, or reproduction is prohibited.

---

## Last Updated

2026-04-28 — Test coverage audit, import/export validation, README review, and repository cleanup.
