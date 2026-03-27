# models/ativos.py

# Classe de domínio que representa um ativo dentro do sistema.
# Aqui mantemos apenas a estrutura do objeto e uma forma simples
# de converter para dicionário quando a camada web precisar renderizar HTML.


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
        usuario_responsavel=None,
        departamento=None,
        status=None,
        data_entrada=None,
        data_saida=None,
        criado_por=None
    ):
        # Identificador único do ativo no sistema.
        self.id_ativo = id_ativo

        # Tipo do ativo.
        self.tipo = tipo

        # Marca do ativo.
        self.marca = marca

        # Modelo do ativo.
        self.modelo = modelo

        # Responsável pelo ativo.
        # Agora este campo pode ser opcional, dependendo do status.
        self.usuario_responsavel = usuario_responsavel

        # Departamento relacionado ao ativo.
        self.departamento = departamento

        # Status atual do ativo.
        self.status = status

        # Data de entrada do ativo.
        self.data_entrada = data_entrada

        # Data de saída do ativo, quando existir.
        self.data_saida = data_saida

        # Usuário que criou o registro.
        self.criado_por = criado_por

    def to_dict(self):
        """
        Converte o objeto em dicionário.

        Observação:
        - campos opcionais são normalizados para string vazia
          quando necessário para facilitar renderização em templates HTML.
        """
        return {
            "id_ativo": self.id_ativo,
            "tipo": self.tipo,
            "marca": self.marca,
            "modelo": self.modelo,
            "usuario_responsavel": self.usuario_responsavel or "",
            "departamento": self.departamento,
            "status": self.status,
            "data_entrada": self.data_entrada,
            "data_saida": self.data_saida or "",
            "criado_por": self.criado_por
        }