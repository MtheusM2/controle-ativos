# FASE B — Perfis e Permissões (Parte 2)

**Data:** 2026-04-10  
**Status:** Design + Proposta de Implementação  
**Prioridade:** Crítica

---

## 1. Ações do Sistema Mapeadas

### Autenticação e Sessão
| Ação | Endpoint | Método | Descrição |
|------|----------|--------|-----------|
| login_page | `/` ou `/login` | GET | Tela de login |
| login | `/login` | POST | Autenticação |
| register_page | `/register` ou `/cadastro` | GET | Tela de cadastro |
| register | `/register` | POST | Registrar novo usuário |
| recovery_page | `/recovery` ou `/recuperar-senha` | GET | Tela de recuperação |
| forgot_password | `/forgot-password` | POST | Solicitar reset de senha |
| logout | `/logout` | GET/POST | Encerrar sessão |
| session_info | `/session` | GET | Info de sessão (JSON) |

### Configurações do Usuário
| Ação | Endpoint | Método | Descrição |
|------|----------|--------|-----------|
| settings_page | `/configuracoes` | GET | Tela de configurações |
| update_profile | `/configuracoes/perfil` | POST | Atualizar nome/email |
| change_password | `/configuracoes/senha` | POST | Alterar senha |
| toggle_remember | `/configuracoes/lembrar-me` | POST | Ativar/desativar "lembrar-me" |

### Dashboard e Listagem
| Ação | Endpoint | Método | Descrição |
|------|----------|--------|-----------|
| dashboard | `/dashboard` | GET | Dashboard principal |
| list_ativos | `/ativos` | GET | Listar ativos (com filtro) |
| list_ativos_json | `/ativos/lista` | GET | JSON de ativos |

### CRUD de Ativos
| Ação | Endpoint | Método | Descrição |
|------|----------|--------|-----------|
| new_ativo_form | `/ativos/novo` | GET | Formulário de criação |
| create_ativo | `/ativos` | POST | Criar novo ativo |
| view_ativo_form | `/ativos/<id>/editar` | GET | Formulário de edição |
| view_ativo_details | `/ativos/<id>/detalhes` | GET | Visualizar detalhe |
| update_ativo | `/ativos/<id>` | PUT | Atualizar ativo |
| delete_ativo | `/ativos/<id>` ou `/ativos/remover/<id>` | DELETE/POST | Remover/inativar ativo |

### Gestão de Anexos
| Ação | Endpoint | Método | Descrição |
|------|----------|--------|-----------|
| upload_file | `/ativos/<id>/anexos` | POST | Fazer upload |
| list_files | `/ativos/<id>/anexos` | GET | Listar anexos |
| download_file | `/anexos/<arquivo_id>/download` | GET | Download de arquivo |
| delete_file | `/anexos/<arquivo_id>` | DELETE | Remover anexo |

### Exportação
| Ação | Endpoint | Método | Descrição |
|------|----------|--------|-----------|
| export_csv | `/ativos/export/csv` | GET | Exportar em CSV |
| export_xlsx | `/ativos/export/xlsx` | GET | Exportar em Excel |
| export_pdf | `/ativos/export/pdf` | GET | Exportar em PDF |
| export_generic | `/ativos/export/<formato>` | GET | Rota genérica |

### Importação (Admin)
| Ação | Endpoint | Método | Descrição |
|------|----------|--------|-----------|
| import_csv | `/ativos/import/csv` | POST | Importar de CSV |

---

## 2. Definição dos Perfis

### Perfis Propostos

#### 1. **admin** (Administrador Técnico)
- Acesso total ao sistema
- Gestão de usuários (criação, promoção, bloqueio)
- Acesso a todas as empresas
- Importação/exportação ilimitada
- Alteração de configurações do sistema
- Visualização de auditoria
- **Responsabilidade:** Ops / TI

#### 2. **gestor_unidade** (Gerente de Unidade)
- Acesso a ativos da sua empresa apenas
- Pode ver todos os ativos da empresa
- Pode criar/editar/remover ativos
- Pode exportar dados da empresa
- Pode visualizar relatórios simples
- NÃO pode ver ativos de outras empresas
- NÃO pode gerenciar outros usuários
- **Responsabilidade:** Gerente de Unidade / Filial

#### 3. **operador** (Operador de Ativos)
- Acesso a ativos da sua empresa
- Pode criar e editar ativos (básico)
- Pode upload/download de anexos
- Pode exportar ativos
- NÃO pode remover ativos (apenas inativar)
- NÃO pode editar alguns campos críticos
- **Responsabilidade:** Técnico de Ativos / Operacional

