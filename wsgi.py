"""
Entry point WSGI para Waitress (produção no Windows Server).

Iniciar manualmente:
    python -m waitress --listen=127.0.0.1:8000 wsgi:application

Em produção, o NSSM executa este entry point automaticamente via
deploy/nssm/install_service.ps1.
"""

from web_app.app import application


app = application