# Auditoria Completa da Suíte de Testes — controle-ativos

**Data:** 2026-04-17  
**Status da Suíte:** 175/188 testes passando (93%) — 13 falhas em auditoria (DB connectivity)

---

## PARTE 1 — INVENTÁRIO DOS TESTES EXISTENTES

### Resumo Geral
| Arquivo | Testes | Status | Observações |
|---------|--------|--------|-------------|
| test_app.py | 56 | ✓ Pass | Rotas web, regressões, templates |
| test_ativos_validacao.py | 25 | ✓ Pass | Validações, regras de negócio, datas, IMEI |
| test_permissions.py | 39 | ✓ Pass | Roles, ACL, permissões por ação |
| test_ativos_arquivo.py | 19 | ✓ Pass | Upload, tipos, validação de arquivo |
| test_csrf_hardening.py | 7 | ✓ Pass | CSRF, ordem de validação |
| test_auditoria.py | 16 | ✗ Fail | DB connectivity (sem mock) |
| **TOTAL** | **188** | **175 Pass** | **13 Fail** |

### Cobertura por Camada

#### 1. **Validadores (utils/validators.py)** — 25 testes
- ✓ Validação de tipo_ativo
- ✓ Regra "Em Uso exige responsável"
- ✓ Data entrada não futura
- ✓ Data compra ≤ data entrada
- ✓ Número de linha (10/11 ou 12/13 com DDI 55)
- ✓ IMEI com checksum Luhn (15 dígitos)
- ✓ Monitor simplificado (apenas polegadas)
- ✓ Serial e código interno (regex alfanumérico)
- ✓ Unidades/localização válidas (Opus Medical, Vicente Martins)
- ✓ Email format
- ⚠️ **LACUNA:** Não há testes para validação isolada de cada função de normalize (ex: normalizar_valor_monetario)
- ⚠️ **LACUNA:** Não há testes para campos ainda opcio

nais que podem quebrar (polegadas para monitor)

#### 2. **Services (services/ativos_service.py)** — 10+ testes
- ✓ Criar ativo com compatibilidade legado (tipo + departamento)
- ✓ Analisar movimentação (entrega, devolução, troca, transferência, manutenção)
- ✓ Movimentação não altera timestamp em atualizações técnicas
- ✓ Preencher responsável sugere "Em Uso"
- ✓ Preparar dados confirmação (sem exigir campos cadastrais)
- ⚠️ **LACUNA:** Não há testes de listagem com filtros complexos
- ⚠️ **LACUNA:** Não há testes de busca por ID (happy path + not found)
- ⚠️ **LACUNA:** Não há testes de deleção/inativação
- ⚠️ **LACUNA:** Não há testes de deduplicação
- ⚠️ **LACUNA:** Não há testes de erro em contexto de acesso

#### 3. **Rotas Web (web_app/routes/ativos_routes.py)** — 56 testes
- ✓ Healthcheck
- ✓ Dashboard autenticado
- ✓ Listagem (/ativos/lista)
- ✓ Novo ativo (/ativos/novo)
- ✓ Regressão: não encadear replaceAll em map()
- ✓ Regressão: não deixar Jinja raw em JavaScript
- ✓ Regressão: quick filters desativados
- ✓ Regressão: header sort bloqueado
- ⚠️ **LACUNA:** Não há testes de criação via POST
- ⚠️ **LACUNA:** Não há testes de edição (PUT)
- ⚠️ **LACUNA:** Não há testes de deleção (DELETE) além de CSRF
- ⚠️ **LACUNA:** Não há testes de filtros (status, setor, localizacao, etc)
- ⚠️ **LACUNA:** Não há testes de exportação (CSV, XLSX, PDF)
- ⚠️ **LACUNA:** Não há testes de importação de CSV
- ⚠️ **LACUNA:** Não há testes de paginação
- ⚠️ **LACUNA:** Não há testes de rota 404 quando ativo não existe

