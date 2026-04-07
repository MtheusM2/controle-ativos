# Guia de Deploy — Controle de Ativos

## Desenvolvimento local (Windows)

```powershell
# 1. Copie o .env de exemplo e preencha os segredos
cp .env.example .env

# 2. Inicialize o banco de dados
python database/init_db.py

# 3. Inicie a aplicação
scripts/start_local.ps1
```

## Desenvolvimento local (Linux / WSL)

```bash
cp .env.example .env
python3 database/init_db.py
bash scripts/start_local.sh
```

---

## Produção — Ubuntu Linux

### 1. Clone e estrutura

```bash
sudo mkdir -p /opt/controle_ativos
sudo chown www-data:www-data /opt/controle_ativos
git clone <URL_REPO> /opt/controle_ativos
cd /opt/controle_ativos
```

### 2. Bootstrap inicial

```bash
bash scripts/setup_server.sh
```

O script:
- Cria o `.env` a partir de `.env.example`
- Cria o virtualenv e instala dependências
- Cria pastas `logs/` e `web_app/static/uploads/` com permissões restritivas

### 3. Configure o `.env`

Edite `/opt/controle_ativos/.env` com os valores reais:

```
DB_USER=opus_app
DB_PASSWORD=<senha-forte>
DB_NAME=controle_ativos
FLASK_SECRET_KEY=<chave-aleatória-32-chars>
APP_PEPPER=<pepper-aleatório-32-chars>
SESSION_COOKIE_SECURE=1
FLASK_DEBUG=0
```

Gere valores seguros com:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### 4. Banco de dados

```bash
# Criar schema completo (inclui todas as tabelas)
mysql -u root -p < database/schema.sql

# Aplicar migrações sequencialmente se o banco já existir
mysql -u root -p controle_ativos < database/migrations/001_usuario_responsavel_opcional.sql
mysql -u root -p controle_ativos < database/migrations/002_empresas_perfis_escopo.sql
mysql -u root -p controle_ativos < database/migrations/003_seguro_para_garantia.sql
mysql -u root -p controle_ativos < database/migrations/004_usuarios_nome_lembrar_me.sql
```

### 5. Nginx

```bash
sudo cp deploy/nginx/controle_ativos.conf /etc/nginx/sites-available/controle_ativos
sudo ln -s /etc/nginx/sites-available/controle_ativos /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

> O arquivo de configuração Nginx inclui headers de segurança (CSP, X-Frame-Options,
> X-Content-Type-Options, Referrer-Policy) e bloqueia acesso direto à pasta de uploads.

### 6. Systemd

```bash
sudo cp deploy/systemd/controle_ativos.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable controle_ativos
sudo systemctl start controle_ativos
```

### 7. Verificação

```bash
# Healthcheck local
curl http://localhost:8000/health

# Verificar logs
sudo journalctl -u controle_ativos -f
```

---

## WSGI — Ponto de entrada

| Cenário           | Target Gunicorn    |
|-------------------|--------------------|
| Produção (systemd)| `wsgi:app`         |
| Alternativo       | `wsgi:application` |

Ambos são equivalentes — `wsgi.py` expõe `app = application`.

---

## Operação

### Reiniciar após atualização de código

```bash
cd /opt/controle_ativos
git pull
sudo systemctl restart controle_ativos
```

### Rollback

```bash
git checkout <commit-anterior>
sudo systemctl restart controle_ativos
```

### Rotação de logs

Os logs do Gunicorn são direcionados ao journald pelo systemd.
Para consultar:
```bash
sudo journalctl -u controle_ativos --since "1 hour ago"
```

---

## Checklist pré-produção

- [ ] `.env` preenchido com segredos reais (sem valores `CHANGE_ME`)
- [ ] `SESSION_COOKIE_SECURE=1` habilitado (exige HTTPS)
- [ ] `FLASK_DEBUG=0`
- [ ] `LOG_LEVEL=WARNING` ou `ERROR` para produção
- [ ] Banco de dados criado com schema completo + migrações aplicadas
- [ ] Usuário `opus_app` criado com permissões mínimas (`SELECT, INSERT, UPDATE, DELETE`)
- [ ] Pastas `logs/` e `uploads/` com owner `www-data`
- [ ] Nginx testado (`nginx -t`) e recarregado
- [ ] Serviço systemd ativo (`systemctl status controle_ativos`)
- [ ] Healthcheck respondendo (`/health` retorna `{"ok": true}`)
- [ ] Certificado TLS configurado e `SESSION_COOKIE_SECURE=1` validado

## Checklist pós-deploy

- [ ] Login funcional com usuário real
- [ ] CRUD de ativos funcionando
- [ ] Upload de documento funcionando
- [ ] Download de documento funcionando (apenas via rota autenticada)
- [ ] Export CSV/XLSX/PDF funcionando
- [ ] Logs sem erros críticos
- [ ] Acesso direto a `/static/uploads/` retorna 403 (Nginx bloqueando)
