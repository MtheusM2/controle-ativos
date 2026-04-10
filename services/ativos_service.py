# services/ativos_service.py

# Serviço de ativos com regra corporativa de escopo.
# Nesta etapa:
# - usuario comum vê somente ativos da própria empresa
# - adm vê ativos de todas as empresas
# - criado_por deixa de ser regra de acesso e passa a ser campo de auditoria

from models.ativos import Ativo
from database.connection import cursor_mysql
from utils.validators import (
    STATUS_VALIDOS,
    validar_ativo,
    validar_id_ativo,
    padronizar_texto,
    validar_data_iso_opcional
)


class AtivoErro(Exception):
    """
    Erro base relacionado a ativos.
    """
    pass


class AtivoJaExiste(AtivoErro):
    """
    Erro para ativo duplicado.
    """
    pass


class AtivoNaoEncontrado(AtivoErro):
    """
    Erro para ativo inexistente.
    """
    pass


class PermissaoNegada(AtivoErro):
    """
    Erro para acesso não autorizado.
    """
    pass


def _row_para_ativo(row: dict) -> Ativo:
    """
    Converte uma linha do banco em objeto Ativo.
    """
    return Ativo(
        id_ativo=row["id"],
        tipo=row["tipo"],
        marca=row["marca"],
        modelo=row["modelo"],
        usuario_responsavel=row["usuario_responsavel"],
        departamento=row["departamento"],
        nota_fiscal=row.get("nota_fiscal"),
        # Faz o mapeamento da coluna documental renomeada para o domínio.
        garantia=row.get("garantia"),
        status=row["status"],
        data_entrada=str(row["data_entrada"]),
        data_saida=str(row["data_saida"]) if row["data_saida"] else None,
        criado_por=row["criado_por"]
    )


def _normalizar_responsavel(usuario_responsavel: str | None) -> str | None:
    """
    Normaliza o responsável do ativo.
    """
    valor = (usuario_responsavel or "").strip()

    if not valor:
        return None

    return padronizar_texto(valor, "title")


def _normalizar_documento(valor: str | None) -> str | None:
    """
    Normaliza campos documentais como nota fiscal e garantia.
    Não força title/upper para evitar deformar códigos e números.
    """
    valor = (valor or "").strip()

    if not valor:
        return None

    return valor


def _padronizar_ativo(ativo: Ativo) -> Ativo:
    """
    Padroniza campos textuais do ativo antes da persistência.
    """
    return Ativo(
        id_ativo=(ativo.id_ativo or "").strip(),
        tipo=padronizar_texto(ativo.tipo, "title"),
        marca=padronizar_texto(ativo.marca, "title"),
        modelo=padronizar_texto(ativo.modelo, "upper"),
        usuario_responsavel=_normalizar_responsavel(ativo.usuario_responsavel),
        departamento=padronizar_texto(ativo.departamento, "title"),
        nota_fiscal=_normalizar_documento(ativo.nota_fiscal),
        # Preserva a normalização documental para a garantia.
        garantia=_normalizar_documento(ativo.garantia),
        status=padronizar_texto(ativo.status, "title"),
        data_entrada=(ativo.data_entrada or "").strip(),
        data_saida=(ativo.data_saida or "").strip() or None,
        criado_por=ativo.criado_por
    )


