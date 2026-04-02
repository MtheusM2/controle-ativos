# ⚡ AÇÃO RÁPIDA — Roteiro Executivo em 5 Etapas

**Tempo estimado:** 2-3 horas  
**Complexidade:** Média  
**Risco:** Requer atenção na limpeza git  

---

## 📋 RESUMO DAS AÇÕES

```
Hoje:
[ ] 1. Rotacionar credenciais do banco (15 min)
[ ] 2. Atualizar .env localmente (5 min)
[ ] 3. Executar limpeza git (30-45 min)
[ ] 4. Validar que está limpo (15 min)

Amanhã:
[ ] 5. Atualizar README e finalizar (30 min)
[ ] 6. Executar checklist completo (30 min)
[ ] 7. Publicar no GitHub (5 min)
```

---

## 1️⃣ ROTACIONAR CREDENCIAIS (15 min)

### Passo 1a: Nova Senha do Banco MySQL

```bash
# Conectar ao MySQL
mysql -u root -p etectcc@2026
# (Usar senha atual: etectcc@2026)

# Dentro do MySQL:
ALTER USER 'root'@'localhost' IDENTIFIED BY 'N3w_Secure_P@ss_2024_ChangeMe!';
FLUSH PRIVILEGES;
EXIT;
```

### Passo 1b: Gerar novos secrets

```bash
# Abrir PowerShell e gerar valores aleatórios
python -c "import secrets; print('FLASK_SECRET_KEY=' + secrets.token_hex(32))"
python -c "import secrets; print('APP_PEPPER=' + secrets.token_hex(32))"

# Copiar os valores
```

### Passo 1c: Atualizar .env localmente (NÃO fazer commit)

```bash
# Editar .env local com novos valores
nano .env
# ou
code .env
```

**Conteúdo novo:**
```
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=N3w_Secure_P@ss_2024_ChangeMe!          ← Nova senha aqui
DB_NAME=controle_ativos
FLASK_SECRET_KEY=<novo_secret_gerado_acima>        ← Cola aqui
APP_PEPPER=<novo_pepper_gerado_acima>              ← Cola aqui
```

**Salvar, mas NÃO fazer commit.**

### ✅ Validar

```bash
# Testar conexão com nova senha
python database/init_db.py
# Deve conectar sem erro
```

---

## 2️⃣ LIMPEZA GIT (30-45 min)

**AVISO:** Isso reescreve o histórico. Backup feito automaticamente.

### Passo 2a: Criar branch de backup

```bash
git branch backup_before_cleanup
# Agora tem um backup de tudo
```

### Passo 2b: Remover .env do histórico

```bash
# Instalar git-filter-repo (se não tiver)
pip install git-filter-repo

# Remover .env de TODOS os commits
git filter-repo --path .env --invert-paths

# (Isso leva um minuto ou dois)
```

### Passo 2c: Remover arquivos acadêmicos

```bash
# Remover arquivos do filesytem
rm ETAPA5_*.md ETAPA5_*.py
rm REFACTORING_*.md
rm STEP_*.py DIAGNOSE_SCHEMA.py
rm MIGRATION_GUIDE.md
rm PRE_DEPLOY_CHECKLIST.md
rm BACKUP_*.csv
rm -r "Interface Sistema Controle Ativos"

# Confirmar que foram deletados
git status
# Deve mostrar como deletado

# Fazer commit
git add -A
git commit -m "cleanup: remove TCC artifacts, backups, and internal scripts"
```

### Passo 2d: Forçar push com histórico reescrito

```bash
# push com força (MAS seguro)
git push origin main --force-with-lease

# Se tiver erro de permissão, contacte o DBA/admin repo
```

---

## 3️⃣ VALIDAÇÃO — Confirmar que Está Limpo (15 min)

### Passo 3a: Procurar credenciais no histórico

```bash
# Procurar por "password", "secret", "key"
git log -p | grep -i "password\|secret\|DB_PASSWORD"

# Deve retornar NADA (ou logs bem antigos)
# Se retornar algo, contacte suporte
```

### Passo 3b: Listar arquivos no repositório

```bash
# Confirmar que .env NÃO está
git ls-files | grep ".env"
# Deve retornar NADA (ou só ".env.example")

# Confirmar que acadêmicos foram removidos
git ls-files | grep "ETAPA\|REFACTORING\|STEP_"
# Deve retornar NADA

# Confirmar que CSVs foram removidos
git ls-files | grep "BACKUP_"
# Deve retornar NADA
```

### ✅ Se tudo passou

```
✅ Credenciais foram removidas
✅ Arquivos acadêmicos foram removidos
✅ Histórico foi reescrito e empurrado
```

---

## 4️⃣ ATUALIZAR README E FINALIZAR (30 min)

### Passo 4a: Substituir README

```bash
# Remover README antigo
mv README.md README_OLD.md

# Usar novo README
mv README_NOVO.md README.md

# Confirmar conteúdo
cat README.md | head -20
# Deve mostrar novo conteúdo profissional
```

### Passo 4b: Confirmar arquivos de suporte

