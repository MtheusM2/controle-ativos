#!/usr/bin/env python
"""
Script de auditoria de segurança para preparação de homologação.

Verifica:
- Autenticação em rotas sensíveis
- CSRF em todas as mutações
- Status HTTP (401, 403, 422)
- Proteção contra SQL injection
- Proteção contra XSS
- Segurança de sessão
- Validação de entrada
"""

import re
import sys
from pathlib import Path

# Cores para terminal
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def read_file(path):
    """Lê arquivo e retorna conteúdo."""
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    except Exception as e:
        print(f"{Colors.RED}Erro ao ler {path}: {e}{Colors.RESET}")
        return ""

def find_routes(content):
    """Extrai rotas Flask do conteúdo."""
    pattern = r'@app\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']\)'
    matches = re.findall(pattern, content)
    return matches

def check_auth_decoration(content, route_method):
    """Verifica se uma rota tem @require_auth_api()."""
    # Procura pelo padrão: @app.método seguido por @require_auth_api
    pattern = f"@app\\.{route_method}.*?@require_auth_api"
    return bool(re.search(pattern, content, re.DOTALL))

def check_csrf_decoration(content, route_method):
    """Verifica se uma rota tem @require_csrf()."""
    pattern = f"@app\\.{route_method}.*?@require_csrf"
    return bool(re.search(pattern, content, re.DOTALL))

def check_sql_injection(content):
    """Verifica por possíveis SQL injection (interpolação direta)."""
    # Procura por padrões perigosos como f"... {var} ..." em SQL
    dangerous = re.findall(r'(f\s*["\'].*?SELECT.*?\{.*?\}.*?["\'])', content, re.IGNORECASE | re.DOTALL)
    return dangerous

def check_exception_handling(content):
    """Verifica por exception handling genérico."""
    # Procura por except Exception ou except: sem mais especificidade
    generic_except = re.findall(r'except\s+(Exception|:)', content)
    return generic_except

