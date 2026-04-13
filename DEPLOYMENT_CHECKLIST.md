# DEPLOYMENT CHECKLIST — Atualização do Servidor

**Versão:** 2026-04-13  
**Objetivo:** Sincronizar servidor com repositório `main` de forma segura e profissional

---

## PARTE 1: PREPARAÇÃO ANTES DA ATUALIZAÇÃO

### 1.1 Backup Completo

- [ ] **Backup do banco de dados:**
  ```powershell
  mysqldump -u root -p controle_ativos > "C:\backups\controle_ativos_$(Get-Date -f 'yyyyMMdd_HHmmss').sql"
  ```
  
- [ ] **Backup do diretório de aplicação:**
  ```powershell
  $backupPath = "C:\backups\controle_ativos_$(Get-Date -f 'yyyyMMdd_HHmmss')"
  Copy-Item -Path "C:\controle_ativos" -Destination $backupPath -Recurse -Force
  ```

- [ ] **Backup de configurações sensíveis:**
  ```powershell
  # Guardar em local seguro fora do repositório
  Copy-Item -Path "C:\controle_ativos\.env" -Destination "C:\backups\.env.bak"
  Copy-Item -Path "$env:APPDATA\cloudflared\" -Destination "C:\backups\cloudflared_config" -Recurse
  ```

- [ ] **Verificar espaço livre:**
  ```powershell
  Get-Volume C: | Select-Object SizeRemaining
  ```

### 1.2 Documentação de Estado Atual

- [ ] **Registrar versão atual:**
  ```powershell
  cd C:\controle_ativos
  git log --oneline -5 > "C:\backups\version_before_update.txt"
  git status >> "C:\backups\version_before_update.txt"
  ```

- [ ] **Registrar variáveis de ambiente em produção:**
  ```powershell
  # Lista variáveis (NÃO salve values reais, apenas keys):
  Get-ChildItem Env: | Where-Object {$_.Name -match "DB_|FLASK_|SESSION_"} | Select-Object Name | Export-Csv "C:\backups\env_keys_before.csv"
  ```

- [ ] **Snapshot de logs atuais:**
  ```powershell
  Copy-Item -Path "C:\controle_ativos\logs" -Destination "C:\backups\logs_before_update" -Recurse
  ```

### 1.3 Validação de Serviço Atual

- [ ] **Verificar status do serviço:**
  ```powershell
  Get-Service -Name "controle_ativos" | Select-Object Status, StartType
  ```

- [ ] **Testar aplicação em produção:**
  ```
  1. Acessar https://seu_dominio.com/
  2. Login com credenciais de teste
  3. Navegar em algumas páginas
  4. Verificar logs: C:\controle_ativos\logs\app.log
  ```

- [ ] **Validar conexão com banco:**
  ```powershell
  cd C:\controle_ativos
  python scripts/test_db_connection.py
  ```

### 1.4 Planejamento de Downtime

- [ ] **Informar stakeholders** sobre janela de atualização
- [ ] **Agendar atualização** em horário de baixa utilização
- [ ] **Preparar rollback** — ter plano pronto (veja PARTE 4)

---

## PARTE 2: ATUALIZAÇÃO DO SERVIDOR

### 2.1 Parar o Serviço

```powershell
# Parar serviço
Stop-Service -Name "controle_ativos" -Force

# Aguardar 5 segundos e verificar
Start-Sleep -Seconds 5
Get-Service -Name "controle_ativos" | Select-Object Status
```

### 2.2 Atualizar Repositório

```powershell
cd C:\controle_ativos

# Fetch da versão mais recente
git fetch origin main
git reset --hard origin/main

# Verificar versão
git log --oneline -1
```

### 2.3 Instalar/Atualizar Dependências

```powershell
cd C:\controle_ativos

# Atualizar pip
python -m pip install --upgrade pip

# Instalar requirements
pip install -r requirements.txt

# Verificar instalação
pip list | grep -E "Flask|MySQL|Waitress"
```

### 2.4 Aplicar Migrações de Banco (SE HOUVER)

