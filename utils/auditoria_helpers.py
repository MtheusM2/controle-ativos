"""
Helpers para integração de auditoria com Flask.

Funções para extrair contexto de requisição (IP, User-Agent)
e registrar eventos de forma consistente.
"""

from __future__ import annotations

from flask import request
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flask import Request


def obter_ip_cliente(req: Request | None = None) -> str:
    """
    Obtém o IP do cliente a partir da requisição Flask.

    Considera headers de proxy (X-Forwarded-For, X-Real-IP) para ambientes
    com reverse proxy (como IIS em produção).

    Args:
        req: Objeto Request do Flask (se None, usa request global)

    Returns:
        Endereço IP em formato string (IPv4 ou IPv6)
    """
    if req is None:
        req = request

    # Verifica X-Forwarded-For (lista de IPs em proxies)
    if req.headers.get("X-Forwarded-For"):
        # Pega o primeiro IP (cliente original)
        return req.headers["X-Forwarded-For"].split(",")[0].strip()

    # Verifica X-Real-IP (Nginx, etc)
    if req.headers.get("X-Real-IP"):
        return req.headers["X-Real-IP"].strip()

    # Fallback para remote_addr (conexão direta)
    return req.remote_addr or "unknown"


def obter_user_agent(req: Request | None = None) -> str:
    """
    Obtém o User-Agent do cliente a partir da requisição Flask.

    Args:
        req: Objeto Request do Flask (se None, usa request global)

    Returns:
        String User-Agent (truncada em 255 caracteres)
    """
    if req is None:
        req = request

    user_agent = req.headers.get("User-Agent", "unknown")

    # Trunca para caber na coluna do banco (VARCHAR(255))
    return user_agent[:255] if user_agent else "unknown"


def obter_contexto_requisicao() -> dict:
    """
    Extrai contexto completo da requisição para auditoria.

    Returns:
        Dicionário com:
        - ip_origem: IP do cliente
        - user_agent: navegador/client
        - metodo: GET, POST, etc
        - rota: path acessado
        - parametros: query string (sanitizada)
    """
    return {
        "ip_origem": obter_ip_cliente(),
        "user_agent": obter_user_agent(),
        "metodo": request.method,
        "rota": request.path,
        "parametros": dict(request.args),
    }


def descrever_evento_humano(tipo_evento: str, dados: dict) -> str:
    """
    Gera descrição legível de um evento para auditoria.

    Args:
        tipo_evento: tipo de evento (ex: ATIVO_CRIADO)
        dados: dicionário com contexto do evento

    Returns:
        String descritiva (ex: "Ativo OPU-001 (Notebook) criado")
    """
    descricoes = {
        "ATIVO_CRIADO": lambda d: f"Ativo {d.get('id')} ({d.get('tipo')}) criado",
        "ATIVO_EDITADO": lambda d: f"Ativo {d.get('id')} — campo '{d.get('campo')}' alterado",
        "ATIVO_REMOVIDO": lambda d: f"Ativo {d.get('id')} removido",
        "ATIVO_INATIVADO": lambda d: f"Ativo {d.get('id')} inativado",
        "ARQUIVO_ENVIADO": lambda d: f"Arquivo {d.get('nome')} anexado a {d.get('ativo_id')}",
        "ARQUIVO_REMOVIDO": lambda d: f"Arquivo removido de {d.get('ativo_id')}",
        "LOGIN_SUCESSO": lambda d: f"Login bem-sucedido: {d.get('email')}",
        "LOGIN_FALHA": lambda d: f"Falha de login: {d.get('email')} - {d.get('razao')}",
        "ACESSO_NEGADO": lambda d: f"Acesso negado: {d.get('razao')}",
        "USUARIO_PROMOVIDO": lambda d: f"Usuário promovido a {d.get('novo_perfil')}",
    }

    gerador = descricoes.get(tipo_evento)
    if gerador:
        try:
            return gerador(dados or {})
        except (KeyError, TypeError, AttributeError):
            pass

    # Fallback se não conseguir gerar
    return tipo_evento