#### 4. **consulta** (Consultor / Auditoria)
- Acesso de somente leitura a ativos da empresa
- Pode visualizar detalhe
- Pode exportar para auditoria/relatório
- NÃO pode criar, editar ou remover
- NÃO pode fazer upload
- **Responsabilidade:** Auditor Interno / Compliance

#### 5. **usuario** (Compatibilidade com Parte 1)
- Mapeado como `operador` para compatibilidade
- Comportamento: igual ao `operador`
- Será descontinuado em Parte 3

---

## 3. Matriz de Permissões

### Legenda
- ✅ Permitido
- ❌ Negado
- 🔒 Apenas sua empresa
- 🌐 Todas as empresas

### Autenticação e Sessão
| Ação | admin | gestor_unidade | operador | consulta |
|------|-------|-----------------|----------|----------|
| Login | ✅ | ✅ | ✅ | ✅ |
| Logout | ✅ | ✅ | ✅ | ✅ |
| Alterar senha própria | ✅ | ✅ | ✅ | ✅ |
| Registrar novo usuário | ✅ | ❌ | ❌ | ❌ |
| Recuperar senha | ✅ | ✅ | ✅ | ✅ |

### Dashboard e Listagem
| Ação | admin | gestor_unidade | operador | consulta |
|------|-------|-----------------|----------|----------|
| Dashboard | ✅ | ✅ | ✅ | ✅ |
| Listar ativos | 🌐 | 🔒 | 🔒 | 🔒 |
| Filtrar ativos | 🌐 | 🔒 | 🔒 | 🔒 |

### CRUD de Ativos
| Ação | admin | gestor_unidade | operador | consulta |
|------|-------|-----------------|----------|----------|
| Criar ativo | 🌐 | 🔒 | 🔒 | ❌ |
| Visualizar detalhe | 🌐 | 🔒 | 🔒 | 🔒 |
| Editar ativo | 🌐 | 🔒 | 🔒 (básico) | ❌ |
| Remover ativo | 🌐 | 🔒 | ❌ | ❌ |
| Inativar ativo | 🌐 | 🔒 | 🔒 | ❌ |

### Gestão de Anexos
| Ação | admin | gestor_unidade | operador | consulta |
|------|-------|-----------------|----------|----------|
| Upload de anexo | 🌐 | 🔒 | 🔒 | ❌ |
| Download de anexo | 🌐 | 🔒 | 🔒 | 🔒 |
| Remover anexo | 🌐 | 🔒 | 🔒 | ❌ |

### Exportação
| Ação | admin | gestor_unidade | operador | consulta |
|------|-------|-----------------|----------|----------|
| Exportar CSV | 🌐 | 🔒 | 🔒 | 🔒 |
| Exportar XLSX | 🌐 | 🔒 | 🔒 | 🔒 |
| Exportar PDF | 🌐 | 🔒 | 🔒 | 🔒 |

### Importação e Admin
| Ação | admin | gestor_unidade | operador | consulta |
|------|-------|-----------------|----------|----------|
| Importar CSV | ✅ | ❌ | ❌ | ❌ |
| Visualizar auditoria | ✅ | ❌ | ❌ | ❌ |
| Gerenciar usuários | ✅ | ❌ | ❌ | ❌ |

---

## 4. Regras de Negócio por Perfil

### Edição de Campos

#### operador pode editar:
- tipo, marca, modelo
- departamento
- nota_fiscal, garantia
- usuario_responsavel (apenas se status = "Em Uso")
- data_entrada, data_saida
- status (com validações)

#### operador NÃO pode editar:
- empresa_id (criado por admin)
- criado_por (histórico)
- criado_em, atualizado_em (timestamps)

#### gestor_unidade pode editar:
- Todos os campos acima
- ALÉM DISSO: Pode promover `usuario` → `operador` dentro da empresa

#### admin pode editar:
- Tudo
- Inclui: empresa_id, criado_por, qualquer campo

---

## 5. Estratégia de Implementação

### Abordagem Incremental e Segura

#### Fase 5.1: Camada de Service (não toca rotas)
1. Criar classe `Permission` (enum com os 4 perfis)
2. Adicionar método `pode_acessar()` em cada service
3. Método retorna boolean + mensagem de erro
4. **Exemplo:**
   ```python
   class AtivosService:
       def pode_ver_ativo(self, user_id: int, ativo_id: str, empresa_id: int) -> bool:
           # Admins veem tudo
           if self.eh_admin(user_id):
               return True
           # Não-admins só veem da própria empresa
           return user.empresa_id == empresa_id
   ```