```powershell
cd C:\controle_ativos

# Verificar se há novas migrações
dir database\migrations\

# Se houver novas migrações:
# Executar script de inicialização (já lida os .sql)
python database/init_db.py

# OU aplicar manualmente
# (consulte DEPLOYMENT.md para procedimento)
```

### 2.5 Iniciar o Serviço

```powershell
# Iniciar serviço
Start-Service -Name "controle_ativos"

# Aguardar inicialização (30 segundos)
Start-Sleep -Seconds 30

# Verificar status
Get-Service -Name "controle_ativos" | Select-Object Status, StartType
```

### 2.6 Validar Logs de Inicialização

```powershell
# Verificar se há erros nos logs
Get-Content "C:\controle_ativos\logs\app.log" -Tail 50

# Procurar por "ERROR" ou "CRITICAL"
Select-String -Path "C:\controle_ativos\logs\app.log" -Pattern "ERROR|CRITICAL" -Context 2
```

---

## PARTE 3: VALIDAÇÃO PÓS-ATUALIZAÇÃO

### 3.1 Testes Funcionais Básicos

- [ ] **Acessar aplicação:**
  ```
  https://seu_dominio.com/
  ```
  Esperado: Página de login carrega corretamente

- [ ] **Fazer login:**
  ```
  1. Usar credenciais de teste
  2. Verificar se sessão estabelece
  3. Verificar se dashboard carrega
  ```

- [ ] **Navegar funcionalidades principais:**
  ```
  [ ] Dashboard — carrega sem erro
  [ ] Listar ativos — carrega lista
  [ ] Criar ativo — formulário funciona
  [ ] Exportar — gera arquivo
  [ ] Logout — encerra sessão
  ```

### 3.2 Validação de Banco de Dados

```powershell
cd C:\controle_ativos

# Verificar conexão
python scripts/test_db_connection.py

# Contar registros principais
mysql -u opus_app -p -e "SELECT COUNT(*) as usuarios FROM controle_ativos.usuarios;"
mysql -u opus_app -p -e "SELECT COUNT(*) as ativos FROM controle_ativos.ativos;"
```

### 3.3 Validação de Segurança

```powershell
# Verificar certificados HTTPS (via Cloudflare)
# Acessar: https://seu_dominio.com/ e verificar lock de segurança

# Verificar headers de segurança
# DevTools → Network → Response Headers
# Procurar por: X-Content-Type-Options, X-Frame-Options, Content-Security-Policy
```

### 3.4 Validação de Configuração

```powershell
cd C:\controle_ativos
python scripts/diagnose_runtime_config.py

# Saída esperada:
# ✓ Database connection OK
# ✓ Flask configuration loaded
# ✓ Secret keys configured
# ✓ Logging configured
```

### 3.5 Monitoramento de Logs

```powershell
# Tail de logs em tempo real (PowerShell 7+)
Get-Content -Path "C:\controle_ativos\logs\app.log" -Tail 20 -Wait

# Ou em versões antigas:
while (1) { Clear-Host; Get-Content -Path "C:\controle_ativos\logs\app.log" -Tail 20; Start-Sleep -Seconds 2 }
```

---

## PARTE 4: PLANO DE ROLLBACK

### Se a atualização falhar:

#### 4.1 Parar Serviço Problemático

```powershell
Stop-Service -Name "controle_ativos" -Force
```

#### 4.2 Restaurar Código Anterior

```powershell
cd C:\controle_ativos

# Opção 1: Usar backup
Remove-Item -Path "C:\controle_ativos" -Recurse -Force
Copy-Item -Path "C:\backups\controle_ativos_[DATA_HORA]" -Destination "C:\controle_ativos" -Recurse

# Opção 2: Usar git
cd C:\controle_ativos
git reset --hard HEAD~1  # Volta 1 commit
git log --oneline -1    # Verificar
```

#### 4.3 Restaurar Banco (Se Necessário)

```powershell
# Se migrações causaram problema:
mysql -u root -p controle_ativos < "C:\backups\controle_ativos_[DATA_HORA].sql"

# Verificar integridade
mysql -u opus_app -p -e "SELECT COUNT(*) FROM controle_ativos.usuarios;"
```

