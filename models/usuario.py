class Usuario:
    """
    Classe responsável por representar um usuário do sistema.
    """

    def __init__(
        self,
        id,
        email,
        senha_hash,
        pergunta_recuperacao,
        resposta_recuperacao_hash
    ):
        self.id = id
        self.email = email
        self.senha_hash = senha_hash
        self.pergunta_recuperacao = pergunta_recuperacao
        self.resposta_recuperacao_hash = resposta_recuperacao_hash