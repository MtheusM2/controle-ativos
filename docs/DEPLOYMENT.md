# Guia de Deploy — Controle de Ativos

## Stack de producao

| Componente       | Tecnologia                          |
|------------------|-------------------------------------|
| Linguagem        | Python 3.11                         |
| Framework        | Flask 2.3                           |
| Servidor WSGI    | Waitress 3.0 (nativo no Windows)    |
| Servico Windows  | NSSM (Non-Sucking Service Manager)  |
| Reverse proxy    | IIS (Internet Information Services) |
| Banco de dados   | MySQL 8                             |
| TLS              | Gerenciado pelo IIS                 |

---

## Desenvolvimento local (Windows)

```powershell
# 1. Copie o .env de exemplo e preencha os segredos
cp .env.example .env

# 2. Inicialize o banco de dados
python database/init_db.py

# 3. Inicie a aplicacao em modo desenvolvimento
scripts/start_local.ps1
```

### Simular producao localmente

```powershell
# Roda o Waitress na porta 8001 sem modo debug
scripts/simulate_production.ps1 -Port 8001
```

---

## Producao — Windows Server

### Pre-requisitos no servidor

- Windows Server 2019 ou superior
- Python 3.11+ instalado e no PATH
- MySQL 8 instalado e em execucao
- IIS instalado com os modulos:
  - **URL Rewrite** — [download](https://www.iis.net/downloads/microsoft/url-rewrite)
  - **Application Request Routing (ARR)** — [download](https://www.iis.net/downloads/microsoft/application-request-routing)
- **NSSM** — [download](https://nssm.cc/download), adicione ao PATH

### 1. Copiar o projeto para o servidor

```powershell
# Clonar via Git (recomendado)
git clone <URL_REPO> C:\controle_ativos
cd C:\controle_ativos
```

Ou copiar os arquivos via rede para `C:\controle_ativos`.

### 2. Bootstrap inicial (como Administrador)

```powershell
cd C:\controle_ativos
.\scripts\setup_server.ps1
```

O script:
- Cria o `.env` a partir de `.env.example`
- Cria o virtualenv e instala dependencias
- Cria as pastas `logs\` e `web_app\static\uploads\`
- Executa o diagnostico de configuracao

### 3. Configure o `.env`

Edite `C:\controle_ativos\.env` com os valores reais:

```
DB_HOST=localhost
DB_PORT=3306
DB_USER=opus_app
DB_PASSWORD=<senha-forte>
DB_NAME=controle_ativos
FLASK_SECRET_KEY=<chave-aleatoria-32-chars>
APP_PEPPER=<pepper-aleatorio-32-chars>
SESSION_COOKIE_SECURE=1
FLASK_DEBUG=0
LOG_LEVEL=WARNING
```

Gere valores seguros com:
```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

### 4. Banco de dados

```powershell
# Criar schema completo (inclui todas as tabelas)
mysql -u root -p < database\schema.sql

# Aplicar migracoes se o banco ja existir
mysql -u root -p controle_ativos < database\migrations\001_usuario_responsavel_opcional.sql
mysql -u root -p controle_ativos < database\migrations\002_empresas_perfis_escopo.sql
mysql -u root -p controle_ativos < database\migrations\003_seguro_para_garantia.sql
mysql -u root -p controle_ativos < database\migrations\004_usuarios_nome_lembrar_me.sql
```

### 5. Instalar o servico Windows (NSSM)

Execute como **Administrador**:

```powershell
.\deploy\nssm\install_service.ps1 -ProjectDir "C:\controle_ativos"
```

O script:
- Remove o servico anterior se existir
- Registra o Waitress como servico Windows com inicializacao automatica
- Configura as variaveis de ambiente a partir do `.env`
- Redireciona logs para `logs\waitress_stdout.log` e `logs\waitress_stderr.log`
- Inicia o servico imediatamente

Verificar se esta rodando:
```powershell
Get-Service controle_ativos
Invoke-WebRequest http://127.0.0.1:8000/health
```

### 6. Configurar IIS como reverse proxy

**Habilitar proxy no ARR:**
1. Abra o IIS Manager
2. Clique no servidor (nivel raiz)
3. Abra "Application Request Routing Cache"
4. No painel direito, clique em "Server Proxy Settings"
5. Marque "Enable proxy" e clique em Apply

**Criar o site no IIS:**
1. IIS Manager > Sites > Add Website
2. Site name: `controle_ativos`
3. Physical path: `C:\controle_ativos`
4. Port: `80`

**Aplicar o web.config:**
O arquivo `deploy\iis\web.config` ja esta configurado com:
- Reverse proxy para `http://127.0.0.1:8000`
- Bloqueio de acesso direto a uploads
- Headers de seguranca (CSP, X-Frame-Options, etc.)
- Limite de upload de 10 MB

Copie-o para a raiz do site:
```powershell
Copy-Item deploy\iis\web.config C:\controle_ativos\web.config
```

Ou aponte o site IIS diretamente para `C:\controle_ativos` — o IIS le o `web.config` automaticamente.

### 7. TLS / HTTPS

Configure o certificado no IIS:
1. IIS Manager > servidor > Server Certificates
2. Importe ou solicite o certificado
3. No site `controle_ativos`, adicione um binding HTTPS na porta 443
4. Ative no `.env`: `SESSION_COOKIE_SECURE=1`

---

## WSGI — Ponto de entrada

| Cenario             | Comando Waitress                                         |
|---------------------|----------------------------------------------------------|
| Producao (NSSM)     | `python -m waitress --listen=127.0.0.1:8000 wsgi:application` |
| Simulacao local     | `scripts\simulate_production.ps1`                        |
| Desenvolvimento     | `scripts\start_local.ps1`                                |

---

## Operacao

### Reiniciar apos atualizacao de codigo

```powershell
cd C:\controle_ativos
git pull
Restart-Service controle_ativos
```

### Parar / iniciar o servico

```powershell
Stop-Service controle_ativos
Start-Service controle_ativos
```

### Ver status do servico

```powershell
Get-Service controle_ativos
```

### Ver logs

```powershell
# Logs do Waitress
Get-Content logs\waitress_stderr.log -Tail 50
Get-Content logs\waitress_stdout.log -Tail 50

# Acompanhar em tempo real
Get-Content logs\waitress_stderr.log -Wait -Tail 20
```

### Rollback

```powershell
cd C:\controle_ativos
git checkout <commit-anterior>
Restart-Service controle_ativos
```

---

## Checklist pre-producao

- [ ] `.env` preenchido com segredos reais (sem valores `CHANGE_ME`)
- [ ] `SESSION_COOKIE_SECURE=1` habilitado (exige HTTPS)
- [ ] `FLASK_DEBUG=0`
- [ ] `LOG_LEVEL=WARNING` ou `ERROR`
- [ ] Banco de dados criado com schema completo + migracoes aplicadas
- [ ] Usuario `opus_app` criado com permissoes minimas (`SELECT, INSERT, UPDATE, DELETE`)
- [ ] Servico Windows instalado e iniciando automaticamente
- [ ] IIS configurado com URL Rewrite + ARR habilitado
- [ ] `web.config` aplicado no site IIS
- [ ] Acesso direto a `/static/uploads/` retorna 403 (IIS bloqueando)
- [ ] Healthcheck respondendo (`/health` retorna `{"ok": true}`)
- [ ] Certificado TLS configurado e HTTPS funcionando

## Checklist pos-deploy

- [ ] Login funcional com usuario real
- [ ] CRUD de ativos funcionando
- [ ] Upload de documento funcionando
- [ ] Download de documento funcionando (apenas via rota autenticada)
- [ ] Export CSV/XLSX/PDF funcionando
- [ ] Logs sem erros criticos (`logs\waitress_stderr.log`)
