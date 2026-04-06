# Opus Assets – Asset Management System

[![Python](https://img.shields.io/badge/Python-3.8+-blue?logo=python)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.x-black?logo=flask)](https://flask.palletsprojects.com/)
[![MySQL](https://img.shields.io/badge/MySQL-8.0+-orange?logo=mysql)](https://www.mysql.com/)
[![License](https://img.shields.io/badge/License-Proprietary-red)]()

> **Internal platform for centralized asset management, user authentication, and operational traceability. Built with Python, Flask, and MySQL for scalable, modular architecture.**

---

## 📋 Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [API Overview](#api-overview)
- [Security](#security)
- [Development](#development)
- [Contributing](#contributing)

---

## ✨ Features

- **User Authentication**: Secure login, registration, and password recovery
- **Asset Management**: Create, read, update, delete assets with full audit trail
- **Role-Based Access Control**: Support for user and admin profiles
- **Advanced Filtering**: Search and filter assets by department, responsible, status, and date ranges
- **Centralized Validation**: Consistent business rules and data integrity
- **MySQL Integration**: Persistent, relational data storage
- **Web Layer**: Flask-based web application with template rendering
- **Modular Architecture**: Clean separation of concerns (database, models, services, utilities)

---

## 🏗️ Architecture

The system follows a **layered architecture** for maintainability and scalability:

```
┌─────────────────────────────┐
│    Web Layer (Flask)        │ ← HTTP routes, templates, sessions
├─────────────────────────────┤
│   Services Layer            │ ← Business logic, validations, orchestration
├─────────────────────────────┤
│   Models Layer              │ ← Domain entities (Usuario, Ativo)
├─────────────────────────────┤
│   Database Layer            │ ← MySQL connection, schema, migrations
├─────────────────────────────┤
│   Utilities                 │ ← Crypto, validators, helpers
└─────────────────────────────┘
```

### Key Principles

- **Separation of Concerns**: Each layer has a single, well-defined responsibility
- **Centralized Validation**: Business rules live in `utils/` and `services/`
- **Stateless Services**: Services don't maintain state; they operate on data
- **Testability**: Layered design enables unit and integration testing
- **Scalability**: Modular structure supports incremental growth and feature additions

---

## 🚀 Quick Start

### Prerequisites

- **Python** 3.8+ (recommend 3.9+)
- **MySQL** 8.0+
- **pip** 3.6+ (or poetry)

### Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd opus-assets
   ```

2. **Create virtual environment:**
   ```bash
   # Linux / macOS
   python -m venv .venv
   source .venv/bin/activate
   
   # Windows
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   ```bash
   # Copy template
   cp .env.example .env
   
   # Edit with your credentials
   nano .env  # or use your editor
   ```
   
   **Required variables:**
   - `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`
   - `FLASK_SECRET_KEY` (generate with: `python -c "import secrets; print(secrets.token_hex(32))"`)
   - `APP_PEPPER` (generate with: `python -c "import secrets; print(secrets.token_hex(32))"`)

5. **Initialize database:**
   ```bash
   python database/init_db.py
   ```

6. **Start the application:**
   ```bash
   # Web interface (default: http://localhost:5000)
   python web_app/app.py
   
   # Or CLI terminal mode
   python main.py
   ```

### Troubleshooting: Virtual Environment on Windows

If you see a `WindowsApps` error, recreate the environment:

```powershell
Remove-Item -Recurse -Force .venv
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

---

## 📁 Project Structure

```
opus-assets/
│
├── database/                 # Database layer
│   ├── connection.py         # MySQL connection pool
│   ├── init_db.py            # Database initialization
│   ├── schema.sql            # Schema definition
│   └── migrations/           # SQL migration scripts
│
├── models/                   # Domain models
│   ├── usuario.py            # User entity
│   └── ativos.py             # Asset entity
│
├── services/                 # Business logic layer
│   ├── auth_service.py       # Authentication and user management
│   ├── ativos_service.py     # Asset management and operations
│   └── sistema_ativos.py     # CLI system (terminal interface)
│
├── utils/                    # Utilities and shared functions
│   ├── crypto.py             # Password hashing and verification
│   ├── validators.py         # Input validation and business rules
│   └── validators.py         # Additional validators
│
├── web_app/                  # Flask web application
│   ├── app.py                # Flask app initialization
│   ├── routes/               # HTTP endpoints
│   │   ├── auth_routes.py    # Authentication endpoints
│   │   └── ativos_routes.py  # Asset endpoints
│   ├── templates/            # HTML templates (Jinja2)
│   └── static/               # CSS, JavaScript, images
│
├── main.py                   # Entry point (CLI mode)
├── requirements.txt          # Project dependencies
├── .env.example              # Environment variables template
├── .gitignore               # Git ignore rules
└── README.md                # This file
```

---

## 🔌 API Overview

### Authentication Routes

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Login page |
| `GET` | `/register` | Registration page |
| `GET` | `/recovery` | Password recovery page |
| `POST` | `/login` | Authenticate user |
| `POST` | `/register` | Register new user |
| `GET` | `/logout` | Web logout (redirect to login/home) |
| `POST` | `/logout` | End session |
| `POST` | `/forgot-password` | Initiate password recovery and reset password |
| `GET` | `/session` | Return current authenticated session context |

### Asset Routes

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/dashboard` | Main authenticated dashboard |
| `GET` | `/ativos` | List assets in JSON |
| `POST` | `/ativos` | Create asset |
| `GET` | `/ativos/<id>` | Get asset details |
| `PUT` | `/ativos/<id>` | Update asset |
| `DELETE` | `/ativos/<id>` | Delete asset |
| `GET` | `/ativos/lista` | Legacy compatibility redirect |
| `GET` | `/ativos/novo` | Legacy compatibility redirect |
| `GET` | `/ativos/editar/<id>` | Legacy compatibility redirect |
| `POST` | `/ativos/remover/<id>` | Legacy compatibility redirect |

### Current Scope

- Dashboard remains a summary view with KPIs and preview.
- Full asset list, details, create, and edit run on dedicated pages.
- Authentication screens use fetch with JSON responses and web-compatible logout.
- Attachment HTTP routes are active and integrated in list/create/edit/detail flows.

---

## 🔒 Security

### Implemented Protections

- **Password Hashing**: PBKDF2-SHA256 
- **Recovery Hash**: Security question answers are hashed, never stored in plain text
- **Session Management**: HTTP-only cookies with SameSite protection
- **Environment Isolation**: Sensitive configuration in `.env` (not committed to repository)
- **Input Validation**: Centralized validators for all user inputs
- **Role-Based Access**: Basic user/admin profile distinction

### Best Practices

- Never commit `.env` to version control
- Rotate secrets regularly
- Keep dependencies updated
- Use environment-specific configurations
- Validate and sanitize all inputs
- Review logs for suspicious activity

---

## 🛠️ Development

### Running Tests

```bash
# Activate virtual environment first
source .venv/bin/activate  # or .venv\Scripts\Activate.ps1 on Windows

# Run all tests
pytest

# Run with verbose output
pytest -v

# Run with coverage report
pytest --cov=.
```

### Database Migrations

```bash
# Initialize or apply pending migrations
python database/init_db.py

# Manually run a specific migration
mysql -u <user> -p <database> < database/migrations/001_usuario_responsavel_opcional.sql
```

### Code Standards

- **Style:** Follows PEP 8
- **Functions:** Keep small, focused, with clear docstrings
- **Variables:** Use meaningful names in English
- **Types:** Use type hints where applicable
- **Comments:** Document non-obvious logic only

### Local Debugging

```bash
# Enable Flask debug mode (hot reload)
export FLASK_DEBUG=1
python web_app/app.py

# On Windows
$env:FLASK_DEBUG=1
python web_app/app.py
```

## 🚢 Deployment

### Production Stack

The application is designed to run with:
- **Application Server:** Gunicorn (with WSGI)
- **Web Server:** Nginx (reverse proxy)
- **Process Manager:** systemd (Linux)
- **Database:** MySQL 8.0+

### Pre-Deployment Checklist

- [ ] All tests passing: `pytest`
- [ ] `.env` configured with production credentials
- [ ] Database migrations applied: `python database/init_db.py`
- [ ] Dependencies installed: `pip install -r requirements.txt`

### Deployment on Linux/Ubuntu

```bash
# 1. Run setup script
chmod +x scripts/setup_server.sh
./scripts/setup_server.sh

# 2. Activate virtual environment
source .venv/bin/activate

# 3. Start with Gunicorn
gunicorn -c gunicorn.conf.py wsgi:app
```

### Local Production Simulation

**Windows:**
```powershell
./scripts/simulate_production.ps1
```

**Linux/macOS:**
```bash
chmod +x scripts/simulate_production.sh
./scripts/simulate_production.sh
```

### Production Configuration Files

Key deployment artifacts:
- [wsgi.py](wsgi.py) — WSGI application entry point
- [gunicorn.conf.py](gunicorn.conf.py) — Gunicorn configuration
- [deploy/nginx/controle_ativos.conf](deploy/nginx/controle_ativos.conf) — Nginx configuration
- [deploy/systemd/controle_ativos.service](deploy/systemd/controle_ativos.service) — systemd service unit

### Environment Variables for Production

Required `.env` variables (must be configured before deployment):
```
DB_HOST=<production-db-host>
DB_PORT=3306
DB_USER=<db-user>
DB_PASSWORD=<strong-password>
DB_NAME=opus_assets
FLASK_SECRET_KEY=<generate-random-string>
APP_PEPPER=<generate-random-string>
FLASK_ENV=production
```

**Never commit `.env` to version control.**

---

## 📌 Contributing

This is a proprietary internal system developed for Opus Medical. 

**For internal team members:**

1. **Create a feature branch:**
   ```bash
   git checkout -b feature/descriptive-name
   # or for fixes
   git checkout -b fix/issue-description
   ```

2. **Make commits with clear messages:**
   ```bash
   git commit -m "feat: add new functionality"
   git commit -m "fix: resolve specific issue"
   git commit -m "docs: update documentation"
   git commit -m "refactor: improve code structure"
   ```

3. **Push and open a Pull Request:**
   ```bash
   git push origin feature/descriptive-name
   ```

4. **Code review** is required before merging to main

**External contributions:** Not accepted. This is internal use only.

---

## 📄 License & Usage

**Status:** Proprietary — All rights reserved

This software is confidential and proprietary to Opus Medical.  
Unauthorized distribution, reproduction, or use is prohibited.

For access or licensing inquiries, contact the development team.

---

## 📞 Internal Resources

- **Documentation:** See [docs/](docs/) folder
- **Internal notes:** See [docs/interno/](docs/interno/) folder (reference only)

---

**Last Updated:** April 2, 2026  
**Maintained By:** Development Team
