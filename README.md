# Sistema de Controle de Ativos

Projeto desenvolvido para gerenciamento de ativos com autenticação de usuários e integração com banco de dados MySQL.

## Funcionalidades

- Cadastro de usuários com autenticação segura
- Login e controle de sessão
- Recuperação de senha via pergunta de segurança
- Cadastro de ativos
- Listagem de ativos
- Busca por ativos
- Edição de ativos
- Remoção de ativos

## Tecnologias utilizadas

- Python
- MySQL
- Arquitetura modular (models, services, database, utils)

## Estrutura do projeto

controle_ativos/
│
├── database/
├── models/
├── services/
├── utils/
├── web/
├── .gitignore
└── main.py


## Como executar o projeto

### 1. Instalar dependências

```bash
pip install mysql-connector-python

Configurar variáveis de ambiente
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=sua_senha
DB_NAME=controle_ativos
APP_PEPPER=segredo_extra

Criar banco e tabelas
python -m database.init_db
```
Executar o sistema

python main.py

Observações

Este projeto foi desenvolvido como parte de um trabalho acadêmico (TCC), com foco em boas práticas de organização, autenticação e persistência de dados.

Autor

Matheus Santos do Nascimento
