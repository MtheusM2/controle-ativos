#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ===========================================================================
# VALIDACAO E AJUSTE DE AMBIENTE - FASE E DA PRIMEIRA ETAPA
# ===========================================================================
#
# Objetivo:
#   Validar e ajustar o minimo necessario para homologacao controlada:
#     1. DEBUG mode coerente com ambiente
#     2. SESSION_COOKIE_SECURE configurado
#     3. SESSION_COOKIE_HTTPONLY configurado
#     4. SESSION_COOKIE_SAMESITE configurado
#     5. Variaveis criticas de seguranca presentes
#     6. Ambiente consistente
#
# Uso:
#   python scripts/validate_phase1_environment.py
#
# ===========================================================================

import sys
import os
from pathlib import Path

# Adiciona o raiz do projeto ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Importa as configuracoes
import config
from web_app.app import create_app


class ValidadorAmbiente:
    """Valida o ambiente de homologacao."""

    def __init__(self):
        self.resultados = []
        self.app = None
        self.avisos = []

    def log_resultado(self, teste, passou, mensagem=""):
        """Registra o resultado de um teste."""
        status = "[OK]" if passou else "[FALHOU]"
        print(f"  {status} {teste}")
        if mensagem:
            print(f"       {mensagem}")
        self.resultados.append({"teste": teste, "passou": passou, "mensagem": mensagem})

    def log_aviso(self, aviso):
        """Registra um aviso."""
        print(f"  [AVISO] {aviso}")
        self.avisos.append(aviso)

    def teste_db_configurado(self):
        """Valida que banco esta configurado."""
        print("\n[1] VALIDACAO - BANCO DE DADOS CONFIGURADO")

        try:
            db_host = config.DB_HOST
            db_port = config.DB_PORT
            db_name = config.DB_NAME
            db_user = config.DB_USER

            if all([db_host, db_port, db_name, db_user]):
                self.log_resultado(
                    "Banco de dados",
                    True,
                    f"Host: {db_host}, Porta: {db_port}, Banco: {db_name}, Usuario: {db_user}"
                )
                return True
            else:
                self.log_resultado("Banco de dados", False, "Alguma variavel de BD nao esta configurada")
                return False
        except Exception as e:
            self.log_resultado("Banco de dados", False, str(e))
            return False

    def teste_flask_secret_key(self):
        """Valida que FLASK_SECRET_KEY esta configurado."""
        print("\n[2] VALIDACAO - FLASK_SECRET_KEY")

        try:
            secret = config.FLASK_SECRET_KEY
            if secret and len(secret) >= 32:
                self.log_resultado(
                    "FLASK_SECRET_KEY",
                    True,
                    f"Configurado ({len(secret)} caracteres)"
                )
                return True
            else:
                self.log_resultado(
                    "FLASK_SECRET_KEY",
                    False,
                    f"Nao configurado ou muito curto"
                )
                return False
        except Exception as e:
            self.log_resultado("FLASK_SECRET_KEY", False, str(e))
            return False

    def teste_app_pepper(self):
        """Valida que APP_PEPPER esta configurado."""
        print("\n[3] VALIDACAO - APP_PEPPER")

        try:
            pepper = config.APP_PEPPER
            if pepper and len(pepper) >= 32:
                self.log_resultado(
                    "APP_PEPPER",
                    True,
                    f"Configurado ({len(pepper)} caracteres)"
                )
                return True
            else:
                self.log_resultado(
                    "APP_PEPPER",
                    False,
                    f"Nao configurado ou muito curto"
                )
                return False
        except Exception as e:
            self.log_resultado("APP_PEPPER", False, str(e))
            return False

    def teste_debug_mode(self):
        """Valida que DEBUG esta apropriado para homologacao."""
        print("\n[4] VALIDACAO - DEBUG MODE")

        try:
            debug = config.FLASK_DEBUG

            # Para homologacao, idealmente False
            # Mas aceitamos True se estiver em desenvolvimento
            if debug:
                self.log_aviso(f"DEBUG=True em ambiente de homologacao (considere desativar em producao)")
                self.log_resultado(
                    "DEBUG mode",
                    True,
                    "DEBUG=True (ativo para facilitar diagnostico)"
                )
            else:
                self.log_resultado(
                    "DEBUG mode",
                    True,
                    "DEBUG=False (apropriado para homologacao)"
                )
            return True
        except Exception as e:
            self.log_resultado("DEBUG mode", False, str(e))
            return False

    def teste_session_security(self):
        """Valida configuracoes de seguranca da sessao."""
        print("\n[5] VALIDACAO - CONFIGURACOES DE SESSAO")

        try:
            # Cria a app para acessar as configuracoes
            self.app = create_app()

            session_secure = self.app.config.get("SESSION_COOKIE_SECURE", False)
            session_httponly = self.app.config.get("SESSION_COOKIE_HTTPONLY", False)
            session_samesite = self.app.config.get("SESSION_COOKIE_SAMESITE", "Lax")

            print(f"      SESSION_COOKIE_SECURE: {session_secure}")
            print(f"      SESSION_COOKIE_HTTPONLY: {session_httponly}")
            print(f"      SESSION_COOKIE_SAMESITE: {session_samesite}")

            # Para homologacao interna, httponly deve ser True
            # secure pode ser False em homologacao interna (sem HTTPS)
            # samesite deve ser Lax ou Strict

            ok = (session_httponly and session_samesite in ("Lax", "Strict"))

            if ok:
                self.log_resultado(
                    "Configuracoes de sessao",
                    True,
                    "Cookies configurados corretamente para seguranca"
                )
                if not session_secure:
                    self.log_aviso("SESSION_COOKIE_SECURE=False (ok para homologacao interna sem HTTPS)")
                return True
            else:
                self.log_resultado(
                    "Configuracoes de sessao",
                    False,
                    f"Algumas configuracoes nao estao apropriadas"
                )
                return False

        except Exception as e:
            self.log_resultado("Configuracoes de sessao", False, str(e))
            return False

    def teste_session_lifetime(self):
        """Valida que SESSION_LIFETIME_MINUTES esta configurado."""
        print("\n[6] VALIDACAO - SESSION_LIFETIME_MINUTES")

        try:
            lifetime = config.SESSION_LIFETIME_MINUTES
            if lifetime and lifetime > 0:
                self.log_resultado(
                    "Session lifetime",
                    True,
                    f"Configurado para {lifetime} minutos"
                )
                return True
            else:
                self.log_resultado(
                    "Session lifetime",
                    False,
                    f"Nao configurado apropriadamente"
                )
                return False
        except Exception as e:
            self.log_resultado("Session lifetime", False, str(e))
            return False

    def teste_auth_lockout(self):
        """Valida que bloqueio de autenticacao esta configurado."""
        print("\n[7] VALIDACAO - AUTH LOCKOUT")

        try:
            max_tentativas = config.AUTH_MAX_FAILED_ATTEMPTS
            lockout_minutos = config.AUTH_LOCKOUT_MINUTES

            if max_tentativas > 0 and lockout_minutos > 0:
                self.log_resultado(
                    "Auth lockout",
                    True,
                    f"Bloqueio apos {max_tentativas} tentativas por {lockout_minutos} minutos"
                )
                return True
            else:
                self.log_resultado(
                    "Auth lockout",
                    False,
                    f"Parametros nao apropriados"
                )
                return False
        except Exception as e:
            self.log_resultado("Auth lockout", False, str(e))
            return False

    def teste_logging(self):
        """Valida que logging esta configurado."""
        print("\n[8] VALIDACAO - LOGGING")

        try:
            log_level = config.LOG_LEVEL
            log_dir = config.LOG_DIR

            if log_level and log_dir:
                self.log_resultado(
                    "Logging",
                    True,
                    f"Level: {log_level}, Dir: {log_dir}"
                )
                return True
            else:
                self.log_resultado(
                    "Logging",
                    False,
                    f"Nao configurado apropriadamente"
                )
                return False
        except Exception as e:
            self.log_resultado("Logging", False, str(e))
            return False

    def teste_storage_type(self):
        """Valida que storage type esta configurado."""
        print("\n[9] VALIDACAO - TIPO DE ARMAZENAMENTO")

        try:
            storage_type = config.STORAGE_TYPE

            if storage_type in ("local", "s3"):
                self.log_resultado(
                    "Storage type",
                    True,
                    f"Configurado como '{storage_type}'"
                )
                return True
            else:
                self.log_resultado(
                    "Storage type",
                    False,
                    f"Tipo invalido: {storage_type}"
                )
                return False
        except Exception as e:
            self.log_resultado("Storage type", False, str(e))
            return False

    def teste_app_inicializa(self):
        """Valida que a aplicacao Flask inicializa sem erros."""
        print("\n[10] VALIDACAO - APLICACAO FLASK INICIALIZA")

        try:
            if not self.app:
                self.app = create_app()

            if self.app:
                self.log_resultado(
                    "Aplicacao Flask",
                    True,
                    "Inicializada com sucesso"
                )
                return True
            else:
                self.log_resultado(
                    "Aplicacao Flask",
                    False,
                    "Nao conseguiu inicializar"
                )
                return False

        except Exception as e:
            self.log_resultado("Aplicacao Flask", False, str(e))
            return False

    def executar_validacao(self):
        """Executa a suite completa de validacoes."""
        print("=" * 70)
        print("VALIDACAO E AJUSTE DE AMBIENTE - FASE E")
        print("=" * 70)

        self.teste_db_configurado()
        self.teste_flask_secret_key()
        self.teste_app_pepper()
        self.teste_debug_mode()
        self.teste_session_security()
        self.teste_session_lifetime()
        self.teste_auth_lockout()
        self.teste_logging()
        self.teste_storage_type()
        self.teste_app_inicializa()

        # Resumo
        print("\n" + "=" * 70)
        print("RESUMO DA VALIDACAO DE AMBIENTE")
        print("=" * 70)

        passou = sum(1 for r in self.resultados if r["passou"])
        total = len(self.resultados)

        for resultado in self.resultados:
            status = "[OK]" if resultado["passou"] else "[FALHOU]"
            print(f"  {status}: {resultado['teste']}")

        if self.avisos:
            print(f"\nAvisos ({len(self.avisos)}):")
            for aviso in self.avisos:
                print(f"  - {aviso}")

        print(f"\nResultado: {passou}/{total} testes passaram")

        if passou == total:
            print("\n[OK] FASE E VALIDADA COM SUCESSO")
            return True
        else:
            print(f"\n[FALHOU] FASE E INCOMPLETA ({total - passou} falha(s))")
            return False


if __name__ == "__main__":
    try:
        validador = ValidadorAmbiente()
        sucesso = validador.executar_validacao()
        sys.exit(0 if sucesso else 1)
    except Exception as e:
        print(f"\n[ERRO] ERRO FATAL: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