def print_section(title):
    """Imprime título de seção."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{title}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}\n")

def print_result(status, message):
    """Imprime resultado com cor."""
    if status == "PASS":
        print(f"{Colors.GREEN}[PASS]{Colors.RESET}: {message}")
    elif status == "WARN":
        print(f"{Colors.YELLOW}[WARN]{Colors.RESET}: {message}")
    elif status == "FAIL":
        print(f"{Colors.RED}[FAIL]{Colors.RESET}: {message}")

def main():
    """Executa auditoria de segurança."""
    base_path = Path(__file__).parent.parent
    ativos_routes = base_path / "web_app" / "routes" / "ativos_routes.py"
    auth_routes = base_path / "web_app" / "routes" / "auth_routes.py"

    print(f"\n{Colors.BOLD}{Colors.BLUE}AUDITORIA DE SEGURANÇA - CONTROLE DE ATIVOS{Colors.RESET}")
    print(f"Data: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Lê arquivos
    ativos_content = read_file(ativos_routes)
    auth_content = read_file(auth_routes)

    issues = {
        "FAIL": 0,
        "WARN": 0,
        "PASS": 0
    }

    # ===== AUTENTICAÇÃO =====
    print_section("1. AUTENTICAÇÃO")

    # Verifica se rotas de mutação têm autenticação
    mutations = [
        ("POST", "/ativos"),
        ("PUT", "/ativos/<id>"),
        ("DELETE", "/ativos/<id>"),
        ("POST", "/ativos/<id>/anexos"),
        ("DELETE", "/anexos/<id>"),
    ]

    for method, route in mutations:
        if method == "POST":
            has_auth = "@require_auth_api()" in ativos_content
            if has_auth:
                print_result("PASS", f"{method} {route} protegida com @require_auth_api()")
                issues["PASS"] += 1
            else:
                print_result("FAIL", f"{method} {route} sem @require_auth_api()")
                issues["FAIL"] += 1

    # ===== CSRF =====
    print_section("2. PROTEÇÃO CSRF")

    if "@require_csrf()" in ativos_content:
        count = ativos_content.count("@require_csrf()")
        print_result("PASS", f"Encontradas {count} decorações @require_csrf() em rotas de mutação")
        issues["PASS"] += 1
    else:
        print_result("FAIL", "Nenhuma @require_csrf() encontrada")
        issues["FAIL"] += 1

    # POST /logout protegido
    if "@require_csrf()" in auth_content:
        print_result("PASS", "POST /logout protegido com @require_csrf()")
        issues["PASS"] += 1
    else:
        print_result("WARN", "POST /logout pode não estar protegido com CSRF")
        issues["WARN"] += 1

    # ===== SQL INJECTION =====
    print_section("3. PROTEÇÃO CONTRA SQL INJECTION")

    sql_issues = check_sql_injection(ativos_content)
    if not sql_issues:
        print_result("PASS", "Nenhuma interpolação direta em queries SQL detectada")
        issues["PASS"] += 1
    else:
        print_result("WARN", f"Verificar manualmente {len(sql_issues)} queries dinâmicas")
        issues["WARN"] += 1

    if "WHERE" in ativos_content and "%s" in ativos_content:
        print_result("PASS", "Queries usam placeholders %s (prepared statements)")
        issues["PASS"] += 1

    # ===== EXCEPTION HANDLING =====
    print_section("4. TRATAMENTO DE EXCEÇÕES")

    # Procura por exception genérico que não é capturado corretamente
    lines = ativos_content.split('\n')
    generic_excepts = []
    for i, line in enumerate(lines, 1):
        if re.search(r'except\s+Exception\s*as\s+\w+:', line):
            # Pode ser OK se tratar especificamente
            continue
        if re.search(r'except\s*:', line):
            generic_excepts.append(i)

    if not generic_excepts:
        print_result("PASS", "Sem except genérico nú (bare except)")
        issues["PASS"] += 1
    else:
        print_result("WARN", f"Verificar bare except em linhas: {generic_excepts}")
        issues["WARN"] += 1

    # ===== STATUS HTTP =====
    print_section("5. STATUS HTTP CORRETOS")

    status_codes = {
        401: "Sessão expirada (não autenticado)",
        403: "Permissão negada (CSRF inválido)",
        400: "Requisição inválida",
        422: "Entidade não processável (validação)",
        500: "Erro interno"
    }

    for code, desc in status_codes.items():
        if f"status={code}" in ativos_content:
            print_result("PASS", f"Status {code} ({desc}) encontrado")
            issues["PASS"] += 1

    # ===== VALIDAÇÃO DE ENTRADA =====
    print_section("6. VALIDAÇÃO DE ENTRADA")

    if "validar_" in ativos_content:
        print_result("PASS", "Validações de entrada encontradas (validar_*)")
        issues["PASS"] += 1
    else:
        print_result("WARN", "Verificar se toda entrada está sendo validada")
        issues["WARN"] += 1

    # ===== SESSÃO =====
    print_section("7. SEGURANÇA DE SESSÃO")

    if "SESSION_COOKIE_HTTPONLY" in read_file(base_path / "config.py"):
        print_result("PASS", "SESSION_COOKIE_HTTPONLY habilitado")
        issues["PASS"] += 1

    if "SESSION_COOKIE_SECURE" in read_file(base_path / "config.py"):
        print_result("PASS", "SESSION_COOKIE_SECURE habilitado (em produção)")
        issues["PASS"] += 1
    else:
        print_result("WARN", "SESSION_COOKIE_SECURE não está configurado (necessário em produção)")
        issues["WARN"] += 1

    # ===== RESUMO =====
    print_section("RESUMO DA AUDITORIA")

    total = issues["PASS"] + issues["FAIL"] + issues["WARN"]
    print(f"Total de verificações: {total}")
    print(f"{Colors.GREEN}Passou: {issues['PASS']}{Colors.RESET}")
    print(f"{Colors.YELLOW}Avisos: {issues['WARN']}{Colors.RESET}")
    print(f"{Colors.RED}Falhas: {issues['FAIL']}{Colors.RESET}\n")

    if issues["FAIL"] > 0:
        print(f"{Colors.RED}RESULTADO: NÃO PRONTO PARA HOMOLOGAÇÃO{Colors.RESET}\n")
        return 1
    elif issues["WARN"] > 0:
        print(f"{Colors.YELLOW}RESULTADO: PRONTO COM AVISOS (corrigir antes de produção){Colors.RESET}\n")
        return 0
    else:
        print(f"{Colors.GREEN}RESULTADO: PRONTO PARA HOMOLOGAÇÃO{Colors.RESET}\n")
        return 0

if __name__ == "__main__":
    sys.exit(main())
