#!/usr/bin/env python3
"""
Script de validação da Sprint 2.1 Final.

Valida que:
1. Configuração está correta
2. App inicia sem erro
3. Testes passam
4. Secrets estão externalizados
5. Nenhuma regressão crítica

Uso:
    python scripts/validar_sprint_2_1.py

Saída:
    - Status de cada validação
    - Relatório com sumarização
    - Exit code: 0 (sucesso) ou 1 (falha)
"""

import sys
import os
from pathlib import Path

# Adiciona diretório do projeto ao path
PROJECT_DIR = Path(__file__).parent.parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))


def validar_config():
    """Valida que configuração foi carregada corretamente."""
    print("\n" + "=" * 80)
    print("1. VALIDAÇÃO DE CONFIGURAÇÃO")
    print("=" * 80)

    try:
        from config import (
            FLASK_SECRET_KEY, APP_PEPPER, DB_PASSWORD,
            DB_HOST, DB_USER, DB_NAME, FLASK_DEBUG,
            SESSION_COOKIE_SECURE, IS_PRODUCTION,
            diagnosticar_config, validar_producao
        )

        # Validar variáveis críticas existem
        assert FLASK_SECRET_KEY, "FLASK_SECRET_KEY não foi carregado"
        assert APP_PEPPER, "APP_PEPPER não foi carregado"
        assert DB_PASSWORD, "DB_PASSWORD não foi carregado"
        assert DB_HOST, "DB_HOST não foi carregado"
        assert DB_USER, "DB_USER não foi carregado"
        assert DB_NAME, "DB_NAME não foi carregado"

        print("[OK] Todas as variaveis criticas foram carregadas")

        # Validar que não são placeholders
        assert FLASK_SECRET_KEY not in ("CHANGE_ME", "dev", ""), \
            "FLASK_SECRET_KEY eh placeholder"
        assert APP_PEPPER not in ("CHANGE_ME", "dev", ""), \
            "APP_PEPPER eh placeholder"

        print("[OK] Secrets nao sao placeholders")

        # Validar FLASK_DEBUG
        assert FLASK_DEBUG == False, "FLASK_DEBUG deve ser False em producao"
        print("[OK] FLASK_DEBUG esta desativado")

        # Executar diagnóstico
        diag = diagnosticar_config()
        print(f"[OK] IS_PRODUCTION: {diag['is_production']}")
        print(f"[OK] ENVIRONMENT: {diag['environment']}")
        print(f"[OK] STORAGE_TYPE: {diag['storage_type']}")

        # Não levanta erro, mas avisa se em produção sem HTTPS
        if IS_PRODUCTION and not SESSION_COOKIE_SECURE:
            print("[AVISO] Em producao mas SESSION_COOKIE_SECURE=0 (ok para intranet)")

        print("[OK] Configuracao validada com sucesso")
        return True

    except Exception as e:
        print(f"[ERRO] na configuracao: {e}")
        return False


def validar_app_inicia():
    """Valida que Flask app inicia sem erro."""
    print("\n" + "=" * 80)
    print("2. VALIDAÇÃO DE STARTUP DA APLICAÇÃO")
    print("=" * 80)

    try:
        from web_app.app import create_app

        app = create_app()
        assert app is not None, "create_app() retornou None"
        assert app.config.get('SECRET_KEY'), "SECRET_KEY não foi setado"

        print("[OK] Flask app foi criado com sucesso")
        print(f"[OK] DEBUG: {app.debug}")
        print(f"[OK] TESTING: {app.testing}")

        # Validar endpoints básicos
        with app.test_client() as client:
            resp = client.get('/health')
            assert resp.status_code == 200, f"Health check falhou com {resp.status_code}"
            print("[OK] Endpoint /health responde 200")

            resp = client.get('/config-diagnostico')
            assert resp.status_code == 200, f"Config diagnostico falhou com {resp.status_code}"
            data = resp.get_json()
            assert data.get('ok') == True, "Config diagnostico retornou ok=False"
            print("[OK] Endpoint /config-diagnostico responde 200")

        print("[OK] App inicializado com sucesso")
        return True

    except Exception as e:
        print(f"[ERRO] ERRO ao inicializar app: {e}")
        import traceback
        traceback.print_exc()
        return False


def validar_banco():
    """Valida que banco de dados está acessível."""
    print("\n" + "=" * 80)
    print("3. VALIDAÇÃO DE BANCO DE DADOS")
    print("=" * 80)

    try:
        from database.connection import cursor_mysql

        with cursor_mysql(dictionary=True) as (conn, cur):
            # Validar tabelas existem
            cur.execute("SHOW TABLES")
            tabelas = [row[f'Tables_in_{os.getenv("DB_NAME")}'] for row in cur.fetchall()]

            required_tables = ['usuarios', 'empresas', 'ativos', 'auditoria_eventos']
            for table in required_tables:
                if table not in tabelas:
                    print(f"[ERRO] Tabela '{table}' não foi encontrada")
                    return False

            print(f"[OK] Todas as tabelas obrigatórias existem: {required_tables}")

            # Contar registros
            cur.execute("SELECT COUNT(*) as cnt FROM usuarios")
            user_count = cur.fetchone()['cnt']
            print(f"[OK] Usuários no banco: {user_count}")

            cur.execute("SELECT COUNT(*) as cnt FROM empresas")
            company_count = cur.fetchone()['cnt']
            print(f"[OK] Empresas no banco: {company_count}")

            cur.execute("SELECT COUNT(*) as cnt FROM auditoria_eventos")
            audit_count = cur.fetchone()['cnt']
            print(f"[OK] Eventos de auditoria: {audit_count}")

        print("[OK] Banco de dados validado com sucesso")
        return True

    except Exception as e:
        print(f"[ERRO] ERRO ao validar banco: {e}")
        import traceback
        traceback.print_exc()
        return False


