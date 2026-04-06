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

- Python 3.8+
- MySQL 8.0+
- pip or poetry

### Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd opus-assets
   ```

2. **Create and activate virtual environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\Activate.ps1
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your database credentials and secret keys
   nano .env
   ```

5. **Initialize database:**
   ```bash
   python database/init_db.py
   ```

6. **Run the application:**
   ```bash
   # Terminal mode
   python main.py
   
   # Or web mode
   python app.py
   # Compatibility entrypoint
   python web_app/app.py
   # Access at http://localhost:5000
   ```

### Environment note

If `.venv` stops working on Windows with an error pointing to `WindowsApps`, recreate it from a valid local Python installation:

```bash
rmdir /s /q .venv
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

- The main presentation flow is now centered on the dashboard page.
- Authentication screens use fetch with JSON responses.
- Asset CRUD is executed from the dashboard using the HTTP endpoints above.
- The attachment service exists in the services layer, but attachment HTTP routes are not wired in the current web flow.

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
pytest
```

### Database Migrations

```bash
# Apply pending migrations
python database/init_db.py

# Or manually run a specific migration
mysql -u <user> -p <database> < database/migrations/001_initial.sql
```

### Code Style

- Follow PEP 8
- Use meaningful variable and function names
- Write docstrings for all functions and classes
- Keep functions small and focused
- Avoid deep nesting

### Debugging

```bash
# Enable Flask debug mode
export FLASK_DEBUG=1
python app.py
```

## 🚢 Deployment

### Local production simulation on Windows

```powershell
scripts\simulate_production.ps1
```

### Local production simulation on Linux

```bash
chmod +x scripts/*.sh
scripts/simulate_production.sh
```

### Production on Ubuntu with Gunicorn

```bash
scripts/setup_server.sh
source .venv/bin/activate
gunicorn -c gunicorn.conf.py wsgi:app
```

### Main production artifacts

- [wsgi.py](wsgi.py)
- [gunicorn.conf.py](gunicorn.conf.py)
- [deploy/nginx/controle_ativos.conf](deploy/nginx/controle_ativos.conf)
- [deploy/systemd/controle_ativos.service](deploy/systemd/controle_ativos.service)
- [.env.example](.env.example)

---

## 📌 Contributing

This is a proprietary internal system. External contributions are not accepted.

For internal team updates:
1. Create a feature branch: `git checkout -b feature/your-feature`
2. Commit with clear messages: `git commit -m "feat: add your feature"`
3. Push and create a pull request
4. Code review required before merge

---

## 📄 License

This software is proprietary and confidential. All rights reserved.


---

**Last Updated:** April 2, 2026  
**Maintained By:** Development Team