```bash
# Verificar que .env.example existe
ls -la .env.example
# Deve retornar arquivo sem credenciais

# Verificar que requirements.txt está preenchido
cat requirements.txt
# Deve ter Flask, mysql-connector-python, etc
```

### Passo 4c: Fazer commit final

```bash
git add README.md .env.example requirements.txt
git commit -m "docs: update README to professional standard and add .env.example"
git push origin main
```

---

## 5️⃣ VALIDAÇÃO FINAL (30 min)

### Passo 5a: Testar instalação limpa

```bash
# Simular novo clone/novo dev
python -m venv test_env
source test_env/bin/activate  # ou .venv\Scripts\Activate.ps1

# Instalar dependências
pip install -r requirements.txt
# Deve funcionar sem erros

# Desativar
deactivate
rm -r test_env
```

### Passo 5b: Testar aplicação

```bash
# Ativar ambiente principal
source .venv/bin/activate

# Testar CLI
python main.py
# Deve iniciar menu

# Testar web
python web_app/app.py
# Deve iniciar em http://localhost:5000
```

### Passo 5c: Executar PRE_PUBLISH_CHECKLIST

```bash
# Abrir arquivo
cat PRE_PUBLISH_CHECKLIST.md

# Marcar cada item conforme valida
# Deve passar em TODOS os itens antes de publicar
```

---

## ✅ RESULTADO FINAL

### No seu repositório GitHub terá:

```
✅ Sem credenciais expostas
✅ Sem arquivos acadêmicos
✅ Sem .env commitado
✅ README profissional
✅ requirements.txt funcional
✅ .env.example como template
✅ Histórico limpo
✅ Pronto para portfólio corporativo
```

### Verificar no GitHub

```bash
# Ir para https://github.com/seu-usuario/opus-assets

# Validar:
[ ] README é profissional
[ ] Não há "ETAPA5", "REFACTORING", "STEP_", "Interface Sistema"
[ ] Não há .env com credenciais
[ ] .env.example está lá
[ ] requirements.txt tem conteúdo
```

---

## 🆘 TROUBLESHOOTING

### Problem: "git push rejeitado com erro de permissão"
**Solução:** 
```bash
git push origin main --force-with-lease --repo <full-repo-url>
# Ou contacte admin do repositório GitHub para ativar force-push
```

### Problem: "git-filter-repo não encontrado"
**Solução:**
```bash
pip install git-filter-repo
# Depois tentar de novo
```

### Problem: "Still see credenciais no git log"
**Solução:**
```bash
# Fazer cleanup mais agressivo
git filter-repo --path .env --invert-paths
git log -p | grep password  # Procurar de novo
# Se ainda aparece, contacte suporte Git/DevOps
```

### Problem: "Removi arquivo errado"
**Solução:**
```bash
# Você tem um backup!
git reset --hard backup_before_cleanup
# Começa de novo com cuidado
```

---

## ⏱️ TIMELINE

| Hora | Atividade | Duração |
|------|-----------|---------|
| 14:00 | Rotacionar credenciais | 15 min |
| 14:15 | Atualizar .env local | 5 min |
| 14:20 | Limpeza git (filter-repo) | 30 min |
| 14:50 | Validação de limpeza | 15 min |
| 15:05 | Atualizar README | 20 min |
| 15:25 | Commit final | 5 min |
| **15:30** | **✅ PRONTO PARA PUBLICAR** | |

---

## 📝 Checklist Rápido Antes de Publicar

- [ ] `.env` não está nos arquivos do repo
- [ ] `.env` não está no histórico git
- [ ] `ETAPA5_*` foram removidos
- [ ] `REFACTORING_*` foram removidos
- [ ] `STEP_*.py` foram removidos
- [ ] `BACKUP_*.csv` foram removidos
- [ ] `"Interface Sistema..."` foi removido
- [ ] README.md é novo e profissional
- [ ] `.env.example` existe sem credenciais
- [ ] `requirements.txt` tem dependências
- [ ] `pip install -r requirements.txt` funciona
- [ ] `python main.py` funciona
- [ ] `git log -p | grep password` retorna nada

---

## 🎯 KPI (Como saber que funcionou)

```
ANTES:
- git ls-files | wc -l  → ~25+ arquivos
- git log --oneline | wc -l → 50+? commits

DEPOIS:
- git ls-files | wc -l  → ~15 arquivos (limpo)
- git log --oneline | wc -l → menos commits (rewriter)
- git log -p | grep password → NADA (seguro)
- Repository aparecem profissional no GitHub ✅
```

---

## 📞 SUPORTE RÁPIDO

Se ficar preso em qualquer passo:

1. Consulte o doc correspondente:
   - Segurança/credenciais → `CLEANUP_GIT_HISTORY.md`
   - Validação → `PRE_PUBLISH_CHECKLIST.md`
   - Análise completa → `SENIOR_REVIEW_COMPLETE.md`

2. Contacte equipe de DevOps/GitHub admin se houver erro de permissão

3. Tem branch `backup_before_cleanup` — pode resetar se errar

---

**Boa sorte! Você consegue!** 🚀

Qualquer dúvida, consulte os documentos de suporte. Você tem tudo que precisa aqui.

---

**Versão:** 1.0  
**Última atualização:** April 2, 2026