#### 4. **Permissões (utils/permissions.py)** — 39 testes
- ✓ Perfis: admin, operador, gestor, consulta
- ✓ Acesso a empresa (admin vê tudo, outros vêem só sua empresa)
- ✓ Criar ativo (admin, gestor, operador podem; consulta não)
- ✓ Remover ativo (admin, gestor podem; operador, consulta não)
- ✓ Inativar ativo (admin, gestor, operador podem; consulta não)
- ✓ Fazer upload (admin, gestor, operador podem; consulta não)
- ✓ Visualizar anexo (todos)
- ✓ Exportar (todos)
- ✓ Importar (apenas admin)
- ✓ Acessar auditoria (apenas admin)
- ✓ Promover usuários (apenas admin)
- ✓ Descrição de perfil
- ✓ Factory criar_usuario_contexto
- ✓ Normalização de perfil (adm → admin, usuario → operador)
- ⚠️ **LACUNA:** Não há testes para controle de acesso com multi-tenant (admin de empresa A não pode ver empresa B se houver isolamento)

#### 5. **Anexos (services/ativos_arquivo_service.py)** — 19 testes
- ✓ Validação de arquivo (obrigatório, nome, extensão, tamanho, mimetype)
- ✓ Arquivo vazio rejeitado
- ✓ Arquivo > 10 MB rejeitado
- ✓ Tipo de documento (nota_fiscal, garantia, outro)
- ✓ Tipo de documento inválido
- ✓ Case insensitive e trim
- ✓ Rota de upload (com e sem autenticação)
- ⚠️ **LACUNA:** Não há testes de listagem de arquivos por ativo
- ⚠️ **LACUNA:** Não há testes de download/obtenção
- ⚠️ **LACUNA:** Não há testes de remoção
- ⚠️ **LACUNA:** Não há testes com diferentes backends de storage (S3 vs local)

#### 6. **Auditoria (services/auditoria_service.py)** — 16 testes (FALHANDO)
- ✗ Todos falhando por DB connectivity (conftest.py não faz mock)
- ✓ Testes bem estruturados, apenas precisam de mock

#### 7. **CSRF Hardening** — 7 testes
- ✓ DELETE sem token CSRF → 403
- ✓ POST /ativos/import/csv sem token → 403
- ✓ POST /ativos/<id>/movimentacao/confirmar sem token → 403
- ✓ DELETE com token válido → sucesso (200/404, não 403)
- ✓ POST /ativos/<id>/movimentacao/preview sem token → 403
- ✓ POST sem login → 401 antes de 403 (ordem de validação)
- ✓ POST com login + CSRF válido → 200

---

## PARTE 2 — ANÁLISE DE LACUNAS CRÍTICAS

### A. Lacunas de Cobertura por Criticidade

#### CRÍTICA (Bloqueia validação estrutural)
1. **Criar Ativo (POST /ativos)** — sem testes de rota
   - Criar com dados mínimos
   - Criar com dados completos
   - Criar com validação fallida
   - Criar duplicado (deduplicação não testada)
   - Resposta HTTP e payload

2. **Editar Ativo (PUT /ativos/<id>)** — sem testes de rota
   - Editar com mudança de status
   - Editar com mudança de responsável
   - Editar com dados inválidos
   - Editar ativo inexistente (404)
   - Movimentação deve ser registrada corretamente

3. **Deletar Ativo (DELETE /ativos/<id>)** — sem testes de sucesso
   - DELETE com sucesso
   - DELETE ativo inexistente
   - Apenas CSRF validado, lógica de deleção não

4. **Listagem com Filtros** — sem testes
   - Filtro por status
   - Filtro por setor
   - Filtro por localização
   - Filtro por tipo
   - Filtro por responsável
   - Múltiplos filtros combinados
   - Paginação

5. **Exportação** — sem testes
   - Exportar para CSV
   - Exportar para XLSX
   - Exportar para PDF
   - Exportar com filtros aplicados

