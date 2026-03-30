# models/usuario.py

# Classe de domínio do usuário autenticado.
# Agora o usuário carrega não apenas e-mail e hashes,
# mas também o contexto organizacional necessário
# para controle de acesso corporativo.


class Usuario:
    """
    Representa um usuário do sistema.
    """

    def __init__(
        self,
        id,
        email,
        senha_hash,
        pergunta_recuperacao,
        resposta_recuperacao_hash,
        perfil="usuario",
        empresa_id=None,
        empresa_nome=None
    ):
        # Identificador interno do usuário.
        self.id = id

        # E-mail de login do usuário.
        self.email = email

        # Hash da senha.
        self.senha_hash = senha_hash

        # Pergunta de recuperação cadastrada.
        self.pergunta_recuperacao = pergunta_recuperacao

        # Hash da resposta da recuperação.
        self.resposta_recuperacao_hash = resposta_recuperacao_hash

        # Perfil do usuário dentro do sistema.
        # Valores previstos:
        # - usuario
        # - adm
        self.perfil = perfil

        # Empresa principal à qual o usuário pertence.
        self.empresa_id = empresa_id

        # Nome da empresa para exibição na interface.
        self.empresa_nome = empresa_nome