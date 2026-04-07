"""
Configuracao do Gunicorn para producao.

Workers recomendados: (2 * num_CPUs) + 1, mínimo de 2.
Ajuste via variavel de ambiente GUNICORN_WORKERS no .env do servidor.
"""

from __future__ import annotations

import multiprocessing
import os

# Endereço e porta onde o Gunicorn escuta (Nginx faz proxy nessa porta).
bind = os.getenv("GUNICORN_BIND", "127.0.0.1:8000")

# Número de processos worker. Padrão seguro: 2*CPU+1, mínimo 2.
_cpu_count = multiprocessing.cpu_count()
workers = int(os.getenv("GUNICORN_WORKERS", str(2 * _cpu_count + 1)))

# Classe de worker síncrona (sync) é estável para Flask sem greenlets.
worker_class = os.getenv("GUNICORN_WORKER_CLASS", "sync")

# Timeout de request em segundos. Aumentar para uploads grandes se necessário.
timeout = int(os.getenv("GUNICORN_TIMEOUT", "60"))

# Keepalive: segundos de conexão aberta entre requests do mesmo cliente.
keepalive = int(os.getenv("GUNICORN_KEEPALIVE", "5"))

# Número máximo de requests por worker antes de reciclar o processo.
# Previne vazamentos de memória em aplicações de longa duração.
max_requests = int(os.getenv("GUNICORN_MAX_REQUESTS", "1000"))
max_requests_jitter = int(os.getenv("GUNICORN_MAX_REQUESTS_JITTER", "100"))

# Envia logs de acesso e erro para stdout/stderr — coletados pelo systemd/journald.
accesslog = "-"
errorlog = "-"
loglevel = os.getenv("LOG_LEVEL", "info").lower()

# Repassa print() da aplicação para o errorlog.
capture_output = True

# Identificação do processo no ps/top para facilitar operações.
proc_name = "controle_ativos"