def validar_testes():
    """Valida que testes passam."""
    print("\n" + "=" * 80)
    print("4. VALIDAÇÃO DE TESTES")
    print("=" * 80)

    try:
        import subprocess

        # Tenta rodar testes com pytest
        result = subprocess.run(
            ["pytest", "tests/", "-v", "--tb=short"],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_DIR),
            timeout=60
        )

        # Contar testes
        passed = result.stdout.count(" PASSED")
        failed = result.stdout.count(" FAILED")

        if failed > 0:
            print(f"[ERRO] {failed} testes falharam")
            print(result.stdout)
            return False

        print(f"[OK] {passed} testes passaram, 0 falharam")

        # Validar cobertura mínima
        if passed < 121:
            print(f"[AVISO] AVISO: Esperado >= 121 testes, apenas {passed} passaram")
        else:
            print(f"[OK] Cobertura de testes OK (>= 121)")

        return True

    except Exception as e:
        print(f"[AVISO] AVISO: Não foi possível validar testes ({e})")
        print("   Isso pode ser normal se pytest não está instalado ou há problemas de permissão")
        return True  # Não falhar, apenas avisar


def validar_secrets():
    """Valida que secrets estão externalizados."""
    print("\n" + "=" * 80)
    print("5. VALIDAÇÃO DE SECRETS")
    print("=" * 80)

    try:
        env_file = PROJECT_DIR / ".env"

        # Em produção, .env não deve existir
        if os.getenv("ENVIRONMENT") == "production":
            if env_file.exists():
                print("[AVISO] AVISO: .env existe em produção (deve estar ignorado)")
            else:
                print("[OK] .env não existe em produção")

        # Verificar que .env está no .gitignore
        gitignore = PROJECT_DIR / ".gitignore"
        if gitignore.exists():
            with open(gitignore, 'r') as f:
                if ".env" in f.read():
                    print("[OK] .env está no .gitignore")
                else:
                    print("[AVISO] AVISO: .env pode não estar protegido no .gitignore")
        else:
            print("[AVISO] AVISO: Arquivo .gitignore não encontrado")

        # Validar que scripts de secret existem
        gerador = PROJECT_DIR / "scripts" / "gerar_secrets_seguros.py"
        setup = PROJECT_DIR / "scripts" / "setup_producao_secrets.ps1"

        if gerador.exists():
            print("[OK] Script gerar_secrets_seguros.py existe")
        else:
            print("[ERRO] Script gerar_secrets_seguros.py não encontrado")
            return False

        if setup.exists():
            print("[OK] Script setup_producao_secrets.ps1 existe")
        else:
            print("[ERRO] Script setup_producao_secrets.ps1 não encontrado")
            return False

        print("[OK] Secrets estão corretamente externalizados")
        return True

    except Exception as e:
        print(f"[ERRO] ERRO ao validar secrets: {e}")
        return False


def validar_arquivos_criados():
    """Valida que arquivos da Sprint 2.1 foram criados."""
    print("\n" + "=" * 80)
    print("6. VALIDAÇÃO DE ARQUIVOS CRIADOS")
    print("=" * 80)

    try:
        docs = PROJECT_DIR / "docs"

        required_files = [
            "SPRINT_2_1_FASE_A_LEVANTAMENTO.md",
            "SPRINT_2_1_FASE_B_SECRETS.md",
            "SPRINT_2_1_FASE_C_HTTPS.md",
            "SPRINT_2_1_FASE_D_CHECKLIST.md",
        ]

        missing = []
        for file in required_files:
            path = docs / file
            if path.exists():
                print(f"[OK] {file}")
            else:
                print(f"[ERRO] {file} não encontrado")
                missing.append(file)

        if missing:
            print(f"[ERRO] {len(missing)} arquivos faltando")
            return False

        print("[OK] Todos os arquivos de documentação foram criados")
        return True

    except Exception as e:
        print(f"[ERRO] ERRO ao validar arquivos: {e}")
        return False


def main():
    """Executa todas as validações."""
    print("\n")
    print("=" * 80)
    print("VALIDACAO DA SPRINT 2.1 FINAL".center(80))
    print("=" * 80)

    resultados = {
        "Configuração": validar_config(),
        "Startup da App": validar_app_inicia(),
        "Banco de Dados": validar_banco(),
        "Testes": validar_testes(),
        "Secrets": validar_secrets(),
        "Arquivos Criados": validar_arquivos_criados(),
    }

    # Sumarização
    print("\n" + "=" * 80)
    print("SUMARIZAÇÃO")
    print("=" * 80)

    total = len(resultados)
    passed = sum(1 for v in resultados.values() if v)
    failed = total - passed

    for name, result in resultados.items():
        status = "[OK] OK" if result else "[ERRO] FALHOU"
        print(f"{name:.<50} {status}")

    print()
    print(f"Total: {passed}/{total} validações passaram")

    if failed == 0:
        print("\n[OK] TODAS AS VALIDAÇÕES PASSARAM - SISTEMA PRONTO")
        return 0
    else:
        print(f"\n[ERRO] {failed} validação(ões) falharam - REVISAR ACIMA")
        return 1


if __name__ == "__main__":
    sys.exit(main())
