# 🧹 Guia de Limpeza: Remover Arquivos do Histórico Git

## ⚠️ CRÍTICO: `.env` Foi Commitado com Credenciais

O arquivo `.env` contém:
- `DB_PASSWORD=<EXPOSTA_ANTERIORMENTE>` ← EXPOSTO
- `FLASK_SECRET_KEY=<EXPOSTA_ANTERIORMENTE>` ← EXPOSTO
- `APP_PEPPER=<EXPOSTO_ANTERIORMENTE>` ← EXPOSTO

**Qualquer pessoa com acesso ao repositório tem acessado à senha do banco de dados.**

---

## 🔴 EM PRIMEIRO LUGAR: ROTACIONAR CREDENCIAIS

Antes de fazer qualquer limpeza git, **você PRECISA trocar**:

1. **Senha do banco MySQL** — Nova senha aleatória
2. **Regenerar `FLASK_SECRET_KEY`** — Valor novo aleatório
3. **Regenerar `APP_PEPPER`** — Valor novo aleatório
4. **Revogar acesso de usuários não autorizados** — Se disponível

**Fazer isso ANTES de proceder com a limpeza git.**

---

## 🧹 PASSO 1: Remover `.env` do Histórico Git

### Opção A: Usar `git filter-branch` (simples, mas reescreve todo o histórico)

**⚠️ AVISO:** Isso reescreve o histórico. Se outros estão usando o repo, eles precisarão fazer rebase.

```bash
# Remover .env de TODOS os commits
git filter-branch --tree-filter 'rm -f .env' --prune-empty HEAD

# Forçar push (cuidado! Reescreve histórico público)
git push origin --force-with-lease
```

### Opção B: Usar `git-filter-repo` (mais moderno e seguro)

```bash
# Instalar (se não tiver)
pip install git-filter-repo

# Remover .env do histórico
git filter-repo --path .env --invert-paths

# Forçar push
git push origin --force-with-lease
```

### Opção C: Se o repo é novo/pequeno — Fazer reset e reescrever

```bash
# Backup do branch atual (por segurança)
git branch backup_before_cleanup

# Remover .env do filesystem e staging
rm .env
git rm --cached .env

# Listar todos os commits com .env
git log --name-status --oneline | grep -B1 ".env"

# Se houver poucos commits, fazer reset
git reset HEAD~<N>  # N = número de commits

# Recriar commits sem .env
git add .  # Adicionar arquivos corretos
git commit -m "security: remove .env from repository"

# Forçar push
git push origin main --force-with-lease
```

---

## 🧹 PASSO 2: Remover Arquivos Acadêmicos

### Arquivos a Remover

```bash
# Criar lista de arquivos acadêmicos
git rm --cached ETAPA5_*.md ETAPA5_*.py
git rm --cached REFACTORING_*.md REFACTORING_SUMMARY.md
git rm --cached STEP_1_BACKUP.py STEP_2_MIGRATION.py STEP_3_VALIDATE.py STEP_4_FUNCTIONAL_TEST.py
git rm --cached DIAGNOSE_SCHEMA.py
git rm --cached MIGRATION_GUIDE.md
git rm --cached PRE_DEPLOY_CHECKLIST.md
git rm --cached BACKUP_ativos_*.csv
git rm --cached -r "Interface Sistema Controle Ativos/"

# Fazer commit
git commit -m "cleanup: remove TCC/academic artifacts and internal migration scripts"

# Usar filter-repo para limpar do histórico (se necessário)
git filter-repo --path ETAPA5_RELATORIO_FINAL.md --invert-paths
git filter-repo --path ETAPA5_VALIDATION.py --invert-paths
# ... repita para cada arquivo

# Forçar push
git push origin main --force-with-lease
```

---

## 🧹 PASSO 3: Garantir `.gitignore` está Correto

### Verificar `.gitignore`

```bash
# Ver conteúdo
cat .gitignore

# Deve conter:
# .env
# .env.*
# *.csv (ou apenas backups)
# __pycache__/
# .venv/
```

### Se `.gitignore` não tem `.env`:

```bash
# Adicionar
echo ".env" >> .gitignore
echo ".env.*" >> .gitignore

# Commit
git add .gitignore
git commit -m "chore: add .env to gitignore"
git push
```