class AtivosService:
    """
    Serviço responsável pelas regras de negócio e persistência dos ativos.
    """

    def _obter_contexto_acesso(self, user_id: int) -> dict:
        """
        Busca o perfil e a empresa do usuário autenticado.
        """
        with cursor_mysql(dictionary=True) as (_conn, cur):
            cur.execute(
                """
                SELECT u.id, u.perfil, u.empresa_id, e.nome AS empresa_nome
                FROM usuarios u
                INNER JOIN empresas e
                    ON e.id = u.empresa_id
                WHERE u.id = %s
                  AND e.ativa = 1
                """,
                (user_id,)
            )
            row = cur.fetchone()

        if row is None:
            raise PermissaoNegada("Usuário inválido ou sem empresa ativa.")

        return row

    def _usuario_eh_admin(self, contexto: dict) -> bool:
        """
        Indica se o usuário possui perfil administrativo.
        """
        # Aceita perfis administrativo legado e novo para evolucao sem quebra.
        return (contexto.get("perfil") or "").strip().lower() in {"adm", "admin"}

    def _gerar_id_sequencial(self, empresa_id: int, conn, cur) -> str:
        """
        Gera o próximo ID de ativo para a empresa de forma transacionalmente segura.
        Usa SELECT FOR UPDATE na tabela sequencias_ativo para evitar colisão em
        ambientes com requisições concorrentes.

        Deve ser chamado dentro do bloco 'with cursor_mysql()' do chamador —
        o commit e rollback são controlados pelo context manager externo.
        """
        # Obtém o prefixo configurado para a empresa
        cur.execute(
            "SELECT prefixo_ativo FROM empresas WHERE id = %s AND ativa = 1",
            (empresa_id,)
        )
        row = cur.fetchone()
        if row is None or not (row.get("prefixo_ativo") or "").strip():
            raise AtivoErro(
                "Empresa sem prefixo de ativo configurado. "
                "Configure o campo prefixo_ativo na tabela empresas e "
                "adicione a linha correspondente em sequencias_ativo."
            )
        prefixo = row["prefixo_ativo"].strip().upper()

        # Trava a linha para esta empresa — impede leitura concorrente do mesmo número
        cur.execute(
            "SELECT proximo_numero FROM sequencias_ativo "
            "WHERE empresa_id = %s FOR UPDATE",
            (empresa_id,)
        )
        seq_row = cur.fetchone()
        if seq_row is None:
            raise AtivoErro(
                "Sequência de ativo não inicializada para esta empresa. "
                "Execute a migration 005 ou insira a linha manualmente em sequencias_ativo."
            )

        numero = seq_row["proximo_numero"]

        # Incrementa o contador — será commitado junto com o INSERT do ativo
        cur.execute(
            "UPDATE sequencias_ativo "
            "SET proximo_numero = proximo_numero + 1, updated_at = NOW() "
            "WHERE empresa_id = %s",
            (empresa_id,)
        )

        # Formato: PREFIX-000001 (6 dígitos com zero-padding, compatível com VARCHAR(20))
        return f"{prefixo}-{numero:06d}"

    def criar_ativo(self, ativo: Ativo, user_id: int) -> str:
        """
        Cria novo ativo. O ID é gerado automaticamente pelo backend via
        sequência por empresa — o usuário não define o ID.

        Retorna o ID gerado (str) para que a rota possa buscar o ativo recém-criado.

        Permissões: admin, gestor_unidade, operador (não: consulta)
        """
        contexto = self._obter_contexto_acesso(user_id)
        empresa_id = int(contexto["empresa_id"])
        perfil = contexto.get("perfil", "").strip().lower()

        # Validação de permissão: apenas usuários que podem criar (não consulta)
        if perfil not in {"admin", "adm", "gestor_unidade", "operador", "usuario"}:
            raise PermissaoNegada(f"Perfil '{perfil}' não tem permissão para criar ativos.")

        ativo.criado_por = user_id
        ativo_norm = _padronizar_ativo(ativo)

        try:
            # validar_id=False pois o ID ainda não foi gerado neste ponto
            validar_ativo(ativo_norm, validar_id=False)
        except ValueError as erro:
            raise AtivoErro(str(erro))

        with cursor_mysql(dictionary=True) as (conn, cur):
            # Gera o ID dentro da mesma transação do INSERT — atomicidade garantida.
            # Se o INSERT falhar, o rollback automático desfaz também o incremento.
            id_gerado = self._gerar_id_sequencial(empresa_id, conn, cur)
            ativo_norm.id_ativo = id_gerado

            cur.execute(
                """
                INSERT INTO ativos (
                    id,
                    tipo,
                    marca,
                    modelo,
                    usuario_responsavel,
                    departamento,
                    nota_fiscal,
                    garantia,
                    status,
                    data_entrada,
                    data_saida,
                    criado_por,
                    empresa_id
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    ativo_norm.id_ativo,
                    ativo_norm.tipo,
                    ativo_norm.marca,
                    ativo_norm.modelo,
                    ativo_norm.usuario_responsavel,
                    ativo_norm.departamento,
                    ativo_norm.nota_fiscal,
                    ativo_norm.garantia,
                    ativo_norm.status,
                    ativo_norm.data_entrada,
                    ativo_norm.data_saida,
                    user_id,
                    empresa_id,
                )
            )

        return id_gerado

    def listar_ativos(self, user_id: int) -> list[Ativo]:
        """
        Lista ativos conforme o escopo do usuário:
        - usuario: apenas da própria empresa
        - adm: todos
        """
        contexto = self._obter_contexto_acesso(user_id)

        with cursor_mysql(dictionary=True) as (_conn, cur):
            if self._usuario_eh_admin(contexto):
                cur.execute(
                    """
                    SELECT id, tipo, marca, modelo, usuario_responsavel,
                              departamento, nota_fiscal, garantia, status,
                           data_entrada, data_saida, criado_por
                    FROM ativos
                    ORDER BY id
                    """
                )
            else:
                cur.execute(
                    """
                    SELECT id, tipo, marca, modelo, usuario_responsavel,
                              departamento, nota_fiscal, garantia, status,
                           data_entrada, data_saida, criado_por
                    FROM ativos
                    WHERE empresa_id = %s
                    ORDER BY id
                    """,
                    (int(contexto["empresa_id"]),)
                )

            rows = cur.fetchall()

        return [_row_para_ativo(row) for row in rows]

    def buscar_ativo(self, id_ativo: str, user_id: int) -> Ativo:
        """
        Busca um ativo respeitando o escopo do usuário.

        Para usuários comuns, o filtro de empresa é aplicado diretamente no SQL
        para evitar que IDs de outras empresas sejam enumeráveis via mensagem de erro
        diferenciada (information disclosure em contexto multi-tenant).
        Admin acessa qualquer ativo sem restrição de empresa.
        """
        ok, msg = validar_id_ativo(id_ativo)
        if not ok:
            raise AtivoErro(msg)

        contexto = self._obter_contexto_acesso(user_id)

        with cursor_mysql(dictionary=True) as (_conn, cur):
            if self._usuario_eh_admin(contexto):
                # Admin: busca sem restrição de empresa.
                cur.execute(
                    """
                    SELECT id, tipo, marca, modelo, usuario_responsavel,
                          departamento, nota_fiscal, garantia, status,
                           data_entrada, data_saida, criado_por, empresa_id
                    FROM ativos
                    WHERE id = %s
                    """,
                    (id_ativo.strip(),)
                )
            else:
                # Usuário comum: restringe ao escopo da própria empresa no SQL.
                # Não diferencia "inexistente" de "pertence a outra empresa" para
                # evitar enumeração de IDs entre unidades.
                cur.execute(
                    """
                    SELECT id, tipo, marca, modelo, usuario_responsavel,
                          departamento, nota_fiscal, garantia, status,
                           data_entrada, data_saida, criado_por, empresa_id
                    FROM ativos
                    WHERE id = %s AND empresa_id = %s
                    """,
                    (id_ativo.strip(), int(contexto["empresa_id"]))
                )
            row = cur.fetchone()

        if row is None:
            raise AtivoNaoEncontrado("Ativo não encontrado.")

        return _row_para_ativo(row)

    def filtrar_ativos(
        self,
        user_id: int,
        filtros: dict,
        ordenar_por: str = "id",
        ordem: str = "asc"
    ) -> list[Ativo]:
        """
        Filtra ativos respeitando o escopo organizacional do usuário.
        """
        contexto = self._obter_contexto_acesso(user_id)

        campos_ordenacao = {
            "id": "id",
            "tipo": "tipo",
            "marca": "marca",
            "modelo": "modelo",
            "usuario_responsavel": "usuario_responsavel",
            "departamento": "departamento",
            "nota_fiscal": "nota_fiscal",
            # Permite ordenação pelo campo renomeado garantia.
            "garantia": "garantia",
            "status": "status",
            "data_entrada": "data_entrada",
            "data_saida": "data_saida"
        }

        if ordenar_por not in campos_ordenacao:
            raise AtivoErro("Campo de ordenação inválido.")

        ordem_sql = "ASC" if ordem.lower() == "asc" else "DESC"

        where = ["1 = 1"]
        params = []

        if not self._usuario_eh_admin(contexto):
            where.append("empresa_id = %s")
            params.append(int(contexto["empresa_id"]))

        if filtros.get("id_ativo"):
            where.append("id = %s")
            params.append(filtros["id_ativo"].strip())

        # Suporta filtros textuais diretos da nova experiência da listagem.
        if filtros.get("tipo"):
            where.append("tipo LIKE %s")
            params.append(f"%{filtros['tipo'].strip()}%")

        if filtros.get("marca"):
            where.append("marca LIKE %s")
            params.append(f"%{filtros['marca'].strip()}%")

        if filtros.get("modelo"):
            where.append("modelo LIKE %s")
            params.append(f"%{filtros['modelo'].strip()}%")

        if filtros.get("usuario_responsavel"):
            where.append("usuario_responsavel LIKE %s")
            params.append(f"%{filtros['usuario_responsavel'].strip()}%")

        if filtros.get("departamento"):
            where.append("departamento LIKE %s")
            params.append(f"%{filtros['departamento'].strip()}%")

        if filtros.get("nota_fiscal"):
            where.append("nota_fiscal LIKE %s")
            params.append(f"%{filtros['nota_fiscal'].strip()}%")

        if filtros.get("garantia"):
            where.append("garantia LIKE %s")
            params.append(f"%{filtros['garantia'].strip()}%")

        if filtros.get("status"):
            status = filtros["status"].strip().title()
            if status not in STATUS_VALIDOS:
                raise AtivoErro("Status inválido para filtro.")
            where.append("status = %s")
            params.append(status)

        for campo in [
            "data_entrada_inicial",
            "data_entrada_final",
            "data_saida_inicial",
            "data_saida_final"
        ]:
            valor = filtros.get(campo)
            ok, msg = validar_data_iso_opcional(valor)
            if not ok:
                raise AtivoErro(msg)

        if filtros.get("data_entrada_inicial"):
            where.append("data_entrada >= %s")
            params.append(filtros["data_entrada_inicial"].strip())

        if filtros.get("data_entrada_final"):
            where.append("data_entrada <= %s")
            params.append(filtros["data_entrada_final"].strip())

        if filtros.get("data_saida_inicial"):
            where.append("data_saida >= %s")
            params.append(filtros["data_saida_inicial"].strip())

        if filtros.get("data_saida_final"):
            where.append("data_saida <= %s")
            params.append(filtros["data_saida_final"].strip())

        sql = f"""
            SELECT id, tipo, marca, modelo, usuario_responsavel,
                     departamento, nota_fiscal, garantia, status,
                   data_entrada, data_saida, criado_por
            FROM ativos
            WHERE {" AND ".join(where)}
            ORDER BY {campos_ordenacao[ordenar_por]} {ordem_sql}
        """

        with cursor_mysql(dictionary=True) as (_conn, cur):
            cur.execute(sql, tuple(params))
            rows = cur.fetchall()

        return [_row_para_ativo(row) for row in rows]

    def atualizar_ativo(self, id_ativo: str, dados: dict, user_id: int) -> Ativo:
        """
        Atualiza um ativo existente dentro do escopo permitido.
        """
        atual = self.buscar_ativo(id_ativo=id_ativo, user_id=user_id)

        novo = Ativo(
            id_ativo=atual.id_ativo,
            tipo=dados.get("tipo", atual.tipo),
            marca=dados.get("marca", atual.marca),
            modelo=dados.get("modelo", atual.modelo),
            usuario_responsavel=dados.get("usuario_responsavel", atual.usuario_responsavel),
            departamento=dados.get("departamento", atual.departamento),
            nota_fiscal=dados.get("nota_fiscal", atual.nota_fiscal),
            # Atualiza com o campo documental renomeado garantia.
            garantia=dados.get("garantia", atual.garantia),
            status=dados.get("status", atual.status),
            data_entrada=dados.get("data_entrada", atual.data_entrada),
            data_saida=dados.get("data_saida", atual.data_saida),
            criado_por=atual.criado_por
        )

        novo_norm = _padronizar_ativo(novo)

        try:
            validar_ativo(novo_norm)
        except ValueError as erro:
            raise AtivoErro(str(erro))

        contexto = self._obter_contexto_acesso(user_id)

        with cursor_mysql(dictionary=True) as (_conn, cur):
            if self._usuario_eh_admin(contexto):
                cur.execute(
                    """
                    UPDATE ativos
                    SET tipo = %s,
                        marca = %s,
                        modelo = %s,
                        usuario_responsavel = %s,
                        departamento = %s,
                        nota_fiscal = %s,
                        garantia = %s,
                        status = %s,
                        data_entrada = %s,
                        data_saida = %s
                    WHERE id = %s
                    """,
                    (
                        novo_norm.tipo,
                        novo_norm.marca,
                        novo_norm.modelo,
                        novo_norm.usuario_responsavel,
                        novo_norm.departamento,
                        novo_norm.nota_fiscal,
                        novo_norm.garantia,
                        novo_norm.status,
                        novo_norm.data_entrada,
                        novo_norm.data_saida,
                        novo_norm.id_ativo
                    )
                )
            else:
                cur.execute(
                    """
                    UPDATE ativos
                    SET tipo = %s,
                        marca = %s,
                        modelo = %s,
                        usuario_responsavel = %s,
                        departamento = %s,
                        nota_fiscal = %s,
                        garantia = %s,
                        status = %s,
                        data_entrada = %s,
                        data_saida = %s
                    WHERE id = %s
                      AND empresa_id = %s
                    """,
                    (
                        novo_norm.tipo,
                        novo_norm.marca,
                        novo_norm.modelo,
                        novo_norm.usuario_responsavel,
                        novo_norm.departamento,
                        novo_norm.nota_fiscal,
                        novo_norm.garantia,
                        novo_norm.status,
                        novo_norm.data_entrada,
                        novo_norm.data_saida,
                        novo_norm.id_ativo,
                        int(contexto["empresa_id"])
                    )
                )

            if cur.rowcount == 0:
                raise AtivoNaoEncontrado("Não foi possível atualizar o ativo.")

        return novo_norm

    def remover_ativo(self, id_ativo: str, user_id: int) -> None:
        """
        Remove um ativo conforme o escopo do usuário autenticado.

        Permissões: admin, gestor_unidade (não: operador, consulta)
        """
        ok, msg = validar_id_ativo(id_ativo)
        if not ok:
            raise AtivoErro(msg)

        contexto = self._obter_contexto_acesso(user_id)
        perfil = contexto.get("perfil", "").strip().lower()

        # Validação de permissão: apenas admin e gestor podem remover
        if perfil not in {"admin", "adm", "gestor_unidade"}:
            raise PermissaoNegada(f"Perfil '{perfil}' não tem permissão para remover ativos.")

        with cursor_mysql(dictionary=True) as (_conn, cur):
            if self._usuario_eh_admin(contexto):
                cur.execute(
                    "DELETE FROM ativos WHERE id = %s",
                    (id_ativo.strip(),)
                )
            else:
                cur.execute(
                    "DELETE FROM ativos WHERE id = %s AND empresa_id = %s",
                    (id_ativo.strip(), int(contexto["empresa_id"]))
                )

            if cur.rowcount == 0:
                raise AtivoNaoEncontrado("Não foi possível remover o ativo.")