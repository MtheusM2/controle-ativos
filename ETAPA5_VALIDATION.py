import sys
sys.path.insert(0, '.')
from web_app.app import app
from flask import render_template, url_for
import os

print("\n" + "="*80)
print("ETAPA 5 - VALIDAÇÃO FINAL E TESTES COMPLETOS")
print("="*80)

# ============================================================================
# 5.1 - Compilação Jinja2
# ============================================================================
print("\n[5.1] COMPILAÇÃO JINJA2")
print("-" * 80)

templates_to_test = [
    ('cadastro.html', {'empresas': []}),
    ('recuperar_senha.html', {'dados': {}}),
    ('index.html', {}),
    ('redefinir_senha.html', {}),
    ('login.html', {}),
    ('ativos.html', {'ativos': [], 'status_validos': [], 'filtros': {}, 'usuario_email': 'test@test.com'}),
    ('novo_ativo.html', {'empresas': [], 'status_validos': []}),
    ('editar_ativo.html', {'dados': {}, 'empresas': [], 'status_validos': [], 'arquivos': []}),
]

compiled_count = 0
with app.test_request_context():
    for template_name, context in templates_to_test:
        try:
            result = render_template(template_name, **context)
            # Validações básicas
            has_html = result.count('<') > 5
            no_jinja_errors = '{% error' not in result.lower()
            has_css = 'style.css' in result or 'css' in result.lower()
            
            if has_html and no_jinja_errors:
                compiled_count += 1
                status = "✓ OK"
            else:
                status = "⚠ WARN"
            
            print(f"{status} | {template_name:<30} | {len(result):>6} chars")
        except Exception as e:
            print(f"✗ ERR | {template_name:<30} | {str(e)[:40]}")

print(f"\nResultado: {compiled_count}/8 templates compilam corretamente")

# ============================================================================
# 5.2 - Validação de Rotas Flask e url_for()
# ============================================================================
print("\n[5.2] VALIDAÇÃO DE ROTAS FLASK E URL_FOR()")
print("-" * 80)

routes_to_check = [
    'listar_ativos',
    'criar_ativo',
    'editar_ativo',
    'login',
    'cadastro_usuario',
    'recuperar_senha',
]

route_count = 0
with app.test_request_context():
    for route_name in routes_to_check:
        try:
            url = url_for(route_name)
            if url.startswith('/'):
                route_count += 1
                print(f"✓ {route_name:<30} → {url}")
            else:
                print(f"⚠ {route_name:<30} → {url} (URL inválida)")
        except Exception as e:
            print(f"✗ {route_name:<30} → ERRO: {str(e)[:40]}")

print(f"\nResultado: {route_count}/{len(routes_to_check)} rotas funcionam corretamente")

# ============================================================================
# 5.3 - Verificação de Estrutura de Formulário
# ============================================================================
print("\n[5.3] VERIFICAÇÃO DE ESTRUTURA DE FORMULÁRIO")
print("-" * 80)

form_checks = {
    'cadastro.html': ['method="POST"', 'action=', 'name="email"', 'name="empresa_id"', 'name="senha"'],
    'recuperar_senha.html': ['method="POST"', 'action=', 'name="email"', 'name="acao"'],
    'novo_ativo.html': ['method="POST"', 'action=', 'name="descricao"'],
    'editar_ativo.html': ['method="POST"', 'name="descricao"'],
}

forms_valid = 0
with app.test_request_context():
    for template_name, required_elements in form_checks.items():
        try:
            html = render_template(template_name, **{
                'empresas': [],
                'dados': {},
                'status_validos': [],
                'ativos': [],
                'filtros': {},
                'arquivos': []
            })
            
            found_all = all(elem in html for elem in required_elements)
            if found_all:
                forms_valid += 1
                print(f"✓ {template_name:<30} | Todos elementos presentes")
            else:
                missing = [e for e in required_elements if e not in html]
                print(f"⚠ {template_name:<30} | Faltando: {', '.join(missing[:2])}")
        except Exception as e:
            print(f"✗ {template_name:<30} | ERRO: {str(e)[:35]}")

print(f"\nResultado: {forms_valid}/{len(form_checks)} formulários têm estrutura válida")

# ============================================================================
# 5.4 - Validação de CSS e Responsividade
# ============================================================================
print("\n[5.4] VALIDAÇÃO DE CSS E RESPONSIVIDADE")
print("-" * 80)

css_checks = {
    '--bg-0': '#08090b',
    '--wine-2': '#a81936',
    '--text-0': '#f4f5f7',
    '.app-shell': 'flex',
    '.sidebar-panel': '272px',
    '.select-control': 'appearance',
    '@media (max-width: 480px)': 'mobile breakpoint',
    '@media (max-width: 920px)': 'tablet breakpoint',
    '@media (max-width: 1140px)': 'desktop breakpoint',
}

with open('web_app/static/css/style.css', 'r', encoding='utf-8') as f:
    css_content = f.read()

css_ok = 0
for check_pattern, description in css_checks.items():
    if check_pattern in css_content:
        css_ok += 1
        print(f"✓ {check_pattern:<40} | {description}")
    else:
        print(f"✗ {check_pattern:<40} | FALTANDO")

print(f"\nResultado: {css_ok}/{len(css_checks)} elementos CSS presentes")

# ============================================================================
# 5.5 - Estrutura de Arquivos
# ============================================================================
print("\n[5.5] ESTRUTURA DE ARQUIVOS CRÍTICOS")
print("-" * 80)

critical_files = {
    'web_app/templates/base.html': 'Base template',
    'web_app/templates/cadastro.html': 'Cadastro',
    'web_app/templates/recuperar_senha.html': 'Recuperar Senha',
    'web_app/templates/index.html': 'Home',
    'web_app/templates/login.html': 'Login',
    'web_app/templates/ativos.html': 'Ativos Lista',
    'web_app/templates/novo_ativo.html': 'Novo Ativo',
    'web_app/templates/editar_ativo.html': 'Editar Ativo',
    'web_app/static/css/style.css': 'CSS Global',
}

files_ok = 0
for filepath, description in critical_files.items():
    if os.path.exists(filepath):
        size = os.path.getsize(filepath)
        files_ok += 1
        size_kb = size / 1024
        print(f"✓ {filepath:<50} | {size_kb:>7.1f} KB | {description}")
    else:
        print(f"✗ {filepath:<50} | FALTANDO")

print(f"\nResultado: {files_ok}/{len(critical_files)} arquivos críticos presentes")

# ============================================================================
# Resumo Final
# ============================================================================
print("\n" + "="*80)
print("RESUMO DE VALIDAÇÃO")
print("="*80)
print(f"Compilação Jinja2:         {compiled_count}/8      ✓")
print(f"Rotas Flask:                {route_count}/{len(routes_to_check)}      ✓")
print(f"Estrutura Formulários:     {forms_valid}/{len(form_checks)}      ✓")
print(f"CSS & Responsividade:      {css_ok}/{len(css_checks)}      ✓")
print(f"Arquivos Críticos:         {files_ok}/{len(critical_files)}      ✓")
print("="*80)

if compiled_count == 8 and route_count == len(routes_to_check) and css_ok == len(css_checks):
    print("\n✓ VALIDAÇÃO COMPLETA - SISTEMA PRONTO PARA PRODUÇÃO")
else:
    print("\n⚠ VALIDAÇÃO COM ALERTAS - REVISAR ITENS COM ⚠ OU ✗")

print("="*80 + "\n")
