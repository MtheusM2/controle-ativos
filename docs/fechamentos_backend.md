# Fechamentos do Backend

## Status atual

O backend HTTP principal do sistema ja cobre o fluxo de apresentacao:

- autenticacao com sessao
- cadastro de usuario
- recuperacao de senha por pergunta e resposta
- dashboard autenticado
- CRUD de ativos via JSON

Tambem existem servicos adicionais no projeto que ainda nao estao totalmente expostos na camada web:

- servico de empresas
- servico de anexos de ativos
- campos de seguranca no schema para bloqueio e reset por token

## Etapa 1 - Fechamento de ambiente

Objetivo: conseguir executar e validar a aplicacao localmente.

Itens:

- instalar um Python valido no Windows
- recriar a `.venv`
- reinstalar dependencias do `requirements.txt`
- validar se o `.env` esta preenchido
- subir o MySQL com o schema e migrations aplicados

Observacao:

- a `.venv` atual esta quebrada porque foi criada a partir de um Python do Windows Store que nao existe mais no sistema

## Etapa 2 - Fechamento do backend principal

Objetivo: consolidar o que sera demonstrado no TCC.

Itens:

- validar login, logout e protecao de sessao
- validar cadastro de usuario com empresa ativa
- validar recuperacao de senha
- validar CRUD de ativos ponta a ponta
- validar redirecionamentos e respostas JSON
- revisar mensagens de erro amigaveis

Status:

- esta etapa esta praticamente fechada no codigo
- ainda falta smoke test real no ambiente

## Etapa 3 - Fechamento documental do backend

Objetivo: deixar a documentacao coerente com o sistema real.

Itens:

- manter o `README.md` alinhado com as rotas atuais
- documentar o fluxo principal em `GET /`, `GET /dashboard` e `/ativos`
- documentar as variaveis de ambiente obrigatorias
- documentar o procedimento de inicializacao do banco

Status:

- `README.md` foi parcialmente alinhado com o estado atual

## Etapa 4 - Fechamento de seguranca funcional

Objetivo: usar no backend o que o schema ja promete.

Itens:

- aplicar controle de tentativas de login usando `tentativas_login_falhas`
- aplicar bloqueio temporario usando `bloqueado_ate`
- substituir recuperacao por pergunta/resposta por reset com token
- registrar auditoria de login, alteracao de senha e exclusao de ativo
- revisar expiracao e endurecimento da sessao

Status:

- o schema ja suporta parte disso
- a camada HTTP e os services ainda nao usam esses recursos

## Etapa 5 - Fechamento de anexos

Objetivo: expor na web os anexos de ativos ja suportados pelo service.

Itens:

- criar rotas de upload de anexo
- criar rota de download
- criar rota de remocao de anexo
- integrar a listagem de anexos no dashboard ou em tela dedicada
- validar tipo documental e permissao de acesso

Status:

- o `AtivosArquivoService` existe
- as rotas HTTP ainda nao estao fechadas no fluxo atual

## Etapa 6 - Fechamento de qualidade

Objetivo: deixar o backend confiavel para evolucao.

Itens:

- criar testes unitarios para validators e services
- criar testes de integracao para auth e ativos
- criar smoke tests das rotas principais
- revisar tratamento global de erros
- revisar logs tecnicos

Status:

- ainda nao existe pasta `tests/`

## Etapa 7 - Fechamento para evolucao empresarial

Objetivo: preparar a base para crescer sem retrabalho.

Itens:

- criar endpoints de dashboard com metricas reais
- expor filtros avancados no backend HTTP
- criar endpoints administrativos de empresa e perfil
- planejar API para multi-tenancy mais explicito
- planejar integracoes futuras

Status:

- a base de services e schema aponta nessa direcao
- a camada web ainda esta focada na demonstracao principal
