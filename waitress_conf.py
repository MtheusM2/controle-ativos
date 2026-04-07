"""
Configuracao do Waitress para producao no Windows Server.

O Waitress e um servidor WSGI puro-Python, nativo no Windows.
As variaveis abaixo sao usadas pelo script de inicializacao
(deploy/nssm/install_service.ps1 e scripts/setup_server.ps1).

Para iniciar manualmente:
    python -m waitress --listen=127.0.0.1:8000 --threads=4 wsgi:application
"""

from __future__ import annotations

import multiprocessing
import os

# Endereco e porta onde o Waitress escuta.
# O IIS faz proxy reverso para esta porta.
HOST = os.getenv("WAITRESS_HOST", "127.0.0.1")
PORT = int(os.getenv("WAITRESS_PORT", "8000"))
BIND = f"{HOST}:{PORT}"

# Numero de threads para processar requests concorrentes.
# Waitress e thread-based (nao process-based como Gunicorn).
# Recomendado: 2 a 4x o numero de CPUs logicos.
_cpu_count = multiprocessing.cpu_count()
THREADS = int(os.getenv("WAITRESS_THREADS", str(min(_cpu_count * 4, 16))))

# Tamanho maximo de request (bytes). Alinhado com o limite do Flask e do IIS.
MAX_REQUEST_BODY_SIZE = int(os.getenv("WAITRESS_MAX_REQUEST_BODY_SIZE", str(10 * 1024 * 1024)))

# Timeout de conexao em segundos.
CONNECTION_LIMIT = int(os.getenv("WAITRESS_CONNECTION_LIMIT", "1000"))

# Identificacao nos logs.
IDENT = "controle-ativos"
