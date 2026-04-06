# Deploy Guide

## Local development

1. Copy `.env.example` to `.env` and fill the secrets.
2. Create the virtualenv and install dependencies.
3. Initialize the database with `python database/init_db.py`.
4. Start the app with `scripts/start_local.ps1` on Windows or `scripts/start_local.sh` on Linux.

## Production on Ubuntu

1. Clone the repository into `/opt/controle_ativos`.
2. Create `.env` from `.env.example` and set production secrets.
3. Run `scripts/setup_server.sh`.
4. Apply the schema and migrations.
5. Install the Nginx config from `deploy/nginx/controle_ativos.conf`.
6. Install the systemd unit from `deploy/systemd/controle_ativos.service`.
7. Enable and start the service.

## WSGI entrypoint

- Gunicorn target: `wsgi:application`
- Compatibility alias: `wsgi:app`
