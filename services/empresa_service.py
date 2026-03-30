# services/empresa_service.py

# Serviço responsável por consultar as empresas cadastradas no sistema.
# Nesta primeira versão, ele será usado principalmente no cadastro de usuários
# e em futuras telas administrativas.

# Importa o cursor padronizado de acesso ao MySQL.
from database.connection import cursor_mysql


class EmpresaService:
    """
    Serviço de consulta de empresas.
    """

    def listar_empresas_ativas(self) -> list[dict]:
        """
        Retorna todas as empresas ativas do sistema.

        Retorno:
        - lista de dicionários com id, nome e código da empresa.
        """
        with cursor_mysql(dictionary=True) as (_conn, cur):
            cur.execute(
                """
                SELECT id, nome, codigo
                FROM empresas
                WHERE ativa = 1
                ORDER BY nome
                """
            )
            return cur.fetchall()

    def obter_empresa_ativa_por_id(self, empresa_id: int) -> dict | None:
        """
        Busca uma empresa ativa pelo ID.

        Parâmetros:
        - empresa_id: identificador da empresa.

        Retorno:
        - dicionário da empresa, se existir
        - None, se não existir ou estiver inativa
        """
        with cursor_mysql(dictionary=True) as (_conn, cur):
            cur.execute(
                """
                SELECT id, nome, codigo
                FROM empresas
                WHERE id = %s
                  AND ativa = 1
                """,
                (empresa_id,)
            )
            return cur.fetchone()