# Guia Completo — Do Servidor Zerado ao App em Produção

Este guia parte de um **Windows Server 2019/2022 limpo** e leva até o sistema
rodando com HTTPS, serviço automático e reverse proxy no IIS.

Tempo estimado: 45–90 minutos (depende da velocidade de download).

---

## Índice

1. [Pré-requisitos de hardware/rede](#1-pré-requisitos-de-hardwarerede)
2. [Instalar Python 3.11](#2-instalar-python-311)
3. [Instalar Git](#3-instalar-git)
4. [Instalar MySQL 8](#4-instalar-mysql-8)
5. [Instalar NSSM](#5-instalar-nssm)
6. [Instalar IIS com ARR e URL Rewrite](#6-instalar-iis-com-arr-e-url-rewrite)
7. [Clonar o repositório](#7-clonar-o-repositório)
8. [Executar o bootstrap do servidor](#8-executar-o-bootstrap-do-servidor)
9. [Configurar o .env com valores reais](#9-configurar-o-env-com-valores-reais)
10. [Criar o banco de dados e usuário](#10-criar-o-banco-de-dados-e-usuário)
11. [Instalar o serviço Windows (NSSM)](#11-instalar-o-serviço-windows-nssm)
12. [Configurar o IIS como reverse proxy](#12-configurar-o-iis-como-reverse-proxy)
13. [Configurar TLS / HTTPS](#13-configurar-tls--https)
14. [Verificação final](#14-verificação-final)
15. [Operação do dia a dia](#15-operação-do-dia-a-dia)
16. [Solução de problemas](#16-solução-de-problemas)

---

## 1. Pré-requisitos de hardware/rede

- Windows Server 2019 ou 2022 (Standard ou Datacenter)
- Mínimo: 2 vCPUs, 4 GB RAM, 40 GB disco
- Acesso à internet para baixar os instaladores
- Permissão de Administrador local
- Porta 80 e 443 abertas no firewall/roteador

> Todos os comandos abaixo são executados no **PowerShell como Administrador**
> (botão direito → "Executar como Administrador").

---

## 2. Instalar Python 3.11

1. Baixe o instalador em: https://www.python.org/downloads/release/python-3119/
   - Arquivo: `python-3.11.9-amd64.exe`

2. Execute o instalador com as opções abaixo:
   - **Marque**: "Add python.exe to PATH"
   - **Marque**: "Install for all users"
   - Clique em "Install Now"

3. Verifique a instalação:

```powershell
python --version
# Saída esperada: Python 3.11.x
```

---

## 3. Instalar Git

1. Baixe em: https://git-scm.com/download/win
   - Arquivo: `Git-2.x.x-64-bit.exe`

2. Execute o instalador com as configurações padrão (Next > Next > Install).

3. Verifique:

```powershell
git --version
# Saída esperada: git version 2.x.x
```

---

## 4. Instalar MySQL 8

### 4.1 Download e instalação

1. Baixe o MySQL Installer em: https://dev.mysql.com/downloads/installer/
   - Arquivo: `mysql-installer-community-8.0.x.msi`

2. Execute o instalador:
   - Selecione "Custom" na tela de tipo de instalação
   - Adicione apenas: **MySQL Server 8.0** e **MySQL Shell**
   - Clique em Next > Execute > Next

3. Na tela de configuração do servidor:
   - Type: **Development Computer** (ou Server se for dedicado)
   - Port: `3306` (padrão)
   - Authentication: **Use Strong Password Encryption** (caching_sha2_password)

4. Defina a senha do root quando solicitado. **Anote essa senha.**

5. Marque "Start MySQL Server at System Startup" e finalize.

### 4.2 Adicionar MySQL ao PATH

```powershell
# Adiciona o diretório do MySQL ao PATH permanentemente
[Environment]::SetEnvironmentVariable(
    "PATH",
    $env:PATH + ";C:\Program Files\MySQL\MySQL Server 8.0\bin",
    [EnvironmentVariableTarget]::Machine
)

# Reabra o PowerShell e verifique:
mysql --version
# Saída esperada: mysql  Ver 8.0.x ...
```

---

## 5. Instalar NSSM

O NSSM é o gerenciador que roda o Waitress como serviço Windows.

1. Baixe em: https://nssm.cc/download
   - Arquivo: `nssm-2.24.zip` (ou versão mais recente)

2. Extraia e coloque o executável em um local permanente:

```powershell
# Exemplo: extrair para C:\tools\nssm\
Expand-Archive -Path "$env:USERPROFILE\Downloads\nssm-2.24.zip" -DestinationPath "C:\tools"
Rename-Item "C:\tools\nssm-2.24" "C:\tools\nssm"
```

3. Adicione ao PATH:

```powershell
[Environment]::SetEnvironmentVariable(
    "PATH",
    $env:PATH + ";C:\tools\nssm\win64",
    [EnvironmentVariableTarget]::Machine
)
```

4. Verifique (em um novo PowerShell):

```powershell
nssm version
# Saída esperada: NSSM 2.24 ...
```

---

## 6. Instalar IIS com ARR e URL Rewrite

### 6.1 Habilitar o IIS

```powershell
# Instala o IIS com os recursos necessários para reverse proxy
Install-WindowsFeature -Name Web-Server, Web-Common-Http, Web-Http-Redirect,
    Web-Static-Content, Web-Default-Doc, Web-Http-Errors,
    Web-Http-Logging, Web-Request-Monitor, Web-Http-Tracing,
    Web-Security, Web-Filtering, Web-Windows-Auth,
    Web-Mgmt-Tools, Web-Mgmt-Console -IncludeManagementTools
```

Aguarde a instalação concluir (1–2 minutos).

### 6.2 Instalar URL Rewrite

```powershell
# Baixa e instala o módulo URL Rewrite
$urlRewrite = "$env:TEMP\rewrite_amd64_en-US.msi"
Invoke-WebRequest -Uri "https://download.microsoft.com/download/1/2/8/128E2E22-C1B9-44A4-BE2A-5859ED1D4592/rewrite_amd64_en-US.msi" -OutFile $urlRewrite
Start-Process msiexec.exe -ArgumentList "/i `"$urlRewrite`" /quiet /norestart" -Wait
```

### 6.3 Instalar Application Request Routing (ARR)

```powershell
# Baixa e instala o ARR
$arr = "$env:TEMP\ARRv3_setup_amd64_en-US.exe"
Invoke-WebRequest -Uri "https://download.microsoft.com/download/E/9/8/E9849D6A-020E-47E4-9FD0-A023E99B54EB/ARRv3_setup_amd64_en-US.exe" -OutFile $arr
Start-Process $arr -ArgumentList "/quiet" -Wait
```

### 6.4 Habilitar o proxy no ARR

```powershell
# Habilita o proxy reverso no ARR via linha de comando
Import-Module WebAdministration
Set-WebConfigurationProperty -Filter "system.webServer/proxy" -PSPath "IIS:\" -Name "enabled" -Value $true
```

> **Alternativa visual:** IIS Manager → clique no servidor (nível raiz) →
> "Application Request Routing Cache" → "Server Proxy Settings" → marque "Enable proxy" → Apply.

---

## 7. Clonar o repositório

```powershell
# Cria o diretório de instalação
New-Item -ItemType Directory -Path "C:\controle_ativos" -Force

# Clona o repositório
git clone https://github.com/MtheusM2/controle-ativos.git C:\controle_ativos

# Entra no diretório
Set-Location C:\controle_ativos
```

---

## 8. Executar o bootstrap do servidor

Este script cria o virtualenv, instala dependências e prepara os diretórios:

```powershell
cd C:\controle_ativos
.\scripts\setup_server.ps1
```

O script irá:
- Verificar se Python está disponível
- Criar o `.env` a partir do `.env.example` (com aviso para edição)
- Criar o virtualenv em `.venv\`
- Instalar todas as dependências do `requirements.txt`
- Criar os diretórios `logs\` e `web_app\static\uploads\`
- Executar um diagnóstico de configuração

> O diagnóstico vai **falhar** neste momento porque o `.env` ainda tem valores de exemplo.
> Isso é esperado — continue para o próximo passo.

---

## 9. Configurar o .env com valores reais

Edite o arquivo `C:\controle_ativos\.env`:

```powershell
notepad C:\controle_ativos\.env
```

Preencha cada variável:

```ini
# Banco de dados
DB_HOST=localhost
DB_PORT=3306
DB_USER=opus_app
DB_PASSWORD=<senha-forte-para-o-usuario-opus_app>
DB_NAME=controle_ativos

# Segurança Flask — gere valores únicos com o comando abaixo
FLASK_SECRET_KEY=<valor-gerado>
APP_PEPPER=<valor-gerado>

# Modo de operação
FLASK_DEBUG=0
SESSION_COOKIE_SECURE=1

# Sessão
SESSION_LIFETIME_MINUTES=120

# Proteção de login
AUTH_MAX_FAILED_ATTEMPTS=5
AUTH_LOCKOUT_MINUTES=15

# Logging
LOG_LEVEL=WARNING
LOG_DIR=logs

# Segurança de senha
PBKDF2_ITERATIONS=600000
```

**Gere os valores para SECRET_KEY e PEPPER:**

```powershell
cd C:\controle_ativos
.venv\Scripts\python -c "import secrets; print('FLASK_SECRET_KEY=' + secrets.token_hex(32))"
.venv\Scripts\python -c "import secrets; print('APP_PEPPER=' + secrets.token_hex(32))"
```

Cole os valores gerados no `.env`. **Nunca reutilize os mesmos valores em servidores diferentes.**

---

## 10. Criar o banco de dados e usuário

### 10.1 Aplicar o schema

```powershell
cd C:\controle_ativos
mysql -u root -p < database\schema.sql
```

Digite a senha do root quando solicitado. O schema criará o banco `controle_ativos`
e todas as tabelas necessárias.

### 10.2 Criar o usuário da aplicação

O app nunca usa o root. Crie um usuário com permissões mínimas:

```powershell
mysql -u root -p
```

Dentro do MySQL, execute:

```sql
-- Cria o usuário com acesso apenas local
CREATE USER 'opus_app'@'localhost' IDENTIFIED BY '<mesma-senha-do-DB_PASSWORD-no-env>';

-- Concede apenas o necessário (sem DROP, sem GRANT, sem DDL)
GRANT SELECT, INSERT, UPDATE, DELETE ON controle_ativos.* TO 'opus_app'@'localhost';

FLUSH PRIVILEGES;
EXIT;
```

### 10.3 Verificar conexão

```powershell
cd C:\controle_ativos
.venv\Scripts\python scripts\test_db_connection.py
# Saída esperada: Conexão OK
```

---

## 11. Instalar o serviço Windows (NSSM)

Com o NSSM no PATH, o `.env` configurado e o banco funcionando:

```powershell
cd C:\controle_ativos
.\deploy\nssm\install_service.ps1 -ProjectDir "C:\controle_ativos"
```

O script irá:
- Validar que NSSM, o venv e o `.env` existem
- Remover o serviço anterior se já existir
- Registrar o Waitress como serviço Windows com inicialização automática
- Carregar as variáveis do `.env` no serviço
- Configurar rotação de logs (arquivos de 10 MB em `logs\`)
- Iniciar o serviço imediatamente

**Verificar se está rodando:**

```powershell
Get-Service controle_ativos
# Status esperado: Running

Invoke-WebRequest http://127.0.0.1:8000/health
# Saída esperada: {"ok": true, "status": "healthy"}
```

---

## 12. Configurar o IIS como reverse proxy

### 12.1 Criar o site no IIS

```powershell
Import-Module WebAdministration

# Remove o site Default Web Site se existir na porta 80
Remove-Website -Name "Default Web Site" -ErrorAction SilentlyContinue

# Cria o site do sistema
New-Website -Name "controle_ativos" `
            -PhysicalPath "C:\controle_ativos" `
            -Port 80 `
            -Force
```

### 12.2 Aplicar o web.config

O arquivo `deploy\iis\web.config` já está configurado. Copie-o para a raiz:

```powershell
Copy-Item "C:\controle_ativos\deploy\iis\web.config" `
          "C:\controle_ativos\web.config" -Force
```

> Se você apontou o site IIS diretamente para `C:\controle_ativos`,
> o IIS já lê o `web.config` automaticamente — não precisa copiar.

### 12.3 Verificar o proxy

```powershell
# O IIS deve encaminhar a requisição para o Waitress
Invoke-WebRequest http://localhost/health
# Saída esperada: {"ok": true, "status": "healthy"}
```

---

## 13. Configurar TLS / HTTPS

### Opção A — Certificado emitido por CA interna ou pública

1. Abra o **IIS Manager** (Win + R → `inetmgr`)
2. Clique no servidor (nível raiz) → **Server Certificates**
3. Importe o certificado (`.pfx`) com a chave privada
4. No site `controle_ativos` → **Bindings** → **Add**:
   - Type: `https`
   - Port: `443`
   - SSL certificate: selecione o certificado importado
5. Clique em OK

### Opção B — Certificado autoassinado (apenas para testes internos)

```powershell
# Cria certificado autoassinado válido por 3 anos
$cert = New-SelfSignedCertificate `
    -DnsName "controle-ativos.suaempresa.com.br" `
    -CertStoreLocation "cert:\LocalMachine\My" `
    -NotAfter (Get-Date).AddYears(3)

# Adiciona o binding HTTPS no site
$binding = Get-WebBinding -Name "controle_ativos" -Protocol "http"
New-WebBinding -Name "controle_ativos" -Protocol "https" -Port 443

# Associa o certificado
$sslPath = "IIS:\SslBindings\0.0.0.0!443"
if (Test-Path $sslPath) { Remove-Item $sslPath }
$cert | New-Item -Path $sslPath
```

### Após configurar HTTPS

Confirme no `.env` que está ativo:

```ini
SESSION_COOKIE_SECURE=1
```

Reinicie o serviço para aplicar:

```powershell
Restart-Service controle_ativos
```

---

## 14. Verificação final

Execute cada item e confirme que está OK:

```powershell
# 1. Serviço rodando
Get-Service controle_ativos
# Esperado: Status = Running

# 2. Waitress respondendo diretamente
Invoke-WebRequest http://127.0.0.1:8000/health
# Esperado: {"ok": true, "status": "healthy"}

# 3. IIS encaminhando via HTTP
Invoke-WebRequest http://localhost/health
# Esperado: {"ok": true, "status": "healthy"}

# 4. IIS encaminhando via HTTPS
Invoke-WebRequest https://localhost/health -SkipCertificateCheck
# Esperado: {"ok": true, "status": "healthy"}

# 5. Acesso direto a uploads bloqueado (deve retornar 403)
Invoke-WebRequest http://localhost/static/uploads/qualquer-coisa.pdf
# Esperado: StatusCode 403

# 6. Logs sem erros críticos
Get-Content C:\controle_ativos\logs\waitress_stderr.log -Tail 30
```

**Checklist de segurança:**

- [ ] `.env` não tem nenhum valor `CHANGE_ME`
- [ ] `FLASK_DEBUG=0`
- [ ] `SESSION_COOKIE_SECURE=1`
- [ ] `LOG_LEVEL=WARNING`
- [ ] Usuário `opus_app` criado com permissões mínimas
- [ ] Login funcional com usuário real
- [ ] Upload e download de documento funcionando
- [ ] Export CSV/XLSX/PDF funcionando

---

## 15. Operação do dia a dia

### Atualizar o sistema após novo deploy

```powershell
cd C:\controle_ativos
git pull
Restart-Service controle_ativos
```

### Parar / iniciar / reiniciar

```powershell
Stop-Service controle_ativos
Start-Service controle_ativos
Restart-Service controle_ativos
```

### Ver logs em tempo real

```powershell
Get-Content C:\controle_ativos\logs\waitress_stderr.log -Wait -Tail 30
```

### Ver status do serviço

```powershell
Get-Service controle_ativos
```

### Rollback para commit anterior

```powershell
cd C:\controle_ativos
git log --oneline -10       # identifique o commit
git checkout <hash-do-commit>
Restart-Service controle_ativos
```

---

## 16. Solução de problemas

### Serviço não inicia

```powershell
# Ver log de erro do Waitress
Get-Content C:\controle_ativos\logs\waitress_stderr.log -Tail 50

# Testar a aplicação manualmente (fora do serviço)
cd C:\controle_ativos
.venv\Scripts\python -m waitress --listen=127.0.0.1:8000 wsgi:application
```

### Erro de conexão com o banco

```powershell
# Testar conexão isoladamente
cd C:\controle_ativos
.venv\Scripts\python scripts\test_db_connection.py

# Verificar se o MySQL está rodando
Get-Service MySQL80
```

### IIS retorna 502 Bad Gateway

Significa que o IIS está funcionando mas o Waitress não está respondendo.

```powershell
# Verificar se o Waitress está na porta 8000
netstat -an | findstr ":8000"
# Deve aparecer uma linha com LISTENING

# Verificar o serviço
Get-Service controle_ativos
```

### ARR proxy não encaminha requisições

```powershell
# Verificar se o proxy está habilitado
Import-Module WebAdministration
Get-WebConfigurationProperty -Filter "system.webServer/proxy" -PSPath "IIS:\" -Name "enabled"
# Deve retornar True

# Se False, habilitar:
Set-WebConfigurationProperty -Filter "system.webServer/proxy" -PSPath "IIS:\" -Name "enabled" -Value $true
```

### Diagnóstico completo de configuração

```powershell
cd C:\controle_ativos
.venv\Scripts\python scripts\diagnose_runtime_config.py
```
