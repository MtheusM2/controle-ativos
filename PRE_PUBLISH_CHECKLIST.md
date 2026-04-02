# ✅ Checklist: Antes de Publicar no GitHub

## 🔒 Segurança

- [ ] **`.env` foi removido do repositório?**
  - Rodar: `git log --name-status --oneline | grep ".env"`
  - Se aparecer, seguir guia de limpeza em CLEANUP_GIT_HISTORY.md
  - [ ] Confirmar que `.env` está em `.gitignore`
  - [ ] Confirmar que `.env.example` está no repositório (sem credenciais)
  - [ ] Confirmar que nenhum arquivo `.env.*` foi commitado

- [ ] **Nenhum arquivo com dados sensíveis no repo**
  - [ ] Sem `BACKUP_*.csv` (dados com informações sensíveis)
  - [ ] Sem arquivos de configuração com senhas
  - [ ] Sem arquivos de teste com dados reais
  - [ ] Sem logs com informações sensíveis

- [ ] **Segredos foram rotacionados**
  - [ ] Nova senha do banco de dados (a antiga foi exposta)
  - [ ] Nova `FLASK_SECRET_KEY`
  - [ ] Novo `APP_PEPPER`

---

## 📦 Conteúdo e Estrutura

- [ ] **Arquivos acadêmicos removidos**
  - [ ] `ETAPA5_*.md` (todos removidos?)
  - [ ] `ETAPA5_*.py` (todos removidos?)
  - [ ] `REFACTORING_*.md` (removidos?)
  - [ ] `STEP_1_BACKUP.py` até `STEP_4_*.py` (removidos?)
  - [ ] `DIAGNOSE_SCHEMA.py` (removido?)
  - [ ] `PRE_DEPLOY_CHECKLIST.md` (removido ou renomeado?)
  - [ ] `MIGRATION_GUIDE.md` (removido ou não é valor acadêmico?)
  - [ ] `"Interface Sistema Controle Ativos/"` (separada para outro repo?)
  - [ ] `BACKUP_ativos_*.csv` (deletado?)

- [ ] **Estrutura de pastas profissional**
  - [ ] Nenhum folder com espaços em nome
  - [ ] Nenhum nome em português misturado com inglês
  - [ ] Pasta `web_app` está consistente (não há `web/` também)

- [ ] **Documentação profissional**
  - [ ] README.md atualizado com novo README profissional
  - [ ] Nenhuma referência a TCC, COBIT, cronograma acadêmico
  - [ ] Seção "Quick Start" com instruções claras
  - [ ] Stack e arquitetura bem explicados
  - [ ] `.env.example` presente (sem credenciais)

---

## 📝 Arquivos Obrigatórios

- [ ] `README.md` — Profissional, sem conteúdo acadêmico
- [ ] `requirements.txt` — Com todas as dependências corretas
- [ ] `.env.example` — Template de configuração
- [ ] `.gitignore` — Proteção de arquivos sensíveis
- [ ] `LICENSE` ou indicar "Proprietary" — Se for código interno

---

## 🏢 Alinhamento Corporativo

- [ ] **Branding e nomenclatura**
  - [ ] Nome do projeto é `Opus Assets` ou consistente em todo lugar
  - [ ] Sem referências a "Controle de Ativos" (nome acadêmico)
  - [ ] Sem referências a "ETEC", "TCC", "2026.1"

- [ ] **Descrição do repositório**
  - [ ] Descrição: "Asset management system for Opus Medical — user authentication, centralized control, operational traceability"
  - [ ] Topics: `asset-management`, `python`, `flask`, `mysql`

- [ ] **Licença apropriada**
  - [ ] README menciona "Proprietary — All rights reserved"
  - [ ] Ou incluir arquivo `LICENSE`

---

## 🚀 Funcionalidade e Quality

- [ ] **Código compila e executa**
  - [ ] `pip install -r requirements.txt` funciona sem erros
  - [ ] `python main.py` inicia sem erros
  - [ ] `python web_app/app.py` inicia aplicação Flask
  - [ ] Banco de dados inicializa: `python database/init_db.py`

- [ ] **Sem arquivos quebrados**
  - [ ] Sem arquivos `.pyc` ou `__pycache__` (devem estar em `.gitignore`)
  - [ ] Sem imports faltando
  - [ ] Sem syntax errors (verificar com `python -m py_compile *.py`)

- [ ] **Repositório está limpo**
  - [ ] Sem arquivos temporários ou de teste
  - [ ] Sem merge conflicts não resolvidos
  - [ ] Sem commits incompletos

---

## 📊 Visibilidade e Profissionalismo

- [ ] **Primeira impressão profissional**
  - [ ] README é a primeira coisa que aparece
  - [ ] Logo/branding da Opus Medical não expõe informações sensíveis
  - [ ] Sem emojis excessivos (máx 3-4 bem colocados)
  - [ ] Sem linguagem informal ou acadêmica

- [ ] **Documentação técnica clara**
  - [ ] Instruções de instalação testadas e funcionando
  - [ ] Exemplos de uso são realistas
  - [ ] Arquitetura é explicada de forma profissional
  - [ ] Sem "trabalho em progresso" ou "TODO"

---

## 🔄 Antes de fazer Push Final

```bash
# 1. Revisar status dos arquivos
git status

# 2. Revisar commits
git log --oneline -10

# 3. Procurar por credenciais no histórico
git log -p | grep -i "password\|secret\|key"

# 4. Confirmar que .env não está no repo
git ls-files | grep ".env"  # Deve retornar apenas ".env.example"

# 5. Testar que está tudo funcionando
python -m pip install -r requirements.txt
python main.py

# 6. Fazer push
git push origin main
```

---

## ⚠️ Se Encontrar Problemas

### Credenciais expostas no histórico?
→ Ver `CLEANUP_GIT_HISTORY.md`

### Arquivos acadêmicos ainda no repo?
→ Remover com: `git rm --cached <arquivo>` + `git commit -m "cleanup: remove academic artifacts"`

### `.env` ainda commitado?
→ Remover e também limpar do histórico (crítico!)

### requirements.txt vazio ou incompleto?
→ Gerar com: `pip freeze > requirements.txt`

---

## ✅ Aprovação Final

- [ ] CTO/Tech Lead revisou e aprovou
- [ ] Nenhuma informação sensível exposta
- [ ] README está profissional e completo
- [ ] Código está funcionando
- [ ] Repositório está limpo

**Aprovado por:** ________________  
**Data:** ________________

---

**Checklist versão:** 1.0  
**Última atualização:** April 2, 2026