6. **Importação** — sem testes
   - Importar CSV válido
   - Importar com dados inválidos
   - Importar com duplicatas
   - Resposta de sucesso/erro

#### ALTA (Falhas afetam fluxos importantes)
7. **Auditoria** — 16 testes falhando
   - Todos os testes estão corretos, apenas precisam de mock do banco

8. **Rota 404** — sem teste
   - GET /ativos/<id> inexistente deve retornar 404

9. **Controle de Acesso em Listagem** — não testado
   - Usuário comum vê apenas ativos de sua empresa
   - Admin vê ativos de todas as empresas

10. **Attachments Full Cycle** — parcialmente testado
    - Upload testado
    - Listagem não testada
    - Download não testado
    - Remoção não testada

#### MÉDIA (Falhas pontuais)
11. **Normalização de Campos** — sem testes isolados
    - normalizar_valor_monetario
    - Tratamentos de trim/case/spaces
    - Conversão de formatos legados

12. **Integração Rota → Service** — parcialmente testada
    - Payloads são convertidos corretamente?
    - Erros de service são traduzidos para HTTP?
    - Mensagens de sucesso/erro estão corretas?

13. **Movimentação** — lógica bem testada em service, mas não em rota

---

## PARTE 3 — ESTRATÉGIA DE COBERTURA INCREMENTAL

### Prioridade 1: Testes de CRUD Completo (10-15 testes)
- [x] Criar (já parcialmente testado em validação)
- [ ] Ler/Buscar por ID
- [ ] Listar com filtros básicos
- [ ] Editar (status, responsável, dados técnicos)
- [ ] Deletar (com deleção real no service)

### Prioridade 2: Rotas com Dados Dinâmicos (8-10 testes)
- [ ] POST /ativos (rota completa)
- [ ] PUT /ativos/<id> (rota completa)
- [ ] GET /ativos/<id> (sucesso + 404)
- [ ] DELETE /ativos/<id> (além de CSRF, o sucesso real)
- [ ] GET /ativos/lista com query params

### Prioridade 3: Filtros e Busca (6-8 testes)
- [ ] Filtro por status
- [ ] Filtro por setor
- [ ] Filtro por localização
- [ ] Filtro por tipo
- [ ] Filtro por responsável
- [ ] Múltiplos filtros
- [ ] Paginação (limit + offset)

### Prioridade 4: Exportação/Importação (6-8 testes)
- [ ] Exportar CSV
- [ ] Exportar XLSX
- [ ] Exportar PDF
- [ ] Importar CSV
- [ ] Validação de importação

### Prioridade 5: Auditoria (Fix + 0 novos)
- [ ] Mock do banco para testes existentes (já bem estruturados)

### Prioridade 6: Integração Completa (4-6 testes)
- [ ] Attachments: upload → list → download → remove
- [ ] Movimentação: preview → confirmar
- [ ] Controle de acesso multi-empresa

---

## Arquivos Identificados para Refatoração/Ampliação

| Arquivo | Ação | Impacto |
|---------|------|--------|
| tests/test_app.py | Adicionar testes POST/PUT/DELETE de rota | Alto |
| tests/test_ativos_validacao.py | Adicionar testes de normalize | Médio |
| tests/test_auditoria.py | Adicionar mock de DB | Médio |
| tests/conftest.py | Melhorar fake services | Médio |
| web_app/routes/ativos_routes.py | Documentar contrato de erro/sucesso | Informativo |

---

## Próximos Passos

1. ✓ **PARTE 1:** Inventário concluído
2. → **PARTE 2:** Lacunas analisadas (este documento)
3. → **PARTE 3:** Estratégia definida acima
4. → **PARTE 4:** Implementar testes conforme prioridade
5. → **PARTE 5:** Validação final
6. → **PARTE 6:** Relatório consolidado + instruções de commit
