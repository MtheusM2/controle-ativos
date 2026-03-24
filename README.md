# Sistema de Controle de Ativos

Sistema de controle de ativos desenvolvido em **Python**, com arquitetura modular, autenticação de usuários e integração com **MySQL**.

O projeto foi estruturado para permitir evolução progressiva do backend, melhoria de segurança, organização em camadas e futura integração com interface web em **Flask**.

---

## Objetivo do projeto

Este sistema tem como finalidade gerenciar ativos corporativos, permitindo:

- cadastro de usuários
- autenticação com login e senha
- recuperação de senha com pergunta de segurança
- cadastro de ativos
- edição de ativos
- remoção de ativos
- listagem e filtragem de ativos
- persistência em banco de dados MySQL

---

## Tecnologias utilizadas

- **Python 3**
- **MySQL**
- **Flask**
- **mysql-connector-python**
- **python-dotenv**

---

## Estrutura do projeto

```text
controle_ativos/
├── database/
│   ├── connection.py
│   ├── init_db.py
│   └── schema.sql
│
├── models/
│   ├── ativos.py
│   └── usuario.py
│
├── services/
│   ├── ativos_service.py
│   └── auth_service.py
│
├── utils/
│   ├── crypto.py
│   └── validators.py
│
├── web/
│   └── sistema_ativos.py
│
├── app.py
├── main.py
├── .gitignore
├── .env
└── README.md


Arquitetura do sistema

O projeto segue uma estrutura modular separada por responsabilidades:

models/: representa as entidades do sistema
services/: concentra a lógica de negócio
database/: gerencia conexão e estrutura do banco
utils/: contém funções auxiliares, validações e segurança
web/: camada de interface e evolução futura para integração web
main.py: ponto de entrada da aplicação CLI
app.py: base para evolução da aplicação web com Flask
Funcionalidades implementadas
Autenticação
cadastro de usuário
login
recuperação de senha
validação de email
hash de senha
hash de resposta de segurança
Ativos
cadastro de ativo
edição de ativo
exclusão de ativo
listagem de ativos
filtros por critérios
controle de status
associação do ativo ao usuário criador
Regras de negócio principais
cada ativo possui identificador único
o status do ativo deve respeitar valores válidos
o ativo pode possuir:
responsável
departamento
data de entrada
data de saída
regras de validação são centralizadas
o sistema restringe operações conforme o usuário autenticado
Pré-requisitos

Antes de executar o projeto, você precisa ter instalado:

Python 3.11 ou superior
MySQL Server
Git
ambiente virtual Python (venv)
Como clonar o projeto
git clone https://github.com/MtheusM2/controle-ativos.git
cd controle-ativos
Como criar e ativar o ambiente virtual
Windows PowerShell
python -m venv .venv
.venv\Scripts\Activate.ps1
Windows CMD
python -m venv .venv
.venv\Scripts\activate.bat
Como instalar as dependências
pip install mysql-connector-python
pip install python-dotenv
pip install flask

Ou, se estiver usando requirements.txt:

pip install -r requirements.txt
Configuração do ambiente

Crie um arquivo .env na raiz do projeto com o seguinte conteúdo:

DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=sua_senha_aqui
DB_NAME=controle_ativos
FLASK_SECRET_KEY=sua_chave_secreta
APP_PEPPER=seu_pepper

Importante: o arquivo .env não deve ser enviado para o GitHub.

Como criar o banco de dados

Garanta que o MySQL esteja em execução e depois execute o script de inicialização do banco:

python database/init_db.py

Esse script irá utilizar o arquivo schema.sql para criar a estrutura necessária.

Como executar o sistema CLI
python main.py
Como executar a aplicação Flask
python app.py
Status do projeto

Atualmente o sistema possui:

backend funcional
autenticação integrada
MySQL funcionando
validações centralizadas
estrutura modular organizada
base preparada para evolução web

Próximas evoluções planejadas:

padronização completa do backend
melhoria de UX no terminal
filtros avançados
tratamento de erros mais profissional
melhorias de segurança e LGPD
API REST
interface web completa
testes automatizados
documentação complementar
Segurança

O projeto adota algumas práticas de segurança, como:

hash de senha
hash de resposta de recuperação
uso de variáveis de ambiente
separação entre código e configuração sensível

Melhorias futuras previstas:

política de privacidade
controle de permissões mais refinado
fortalecimento das regras de acesso
revisão de exposição de dados sensíveis
Boas práticas adotadas
separação por camadas
centralização de validações
uso de serviços para regras de negócio
organização modular
versionamento com Git e GitHub
preparação para crescimento do sistema
Como contribuir
faça um fork do projeto
crie uma branch para sua funcionalidade
faça as alterações
envie um commit descritivo
abra um pull request
Autor

Desenvolvido por Matheus
Projeto com foco em evolução técnica, arquitetura modular e profissionalização do backend.

Licença

Este projeto está em desenvolvimento para fins educacionais e de evolução profissional.


---

# Como adicionar no projeto

## 1. Criar o arquivo
Na raiz do projeto, crie:

```text
README.md
2. Colar o conteúdo

Cole exatamente o texto acima.

3. Salvar

Salve o arquivo.

4. Subir para o GitHub

No terminal:

git add README.md
git commit -m "docs: adiciona README profissional do projeto"
git push
O que vai deixar ele ainda mais profissional

Eu recomendo também criar estes dois arquivos:

.env.example

Esse arquivo mostra a estrutura das variáveis sem expor seus segredos:

DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=sua_senha_aqui
DB_NAME=controle_ativos
FLASK_SECRET_KEY=sua_chave_secreta
APP_PEPPER=seu_pepper
requirements.txt

Se ainda não tiver, crie com:

flask
mysql-connector-python
python-dotenv

Assim, o README fica coerente com instalação por:

pip install -r requirements.txt