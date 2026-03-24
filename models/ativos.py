class Ativo:
    """
    Representa um ativo do sistema.
    """

    def __init__(
        self,
        id_ativo,
        tipo,
        marca,
        modelo,
        usuario_responsavel,
        departamento,
        status,
        data_entrada,
        data_saida=None,
        criado_por=None
    ):
        self.id_ativo = id_ativo
        self.tipo = tipo
        self.marca = marca
        self.modelo = modelo
        self.usuario_responsavel = usuario_responsavel
        self.departamento = departamento
        self.status = status
        self.data_entrada = data_entrada
        self.data_saida = data_saida
        self.criado_por = criado_por

    def to_dict(self):
        """
        Converte o objeto em dicionário.
        """
        return {
            "id_ativo": self.id_ativo,
            "tipo": self.tipo,
            "marca": self.marca,
            "modelo": self.modelo,
            "usuario_responsavel": self.usuario_responsavel,
            "departamento": self.departamento,
            "status": self.status,
            "data_entrada": self.data_entrada,
            "data_saida": self.data_saida,
            "criado_por": self.criado_por
        }