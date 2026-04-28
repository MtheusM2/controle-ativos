Opus Assets - Asset Management System
Python Flask MySQL Tests Coverage License

Internal platform for centralized asset management, user authentication, and operational traceability. Built with Python, Flask, and MySQL using a modular, production-oriented architecture.

Table of Contents
Features
Architecture
Quick Start
Project Structure
API Overview
Security
Development
Deployment
Contributing
License and Internal Usage
Features
User authentication with login, registration, logout, and password recovery
Asset lifecycle management (create, list, details, update, delete)
Smart asset registration with base data plus dynamic technical specifications by asset type
Automatic timestamps and movement traceability for operational edits
Confirmation modal flow for asset movement review before final save
Structured movement preview with backend-driven status suggestion
Attachment workflow for invoice and warranty documents
Asset export in CSV, XLSX, and PDF formats
CSV import workflow for controlled batch updates
Company-aware access scope with profile-based authorization
Dashboard and settings pages for operational visibility
Modular service layer with centralized validation and business rules
Project Status
Development Phase: Internal Testing & Validation (NOT production-ready yet)

✅ All core modules implemented and tested (authentication, assets, imports, exports)
✅ CSV import/export with round-trip validation (fixed April 27-28, 2026)
✅ 356 automated tests passing with 60.88% code coverage
✅ Multi-tenant support with role-based access control
✅ Comprehensive error handling and validation
⏳ Security audit in progress (see docs/audits/)
⏳ Performance and stress testing pending
⏳ Production deployment testing scheduled
Recent fixes (April 2026):

Fixed CSV export→import round-trip: export now uses canonical field names
Fixed value normalization in import preview: status, setor, tipo_ativo now properly normalized
Added comprehensive round-trip tests (test_roundtrip_preview_seguro.py)
Product and Repository Naming
Product name: Opus Assets
Repository directory name: controle_ativos
This distinction is intentional: product branding remains in English while repository naming preserves operational continuity.
Architecture
The project follows a layered architecture designed for maintainability and controlled growth:

Web Layer (Flask routes, templates, session handling)
    -> Services Layer (business rules, authorization, orchestration)
    -> Models Layer (domain entities)
    -> Database Layer (schema, connection, migrations)
    -> Utilities (crypto, validators, logging)
Core Principles
Separation of concerns across route, service, and persistence boundaries
Authorization based on authenticated user profile and company scope
Reusable validation and normalization rules in shared utility modules
Compatibility routes preserved for legacy navigation without breaking clients
Quick Start
Prerequisites
Python 3.8+ (recommended 3.9+)
MySQL 8.0+
pip
Main Development Flow
Clone and enter repository:
git clone <repository-url>
cd controle_ativos
Create and activate virtual environment:
# Linux/macOS
python -m venv .venv
source .venv/bin/activate

# Windows PowerShell
python -m venv .venv
.venv\Scripts\Activate.ps1
Install dependencies:
pip install -r requirements.txt
Configure environment variables:
# Linux/macOS
cp .env.example .env

# Windows PowerShell
Copy-Item .env.example .env
Initialize schema and migrations:
python database/init_db.py
Start the web application (primary development entrypoint):
python web_app/app.py
Entrypoints
Primary local web entrypoint: python web_app/app.py
Compatibility entrypoint: python app.py
CLI workflow entrypoint: python main.py
Production WSGI entrypoint: wsgi:application (alias wsgi:app)
Essential Environment Variables
Variable	Purpose
DB_HOST	MySQL host
DB_PORT	MySQL port
DB_USER	Application database user
DB_PASSWORD	Database password
DB_NAME	Application database name
FLASK_SECRET_KEY	Session and cookie signing secret
APP_PEPPER	Additional secret for security flows
FLASK_DEBUG	Local debug toggle (0 or 1)
LOG_LEVEL	Runtime log level
LOG_DIR	Log directory path
Project Structure
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
Notes:

Internal private notes are kept in local-only docs_interno_local/, ignored by Git.
Runtime-generated files (uploads, logs, cache, virtualenv) are excluded by .gitignore.
API Overview
Authentication and Session
GET /, GET /login - login page
POST /login - authenticate user
GET /register, POST /register - registration flow
GET /recovery, POST /forgot-password - password recovery flow
POST /logout, GET /logout - session termination
GET /session - active session context
Assets
GET /dashboard - authenticated dashboard
GET /ativos - asset list
POST /ativos - create asset
GET /ativos/<id_ativo> - asset details
PUT /ativos/<id_ativo> - update asset
POST /ativos/<id_ativo>/movimentacao/preview - preview movement without persisting
POST /ativos/<id_ativo>/movimentacao/confirmar - confirm movement and persist final edit
DELETE /ativos/<id_ativo> - delete asset
Attachments and Export
POST /ativos/<id_ativo>/anexos - upload attachment
GET /ativos/<id_ativo>/anexos - list attachments by asset
GET /anexos/<arquivo_id>/download - download attachment
DELETE /anexos/<arquivo_id> - remove attachment
GET /ativos/export/csv|xlsx|pdf - export filtered asset data
POST /ativos/import/csv - import CSV
Import and Export
GET /ativos/export/csv - export assets as CSV (canonical field names)
GET /ativos/export/xlsx - export assets as Excel
GET /ativos/export/pdf - export assets as PDF
POST /importacao/upload-csv - upload CSV for preview analysis
GET /importacao/preview - get import preview with validation results
POST /importacao/confirmar - confirm and process imported assets
Import Workflow:

