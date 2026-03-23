class Ativo:
    """
    Classe responsável por representar um ativo.
    """

    def __init__(
        self,
        id_ativo,
        tipo,
        marca,
        modelo,
        usuario,
        departamento,
        status,
        criado_por=None
    ):
        self.id_ativo = id_ativo
        self.tipo = tipo
        self.marca = marca
        self.modelo = modelo
        self.usuario = usuario
        self.departamento = departamento
        self.status = status
        self.criado_por = criado_por