---

## ✅ PASSO 4: Validação — Confirmar que Tudo Está Limpo

```bash
# 1. Procurar por credenciais no histórico
git log -p | grep -i "password\|secret\|key\|db_password"

# Deve retornar NADA (ou apenas em logs de antes da limpeza)

# 2. Listar arquivos no repositório
git ls-files | grep ".env"

# Deve retornar APENAS ".env.example" (se houver)

# 3. Listar arquivos acadêmicos
git ls-files | grep "ETAPA\|REFACTORING\|STEP_"

# Deve retornar NADA

# 4. Procurar por BACKUP_*.csv
git ls-files | grep "BACKUP_"

# Deve retornar NADA

# 5. Procurar por "Interface Sistema"
git ls-files | grep "Interface"

# Deve retornar NADA
```

---

## 📐 Estrutura Final Esperada

```
opus-assets/
├── README.md                (NOVO PROFISSIONAL)
├── requirements.txt         (NOVO - COM DEPENDÊNCIAS)
├── .env.example             (NOVO - SEM CREDENCIAIS)
├── .gitignore
│
├── database/
│   ├── connection.py
│   ├── init_db.py
│   └── schema.sql
│
├── models/
│   ├── usuario.py
│   └── ativos.py
│
├── services/
│   ├── auth_service.py
│   ├── ativos_service.py
│   └── sistema_ativos.py
│
├── utils/
│   ├── crypto.py
│   └── validators.py
│
├── web_app/
│   ├── app.py
│   ├── routes/
│   │   ├── auth_routes.py
│   │   └── ativos_routes.py
│   ├── templates/
│   └── static/
│
├── main.py
└── PRE_PUBLISH_CHECKLIST.md
```

**NÃO DEVEM ESTAR:**
- `.env` (commitado)
- `ETAPA5_*`, `REFACTORING_*`, `STEP_*`
- `BACKUP_*.csv`
- `Interface Sistema Controle Ativos/`
- Arquivos com credenciais expostas no histórico

---

## 🔍 Se Houver Problema

### "Não consigo remover pelo git, quer dizer que ficou para sempre?"

Não! Alternativas:

1. **Criar novo repositório limpo** (mais seguro para código corporativo)
   ```bash
   # Clonar sem histórico
   git clone --depth 1 <repo-url> nova-copia
   cd nova-copia
   git remote set-url origin <new-repo-url>
   git push -u origin main
   ```

2. **Usar GitHub's "Remove sensitive data" tool** (se em GitHub)
   - Settings → Security & Analysis → Secret Scanning

3. **Contatar suporte** se houver risco maior de exposição

---

## ⚡ Sequência Rápida (Copy-Paste)

Se quer fazer tudo de uma vez (depois de rotacionar credenciais):

```bash
# 1. Backup
git branch backup_before_cleanup

# 2. Remover .env
git rm --cached .env
git filter-repo --path .env --invert-paths

# 3. Remover acadêmicos
git rm --cached ETAPA5_*.md ETAPA5_*.py REFACTORING_*.md
git filter-repo --path ETAPA5_RELATORIO_FINAL.md --invert-paths

# 4. Remover CSVs
git rm --cached BACKUP_*.csv
git commit -m "cleanup: remove backup files"

# 5. Verificar
git log -p | grep "password" && echo "⚠️ Credenciais ainda expostas!" || echo "✅ Limpo!"

# 6. Push
git push origin main --force-with-lease

# 7. Limpar repositório local
git reflog expire --all --expire=now
git gc --prune=now
```

---

## 📞 Suporte

Se algo der errado:

1. Você tem um `backup_before_cleanup` branch
2. Contate o time de DevOps/Git Admin
3. Considere fazer novo clone limpo de um servidor seguro

---

**⚠️ IMPORTANTE:**  
Depois de fazer `--force-with-lease`, notifique a equipe para fazer rebase em branches locais.

**Procedimento de notificação:**
```
Subject: Repository History Rewritten - Please Rebase
Body:
The repository history has been rewritten to remove sensitive data.
All team members must:
1. git fetch origin
2. git rebase origin/main
Or create fresh clones.
```

---

**Documento versão:** 1.0  
**Atualizado:** April 2, 2026