Upload CSV file
System detects headers and maps to canonical field names
Values are normalized (e.g., "rh" → "Rh", "em uso" → "Em Uso")
Preview shows validation results (valid, warnings, errors)
Confirm to persist changes to database
Export Workflow:

Select filters (sector, status, date range, etc.)
Choose format (CSV, XLSX, PDF)
Download exported file with canonical field names
Exported CSV can be re-imported using the import workflow
Profiles and Permissions
usuario profile: restricted to assets from the authenticated company scope
adm and admin profiles: broader visibility and administrative configuration capabilities
Access checks are enforced in services and applied consistently across list/detail/update/delete and attachment operations
For deeper endpoint and deployment details, see docs/DEPLOYMENT.md.

Security
Implemented controls:

Password hashing with PBKDF2-SHA256
Recovery answer hashing and verification
Session hardening with HTTPOnly and SameSite cookies
Company-aware authorization and permission checks
Centralized input validation and controlled data normalization
Environment-based secrets with .env excluded from repository
Security operations reference:

docs/SECURITY_DB_ROTATION_GUIDE.md
database/security/001_create_opus_app.sql
Development
Running Tests
Quick test run:

pytest
pytest -v
Run specific test modules:

# Import/export and round-trip validation
pytest tests/test_roundtrip_preview_seguro.py -v
pytest tests/test_importacao_exportacao_roundtrip.py -v
pytest tests/test_importacao_massa.py -v

# Authentication and permissions
pytest tests/test_app.py -v
pytest tests/test_permissions.py -v

# Asset CRUD and validation
pytest tests/test_ativos_crud.py -v
pytest tests/test_ativos_validacao.py -v

# Run all tests with detailed output
pytest tests/ -v --tb=short
Test Coverage
Generate coverage report:

# Terminal report with missing lines
pytest --cov=. --cov-report=term-missing

# HTML report (opens in browser)
pytest --cov=. --cov-report=html
open htmlcov/index.html  # macOS
start htmlcov/index.html # Windows PowerShell
Current coverage: 60.88% (356 tests, 4755 statements)

High-coverage modules (>80%):

utils/import_validators.py (89.60%)
utils/csrf.py (95.83%)
utils/auth.py (90.91%)
utils/normalizador_valores_importacao.py (97.30%)
Areas for expansion (<50%):

auth_service.py (17.67%) - tested via integration tests
auditoria_importacao_service.py (31.62%)
storage_backend.py (32.05%)
ativos_arquivo_service.py (51.52%)
Migrations
python database/init_db.py
Local Debug
# Linux/macOS
export FLASK_DEBUG=1
python web_app/app.py

# Windows PowerShell
$env:FLASK_DEBUG=1
python web_app/app.py
Code Quality Guidelines
Follow PEP 8 conventions
Keep services focused on business logic
Keep HTTP serialization concerns in route layer
Preserve backward-compatible routes intentionally documented in route modules
Keep movement review logic in the backend as the source of truth
Keep modal editing limited to operational fields only
Always validate field contracts between layers (CSV mapping, normalization, validation)
Deployment
Production Stack
Component	Technology
OS	Windows Server 2019+
WSGI Server	Waitress 3.0
Windows Service	NSSM (Non-Sucking Service Manager)
Reverse Proxy	IIS (URL Rewrite + Application Request Routing)
Database	MySQL 8
TLS	Managed by IIS
Main Production Flow (Windows Server)
Clone repository to C:\controle_ativos
Run bootstrap as Administrator:
.\scripts\setup_server.ps1
Fill in .env with real credentials and secrets
Apply database schema:
mysql -u root -p < database\schema.sql
Install Windows service (as Administrator):
.\deploy\nssm\install_service.ps1 -ProjectDir "C:\controle_ativos"
Configure IIS as reverse proxy using deploy\iis\web.config
Verify: Invoke-WebRequest http://127.0.0.1:8000/health
Local Production Simulation
# Runs Waitress on port 8001 without debug mode
scripts\simulate_production.ps1
Deployment Artifacts
wsgi.py — WSGI entrypoint (wsgi:application)
waitress_conf.py — Waitress configuration (threads, limits, identity)
deploy/iis/web.config — IIS reverse proxy + security headers
deploy/nssm/install_service.ps1 — Windows service installer
scripts/setup_server.ps1 — Bootstrap for new Windows Server
docs/DEPLOYMENT.md — Full step-by-step deployment guide
docs/SETUP_SERVIDOR_ZERADO.md — Complete guide from zero to HTTPS
Contributing
This is a proprietary internal system for Opus Medical.

Internal contribution flow:

Create branch:
git checkout -b feature/short-description
Commit with objective messages:
git commit -m "feat: describe change"
Open pull request and require review before merge.
External public contributions are not accepted.

License and Internal Usage
Status: Proprietary - All rights reserved.

This software is confidential and intended for authorized internal use. Unauthorized distribution or reproduction is prohibited.

Last Updated: April 28, 2026 (Test Coverage Audit & Import Fix Validation)