#### 4.4 Reiniciar Serviço

```powershell
Start-Service -Name "controle_ativos"
Start-Sleep -Seconds 30
Get-Service -Name "controle_ativos"
```

#### 4.5 Verificar Logs

```powershell
Get-Content "C:\controle_ativos\logs\app.log" -Tail 50
```

#### 4.6 Investigar Problema

```
1. Revisar logs de erro
2. Checar variáveis de ambiente (.env)
3. Checar migrações de banco
4. Checar permissões de arquivo
5. Consultar DEPLOYMENT.md para troubleshooting
```

---

## PARTE 5: ARQUIVOS QUE REQUEREM CUIDADO MANUAL

### NÃO sobrescrever automaticamente:

| Arquivo | Ação | Razão |
|---------|------|-------|
| `.env` | **Verificar antes de sobrescrever** | Contém secrets locais de produção |
| `logs/` | **Preservar** | Histórico de operação |
| `web_app/static/uploads/` | **Preservar** | Anexos de ativos (dados do usuário) |
| `cloudflared/config.yml` | **Verificar** | Token do Cloudflare Tunnel |

### Procedimento para estes arquivos:

```powershell
# Antes de git reset/checkout:
$timestamp = Get-Date -f 'yyyyMMdd_HHmmss'
Copy-Item ".env" ".env.backup_$timestamp"
Copy-Item "cloudflared/config.yml" "cloudflared/config.yml.backup_$timestamp"

# Depois de checkout, restaurar se necessário:
Compare-Object -ReferenceObject (Get-Content ".env.example") `
              -DifferenceObject (Get-Content ".env") -PassThru
```

---

## PARTE 6: DIFERENÇAS ENTRE DESENVOLVIMENTO E PRODUÇÃO

### Configurações que diferem em produção:

```powershell
# .env em produção (via variáveis de ambiente Windows, NÃO arquivo):

# Desenvolvimento (local):
FLASK_DEBUG=1
SESSION_COOKIE_SECURE=0
PROXY_FIX_ENABLED=0

# Produção (servidor):
FLASK_DEBUG=0
SESSION_COOKIE_SECURE=1
PROXY_FIX_ENABLED=1
PREFERRED_URL_SCHEME=https
SERVER_NAME=seu_dominio.com
```

### Verificação:

```powershell
cd C:\controle_ativos
python -c "from config import Config; print(f'DEBUG={Config.FLASK_DEBUG}')"
```

---

## PARTE 7: COMUNICAÇÃO

### Notificação pós-atualização:

- [ ] Informar stakeholders que atualização foi bem-sucedida
- [ ] Documentar versão (git commit) deployed
- [ ] Registrar qualquer mudança de comportamento
- [ ] Manter logs de atualização em arquivo

---

## CHECKLIST RÁPIDO (RESUMO)

```powershell
# ANTES
[ ] Backup do banco
[ ] Backup da app
[ ] Verificar status atual
[ ] Testar app em produção

# DURANTE
[ ] Parar serviço
[ ] git pull origin main
[ ] pip install -r requirements.txt
[ ] Iniciar serviço
[ ] Aguardar 30s

# DEPOIS
[ ] Acessar aplicação
[ ] Fazer login
[ ] Testar funcionalidades
[ ] Verificar logs
[ ] Validar banco

# ROLLBACK (se necessário)
[ ] Parar serviço
[ ] git reset --hard HEAD~1
[ ] Restaurar banco (se migrações falhou)
[ ] Iniciar serviço
[ ] Validar
```

---

## REFERÊNCIAS

- **DEPLOYMENT.md** — Guia completo de deploy
- **SECURITY_DB_ROTATION_GUIDE.md** — Rotação de credenciais
- **CLOUDFLARE_TUNNEL_DEPLOY.md** — Manutenção do tunnel
- **docs_interno_local/** — Documentação histórica (backup local)

---

**NOTA IMPORTANTE:** Este checklist é baseado em Windows Server 2019+.  
Para outras plataformas (Linux, macOS), adapte os comandos PowerShell para equivalentes Bash.