#### Fase 5.2: Rotas (adiciona validação)
1. Manter rotas como estão
2. Adicionar chamada a `pode_acessar()` antes de operação crítica
3. Retornar 403 Forbidden se negado
4. **Nunca confiar em perfil sem validar em service**

#### Fase 5.3: Compatibilidade com Parte 1
1. Usuários existentes com `perfil='usuario'` → mapeados como `operador`
2. Sem migração de banco necessária (suportar ambos os valores)
3. Transição gradual possível

### Arquitetura de Segurança

```
Rota HTTP
   ↓
[Autenticação da sessão]
   ↓
Service.pode_acessar() ← FONTE DE VERDADE
   ↓
[Lógica de negócio]
   ↓
Resposta (200 ou 403)
```

**Princípio:** Nunca confiar na sessão ou no frontend para decisões de segurança.

---

## 6. Arquivos que Serão Alterados

### Novos arquivos:
1. `utils/permissions.py` — Definição de perfis e permissões

### Arquivos modificados:
1. `models/usuario.py` — Validar valores de `perfil`
2. `services/auth_service.py` — Métodos para checar perfis
3. `services/ativos_service.py` — Métodos `pode_ver()`, `pode_editar()`, etc
4. `services/ativos_arquivo_service.py` — Métodos `pode_fazer_upload()`, etc
5. `web_app/routes/auth_routes.py` — Retornar erro 403 em acesso negado
6. `web_app/routes/ativos_routes.py` — Retornar erro 403 em acesso negado
7. `database/schema.sql` — NENHUMA alteração (backward compatible)
8. Testes: `tests/test_permissions.py` — Novo arquivo de testes

### NÃO serão alterados:
- Tabela `usuarios` (coluna `perfil` já existe)
- Migração (não necessária)
- Configuração global (suporta valores antigos)

---

## 7. Impactos no Sistema

### ✅ Benefícios
1. **Segurança:** Isolamento real de dados por empresa + perfil
2. **Governança:** Papéis bem definidos
3. **Auditoria:** Cada ação registra quem fez e se tinha permissão
4. **Compatibilidade:** Sem quebra com Parte 1

### ⚠️ Impactos Operacionais
1. **Usuários existentes:**
   - `perfil='usuario'` → comportamento como `operador` (compatível)
   - Sem ação necessária no banco
   - Transição transparente

2. **Novas funcionalidades:**
   - Admin pode promover `usuario` → `operador` manualmente
   - Admin pode criar novo usuário com perfil específico
   - Sem auto-promoção (seguro)

3. **Performance:**
   - Validação adicional: O(1) por requisição (negligível)
   - Nenhum join ou query adicional

### ⚠️ Impactos em Testes
1. Novos testes de permissões (30-40 casos)
2. Testes existentes podem precisar de override de perfil
3. Tempo de execução: +3-5 segundos (marginal)

---

## 8. Implementação Inicial (Sprint 2.1)

### O que será feito NESTA sprint:
1. ✅ Criar `utils/permissions.py` com definições
2. ✅ Atualizar `services/auth_service.py` com métodos de check
3. ✅ Atualizar `services/ativos_service.py` com validações
4. ✅ Adicionar 3-4 validações críticas em rotas (criação, exclusão, exportação)
5. ✅ Testes unitários básicos (10-15 testes)

### O que fica para próxima sprint:
- Validação de campos editáveis por perfil (mais granular)
- Rate limiting por perfil
- Interface de promoção de usuário no dashboard

---

## 9. Próximos Passos

### Imediato
- [ ] Criar `utils/permissions.py`
- [ ] Implementar métodos em services
- [ ] Adicionar validações em rotas críticas
- [ ] Escrever testes

### Validação
- [ ] Opus valida matriz contra requisitos reais
- [ ] Vicente Martins aprova perfis propostos
- [ ] QA testa cada permissão com 4 perfis

### Documentação
- [ ] Criar `docs/USUARIOS_E_PERFIS.md` para usuários finais
- [ ] Documentar como promover usuário (admin)
- [ ] Exemplos de casos de uso

---

## 10. Veredito Técnico

✅ **Perfis e permissões são viáveis com baixo risco.**

**Arquitetura proposta:**
- Baixo acoplamento (validações em services, não em rotas)
- Backward compatible (suporta `usuario` como `operador`)
- Testável (permissões independentes de contexto)
- Escalável (fácil adicionar novos perfis depois)

**Critério de sucesso:**
- Todos os 4 perfis funcionam
- Testes passam com cobertura > 85%
- Nenhuma regressão em Parte 1

---

**Responsável:** Claude Code  
**Data:** 2026-04-10  
**Versão:** 1.0
