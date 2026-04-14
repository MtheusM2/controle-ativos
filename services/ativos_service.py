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



class AtivoJaExiste(AtivoErro):
    """
    Erro para ativo duplicado.
    """



class AtivoNaoEncontrado(AtivoErro):
    """
    Erro para ativo inexistente.
    """



class PermissaoNegada(AtivoErro):
    """
    Erro para acesso não autorizado.
    """



def _row_para_ativo(row: dict) -> Ativo:
    """
    Converte uma linha do banco em objeto Ativo.
    """
    return Ativo(
        id_ativo=row["id"],
        tipo=row["tipo"],
        marca=row["marca"],
        modelo=row["modelo"],
        serial=row.get("serial"),
        codigo_interno=row.get("codigo_interno"),
        descricao=row.get("descricao"),
        categoria=row.get("categoria"),
        tipo_ativo=row.get("tipo_ativo") or row.get("tipo"),
        condicao=row.get("condicao"),
        localizacao=row.get("localizacao"),
        setor=row.get("setor") or row.get("departamento"),
        usuario_responsavel=row["usuario_responsavel"],
        email_responsavel=row.get("email_responsavel"),
        departamento=row["departamento"],
        nota_fiscal=row.get("nota_fiscal"),
        # Faz o mapeamento da coluna documental renomeada para o domínio.
        garantia=row.get("garantia"),
        status=row["status"],
        data_entrada=str(row["data_entrada"]),
        data_saida=str(row["data_saida"]) if row["data_saida"] else None,
        data_compra=str(row["data_compra"]) if row.get("data_compra") else None,
        valor=str(row["valor"]) if row.get("valor") is not None else None,
        observacoes=row.get("observacoes"),
        detalhes_tecnicos=row.get("detalhes_tecnicos"),
        processador=row.get("processador"),
        ram=row.get("ram"),
        armazenamento=row.get("armazenamento"),
        sistema_operacional=row.get("sistema_operacional"),
        carregador=row.get("carregador"),
        teamviewer_id=row.get("teamviewer_id"),
        anydesk_id=row.get("anydesk_id"),
        nome_equipamento=row.get("nome_equipamento"),
        hostname=row.get("hostname"),
        imei_1=row.get("imei_1"),
        imei_2=row.get("imei_2"),
        numero_linha=row.get("numero_linha"),
        operadora=row.get("operadora"),
        conta_vinculada=row.get("conta_vinculada"),
        polegadas=row.get("polegadas"),
        resolucao=row.get("resolucao"),
        tipo_painel=row.get("tipo_painel"),
        entrada_video=row.get("entrada_video"),
        fonte_ou_cabo=row.get("fonte_ou_cabo"),
        created_at=row.get("created_at") or row.get("criado_em"),
        updated_at=row.get("updated_at") or row.get("atualizado_em"),
        data_ultima_movimentacao=row.get("data_ultima_movimentacao"),
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


def _normalizar_email(valor: str | None) -> str | None:
    """
    Normaliza e-mail para comparação e persistência estável.
    """
    valor = (valor or "").strip().lower()

    if not valor:
        return None

    return valor


def _padronizar_ativo(ativo: Ativo) -> Ativo:
    """
    Padroniza campos textuais do ativo antes da persistência.
    """
    # `tipo_ativo` é a autoridade de negócio no novo cadastro; `tipo` fica apenas como legado.
    tipo_ativo_normalizado = padronizar_texto(ativo.tipo_ativo or ativo.tipo, "title")
    # `descricao` pode receber fallback técnico apenas para fluxos legados/importações antigas.
    descricao_fallback = (
        _normalizar_documento(ativo.descricao)
        or _normalizar_documento(" ".join(part for part in [ativo.tipo, ativo.marca, ativo.modelo] if (part or "").strip()))
    )

    return Ativo(
        id_ativo=(ativo.id_ativo or "").strip(),
        tipo=tipo_ativo_normalizado,
        marca=padronizar_texto(ativo.marca, "title"),
        modelo=padronizar_texto(ativo.modelo, "upper"),
        serial=_normalizar_documento(ativo.serial),
        codigo_interno=_normalizar_documento(ativo.codigo_interno),
        # Mantém compatibilidade: caso não informado, usa descrição técnica mínima.
        descricao=descricao_fallback,
        # `setor` é o campo oficial; `departamento` entra apenas como compatibilidade legada.
        categoria=padronizar_texto(ativo.categoria or tipo_ativo_normalizado, "title"),
        tipo_ativo=tipo_ativo_normalizado,
        condicao=padronizar_texto(ativo.condicao, "title"),
        localizacao=padronizar_texto(ativo.localizacao, "title"),
        setor=padronizar_texto(ativo.setor or ativo.departamento, "title"),
        usuario_responsavel=_normalizar_responsavel(ativo.usuario_responsavel),
        email_responsavel=_normalizar_email(ativo.email_responsavel),
        departamento=padronizar_texto(ativo.setor or ativo.departamento, "title"),
        nota_fiscal=_normalizar_documento(ativo.nota_fiscal),
        # Preserva a normalização documental para a garantia.
        garantia=_normalizar_documento(ativo.garantia),
        status=padronizar_texto(ativo.status, "title"),
        data_entrada=(ativo.data_entrada or "").strip(),
        data_saida=(ativo.data_saida or "").strip() or None,
        data_compra=(ativo.data_compra or "").strip() or None,
        valor=_normalizar_documento(ativo.valor),
        observacoes=_normalizar_documento(ativo.observacoes),
        detalhes_tecnicos=_normalizar_documento(ativo.detalhes_tecnicos),
        processador=_normalizar_documento(ativo.processador),
        ram=_normalizar_documento(ativo.ram),
        armazenamento=_normalizar_documento(ativo.armazenamento),
        sistema_operacional=_normalizar_documento(ativo.sistema_operacional),
        carregador=_normalizar_documento(ativo.carregador),
        teamviewer_id=_normalizar_documento(ativo.teamviewer_id),
        anydesk_id=_normalizar_documento(ativo.anydesk_id),
        nome_equipamento=_normalizar_documento(ativo.nome_equipamento),
        hostname=_normalizar_documento(ativo.hostname),
        imei_1=_normalizar_documento(ativo.imei_1),
        imei_2=_normalizar_documento(ativo.imei_2),
        numero_linha=_normalizar_documento(ativo.numero_linha),
        operadora=padronizar_texto(ativo.operadora, "title"),
        conta_vinculada=_normalizar_documento(ativo.conta_vinculada),
        polegadas=_normalizar_documento(ativo.polegadas),
        resolucao=_normalizar_documento(ativo.resolucao),
        tipo_painel=_normalizar_documento(ativo.tipo_painel),
        entrada_video=_normalizar_documento(ativo.entrada_video),
        fonte_ou_cabo=_normalizar_documento(ativo.fonte_ou_cabo),
        created_at=getattr(ativo, "created_at", None),
        updated_at=getattr(ativo, "updated_at", None),
        data_ultima_movimentacao=getattr(ativo, "data_ultima_movimentacao", None),
        criado_por=ativo.criado_por
    )


# Rótulos legíveis para o resumo estruturado de movimentação.
CAMPO_ROTULOS_MOVIMENTACAO = {
    "status": "Status",
    "usuario_responsavel": "Responsável",
    "setor": "Setor",
    "localizacao": "Localização",
    "codigo_interno": "Código interno",
    "descricao": "Descrição",
    "categoria": "Categoria",
    "tipo_ativo": "Tipo de ativo",
    "condicao": "Condição",
    "marca": "Marca",
    "modelo": "Modelo",
    "serial": "Serial",
    "email_responsavel": "E-mail do responsável",
    "data_compra": "Data da compra",
    "data_entrada": "Data de entrada",
    "data_saida": "Data de saída",
    "valor": "Valor",
    "observacoes": "Observações",
    "detalhes_tecnicos": "Detalhes técnicos",
    "processador": "Processador",
    "ram": "RAM",
    "armazenamento": "Armazenamento",
    "sistema_operacional": "Sistema operacional",
    "carregador": "Carregador",
    "teamviewer_id": "TeamViewer ID",
    "anydesk_id": "AnyDesk ID",
    "nome_equipamento": "Nome do equipamento",
    "hostname": "Hostname",
    "imei_1": "IMEI 1",
    "imei_2": "IMEI 2",
    "numero_linha": "Número da linha",
    "operadora": "Operadora",
    "conta_vinculada": "Conta vinculada",
    "polegadas": "Polegadas",
    "resolucao": "Resolução",
    "tipo_painel": "Tipo de painel",
    "entrada_video": "Entrada de vídeo",
    "fonte_ou_cabo": "Fonte ou cabo",
}


# Campos que entram na comparação da edição e no contrato do modal futuro.
CAMPOS_ANALISE_MOVIMENTACAO = tuple(CAMPO_ROTULOS_MOVIMENTACAO.keys())


def _normalizar_valor_comparacao(valor) -> str:
    """
    Gera uma forma canônica do valor para evitar falsos positivos por espaço ou caixa.
    """
    return ("" if valor is None else str(valor)).strip().casefold()


def _valor_exibicao(valor) -> str:
    """
    Prepara um valor bruto para o resumo estruturado.
    """
    return ("" if valor is None else str(valor)).strip()


def _snapshot_movimentacao(ativo: Ativo) -> dict:
    """
    Captura os campos relevantes para comparação entre estados do ativo.
    """
    return {
        campo: _normalizar_valor_comparacao(getattr(ativo, campo, None))
        for campo in CAMPOS_ANALISE_MOVIMENTACAO
    }


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

    def analisar_movimentacao_ativo(self, atual: Ativo, novo: Ativo) -> dict:
        """
        Compara o estado anterior com o novo payload e monta um resumo pronto para a Fase 3.
        """
        snapshot_atual = _snapshot_movimentacao(atual)
        snapshot_novo = _snapshot_movimentacao(novo)

        campos_alterados = []
        for campo in CAMPOS_ANALISE_MOVIMENTACAO:
            if snapshot_atual[campo] == snapshot_novo[campo]:
                continue

            campos_alterados.append(
                {
                    "campo": campo,
                    "rotulo": CAMPO_ROTULOS_MOVIMENTACAO.get(campo, campo),
                    "antes": _valor_exibicao(getattr(atual, campo, None)),
                    "depois": _valor_exibicao(getattr(novo, campo, None)),
                    "relevante": campo in {"status", "usuario_responsavel", "setor", "localizacao"},
                }
            )

        status_atual = (atual.status or "").strip().title()
        status_novo = (novo.status or "").strip().title() or status_atual or "Disponível"
        responsavel_atual = (atual.usuario_responsavel or "").strip()
        responsavel_novo = (novo.usuario_responsavel or "").strip()

        tipo_movimentacao = "atualizacao_cadastral"
        descricao_movimentacao = "Atualização cadastral"
        status_sugerido = status_novo

        if status_atual == "Em Manutenção" and status_novo != "Em Manutenção":
            tipo_movimentacao = "retorno_de_manutencao"
            descricao_movimentacao = "Retorno de manutenção"
            status_sugerido = status_novo or "Disponível"
        elif status_novo == "Em Manutenção" and status_atual != "Em Manutenção":
            tipo_movimentacao = "envio_para_manutencao"
            descricao_movimentacao = "Envio para manutenção"
            status_sugerido = "Em Manutenção"
        elif not responsavel_atual and responsavel_novo:
            tipo_movimentacao = "entrega_para_colaborador"
            descricao_movimentacao = "Entrega para colaborador"
            status_sugerido = "Em Uso"
        elif responsavel_atual and not responsavel_novo:
            tipo_movimentacao = "devolucao_ao_estoque"
            descricao_movimentacao = "Devolução ao estoque"
            status_sugerido = "Disponível"
        elif responsavel_atual and responsavel_novo and responsavel_atual.casefold() != responsavel_novo.casefold():
            tipo_movimentacao = "troca_de_responsavel"
            descricao_movimentacao = "Troca de responsável"
            status_sugerido = "Em Uso"
        elif not responsavel_novo and (snapshot_atual["setor"] != snapshot_novo["setor"] or snapshot_atual["localizacao"] != snapshot_novo["localizacao"]):
            tipo_movimentacao = "transferencia_interna"
            descricao_movimentacao = "Transferência interna"
            status_sugerido = "Disponível"
        elif snapshot_atual["status"] != snapshot_novo["status"]:
            tipo_movimentacao = "alteracao_de_status"
            descricao_movimentacao = "Alteração de status"

        movimento_relevante = any(item["relevante"] for item in campos_alterados)

        return {
            "status_atual": status_atual,
            "status_sugerido": status_sugerido,
            "tipo_movimentacao": tipo_movimentacao,
            "descricao_movimentacao": descricao_movimentacao,
            "mudanca_relevante": movimento_relevante,
            "atualizar_data_ultima_movimentacao": movimento_relevante,
            "campos_alterados": campos_alterados,
            "estado_anterior": {
                "status": _valor_exibicao(atual.status),
                "usuario_responsavel": _valor_exibicao(atual.usuario_responsavel),
                "setor": _valor_exibicao(atual.setor or atual.departamento),
                "localizacao": _valor_exibicao(atual.localizacao),
            },
            "estado_novo": {
                "status": _valor_exibicao(novo.status),
                "usuario_responsavel": _valor_exibicao(novo.usuario_responsavel),
                "setor": _valor_exibicao(novo.setor or novo.departamento),
                "localizacao": _valor_exibicao(novo.localizacao),
            },
        }

    def _gerar_id_sequencial(self, empresa_id: int, _conn, cur) -> str:
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
            raise AtivoErro(str(erro)) from erro

        with cursor_mysql(dictionary=True) as (conn, cur):
            # Gera o ID dentro da mesma transação do INSERT — atomicidade garantida.
            # Se o INSERT falhar, o rollback automático desfaz também o incremento.
            id_gerado = self._gerar_id_sequencial(empresa_id, conn, cur)
            ativo_norm.id_ativo = id_gerado

            cur.execute(
                """
                INSERT INTO ativos (
                    id,
                    codigo_interno,
                    tipo,
                    marca,
                    modelo,
                    serial,
                    descricao,
                    categoria,
                    tipo_ativo,
                    condicao,
                    localizacao,
                    setor,
                    usuario_responsavel,
                    email_responsavel,
                    departamento,
                    nota_fiscal,
                    garantia,
                    status,
                    data_entrada,
                    data_saida,
                    data_compra,
                    valor,
                    observacoes,
                    detalhes_tecnicos,
                    processador,
                    ram,
                    armazenamento,
                    sistema_operacional,
                    carregador,
                    teamviewer_id,
                    anydesk_id,
                    nome_equipamento,
                    hostname,
                    imei_1,
                    imei_2,
                    numero_linha,
                    operadora,
                    conta_vinculada,
                    polegadas,
                    resolucao,
                    tipo_painel,
                    entrada_video,
                    fonte_ou_cabo,
                    criado_por,
                    empresa_id
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s
                )
                """,
                (
                    ativo_norm.id_ativo,
                    ativo_norm.codigo_interno,
                    ativo_norm.tipo,
                    ativo_norm.marca,
                    ativo_norm.modelo,
                    ativo_norm.serial,
                    ativo_norm.descricao,
                    ativo_norm.categoria,
                    ativo_norm.tipo_ativo,
                    ativo_norm.condicao,
                    ativo_norm.localizacao,
                    ativo_norm.setor,
                    ativo_norm.usuario_responsavel,
                    ativo_norm.email_responsavel,
                    ativo_norm.departamento,
                    ativo_norm.nota_fiscal,
                    ativo_norm.garantia,
                    ativo_norm.status,
                    ativo_norm.data_entrada,
                    ativo_norm.data_saida,
                    ativo_norm.data_compra,
                    ativo_norm.valor,
                    ativo_norm.observacoes,
                    ativo_norm.detalhes_tecnicos,
                    ativo_norm.processador,
                    ativo_norm.ram,
                    ativo_norm.armazenamento,
                    ativo_norm.sistema_operacional,
                    ativo_norm.carregador,
                    ativo_norm.teamviewer_id,
                    ativo_norm.anydesk_id,
                    ativo_norm.nome_equipamento,
                    ativo_norm.hostname,
                    ativo_norm.imei_1,
                    ativo_norm.imei_2,
                    ativo_norm.numero_linha,
                    ativo_norm.operadora,
                    ativo_norm.conta_vinculada,
                    ativo_norm.polegadas,
                    ativo_norm.resolucao,
                    ativo_norm.tipo_painel,
                    ativo_norm.entrada_video,
                    ativo_norm.fonte_ou_cabo,
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
                          SELECT id, codigo_interno, tipo, marca, modelo, serial, descricao,
                           categoria, tipo_ativo, condicao, localizacao, setor,
                           usuario_responsavel, email_responsavel, departamento,
                           nota_fiscal, garantia, status, data_entrada, data_saida,
                           data_compra, valor, observacoes, detalhes_tecnicos,
                           processador, ram, armazenamento, sistema_operacional,
                           carregador, teamviewer_id, anydesk_id, nome_equipamento,
                           hostname, imei_1, imei_2, numero_linha, operadora,
                           conta_vinculada, polegadas, resolucao, tipo_painel,
                           entrada_video, fonte_ou_cabo, criado_por,
                           created_at, updated_at, data_ultima_movimentacao
                    FROM ativos
                    ORDER BY id
                    """
                )
            else:
                cur.execute(
                    """
                          SELECT id, codigo_interno, tipo, marca, modelo, serial, descricao,
                           categoria, tipo_ativo, condicao, localizacao, setor,
                           usuario_responsavel, email_responsavel, departamento,
                           nota_fiscal, garantia, status, data_entrada, data_saida,
                           data_compra, valor, observacoes, detalhes_tecnicos,
                           processador, ram, armazenamento, sistema_operacional,
                           carregador, teamviewer_id, anydesk_id, nome_equipamento,
                           hostname, imei_1, imei_2, numero_linha, operadora,
                              conta_vinculada, polegadas, resolucao, tipo_painel,
                              entrada_video, fonte_ou_cabo, criado_por,
                              created_at, updated_at, data_ultima_movimentacao
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
                          SELECT id, codigo_interno, tipo, marca, modelo, serial, descricao,
                           categoria, tipo_ativo, condicao, localizacao, setor,
                           usuario_responsavel, email_responsavel, departamento,
                           nota_fiscal, garantia, status, data_entrada, data_saida,
                           data_compra, valor, observacoes, detalhes_tecnicos,
                           processador, ram, armazenamento, sistema_operacional,
                           carregador, teamviewer_id, anydesk_id, nome_equipamento,
                           hostname, imei_1, imei_2, numero_linha, operadora,
                              conta_vinculada, polegadas, resolucao, tipo_painel,
                              entrada_video, fonte_ou_cabo, criado_por, empresa_id,
                              created_at, updated_at, data_ultima_movimentacao
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
                          SELECT id, codigo_interno, tipo, marca, modelo, serial, descricao,
                           categoria, tipo_ativo, condicao, localizacao, setor,
                           usuario_responsavel, email_responsavel, departamento,
                           nota_fiscal, garantia, status, data_entrada, data_saida,
                           data_compra, valor, observacoes, detalhes_tecnicos,
                           processador, ram, armazenamento, sistema_operacional,
                           carregador, teamviewer_id, anydesk_id, nome_equipamento,
                           hostname, imei_1, imei_2, numero_linha, operadora,
                              conta_vinculada, polegadas, resolucao, tipo_painel,
                              entrada_video, fonte_ou_cabo, criado_por, empresa_id,
                              created_at, updated_at, data_ultima_movimentacao
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
            "tipo_ativo": "tipo_ativo",
            "marca": "marca",
            "modelo": "modelo",
            "descricao": "descricao",
            "categoria": "categoria",
            "usuario_responsavel": "usuario_responsavel",
            "setor": "setor",
            "localizacao": "localizacao",
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
            where.append("(tipo LIKE %s OR tipo_ativo LIKE %s)")
            params.append(f"%{filtros['tipo'].strip()}%")
            params.append(f"%{filtros['tipo'].strip()}%")

        if filtros.get("marca"):
            where.append("marca LIKE %s")
            params.append(f"%{filtros['marca'].strip()}%")

        if filtros.get("modelo"):
            where.append("modelo LIKE %s")
            params.append(f"%{filtros['modelo'].strip()}%")

        if filtros.get("descricao"):
            where.append("descricao LIKE %s")
            params.append(f"%{filtros['descricao'].strip()}%")

        if filtros.get("categoria"):
            where.append("categoria LIKE %s")
            params.append(f"%{filtros['categoria'].strip()}%")

        if filtros.get("localizacao"):
            where.append("localizacao LIKE %s")
            params.append(f"%{filtros['localizacao'].strip()}%")

        if filtros.get("setor"):
            where.append("setor LIKE %s")
            params.append(f"%{filtros['setor'].strip()}%")

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
                             SELECT id, codigo_interno, tipo, marca, modelo, serial, descricao,
                                     categoria, tipo_ativo, condicao, localizacao, setor,
                                     usuario_responsavel, email_responsavel, departamento,
                                     nota_fiscal, garantia, status, data_entrada, data_saida,
                                     data_compra, valor, observacoes, detalhes_tecnicos,
                                     processador, ram, armazenamento, sistema_operacional,
                                     carregador, teamviewer_id, anydesk_id, nome_equipamento,
                                     hostname, imei_1, imei_2, numero_linha, operadora,
                                     conta_vinculada, polegadas, resolucao, tipo_painel,
                                     entrada_video, fonte_ou_cabo, criado_por,
                                     created_at, updated_at, data_ultima_movimentacao
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
            tipo=dados.get("tipo_ativo", dados.get("tipo", atual.tipo_ativo or atual.tipo)),
            marca=dados.get("marca", atual.marca),
            modelo=dados.get("modelo", atual.modelo),
            serial=dados.get("serial", atual.serial),
            codigo_interno=dados.get("codigo_interno", atual.codigo_interno),
            descricao=dados.get("descricao", atual.descricao),
            categoria=dados.get("categoria", atual.categoria),
            tipo_ativo=dados.get("tipo_ativo", atual.tipo_ativo),
            condicao=dados.get("condicao", atual.condicao),
            localizacao=dados.get("localizacao", atual.localizacao),
            setor=dados.get("setor", atual.setor),
            usuario_responsavel=dados.get("usuario_responsavel", atual.usuario_responsavel),
            email_responsavel=dados.get("email_responsavel", atual.email_responsavel),
            departamento=dados.get("setor", dados.get("departamento", atual.departamento)),
            nota_fiscal=dados.get("nota_fiscal", atual.nota_fiscal),
            # Atualiza com o campo documental renomeado garantia.
            garantia=dados.get("garantia", atual.garantia),
            status=dados.get("status", atual.status),
            data_entrada=dados.get("data_entrada", atual.data_entrada),
            data_saida=dados.get("data_saida", atual.data_saida),
            data_compra=dados.get("data_compra", atual.data_compra),
            valor=dados.get("valor", atual.valor),
            observacoes=dados.get("observacoes", atual.observacoes),
            detalhes_tecnicos=dados.get("detalhes_tecnicos", atual.detalhes_tecnicos),
            processador=dados.get("processador", atual.processador),
            ram=dados.get("ram", atual.ram),
            armazenamento=dados.get("armazenamento", atual.armazenamento),
            sistema_operacional=dados.get("sistema_operacional", atual.sistema_operacional),
            carregador=dados.get("carregador", atual.carregador),
            teamviewer_id=dados.get("teamviewer_id", atual.teamviewer_id),
            anydesk_id=dados.get("anydesk_id", atual.anydesk_id),
            nome_equipamento=dados.get("nome_equipamento", atual.nome_equipamento),
            hostname=dados.get("hostname", atual.hostname),
            imei_1=dados.get("imei_1", atual.imei_1),
            imei_2=dados.get("imei_2", atual.imei_2),
            numero_linha=dados.get("numero_linha", atual.numero_linha),
            operadora=dados.get("operadora", atual.operadora),
            conta_vinculada=dados.get("conta_vinculada", atual.conta_vinculada),
            polegadas=dados.get("polegadas", atual.polegadas),
            resolucao=dados.get("resolucao", atual.resolucao),
            tipo_painel=dados.get("tipo_painel", atual.tipo_painel),
            entrada_video=dados.get("entrada_video", atual.entrada_video),
            fonte_ou_cabo=dados.get("fonte_ou_cabo", atual.fonte_ou_cabo),
            criado_por=atual.criado_por
        )

        novo_norm = _padronizar_ativo(novo)

        try:
            validar_ativo(novo_norm)
        except ValueError as erro:
            raise AtivoErro(str(erro)) from erro

        contexto = self._obter_contexto_acesso(user_id)
        resumo_movimentacao = self.analisar_movimentacao_ativo(atual, novo_norm)

        # O SET é montado dinamicamente para manter a mesma lógica para admin e usuário comum.
        campos_update = [
            ("codigo_interno", novo_norm.codigo_interno),
            ("tipo", novo_norm.tipo),
            ("marca", novo_norm.marca),
            ("modelo", novo_norm.modelo),
            ("serial", novo_norm.serial),
            ("descricao", novo_norm.descricao),
            ("categoria", novo_norm.categoria),
            ("tipo_ativo", novo_norm.tipo_ativo),
            ("condicao", novo_norm.condicao),
            ("localizacao", novo_norm.localizacao),
            ("setor", novo_norm.setor),
            ("usuario_responsavel", novo_norm.usuario_responsavel),
            ("email_responsavel", novo_norm.email_responsavel),
            ("departamento", novo_norm.departamento),
            ("nota_fiscal", novo_norm.nota_fiscal),
            ("garantia", novo_norm.garantia),
            ("status", novo_norm.status),
            ("data_entrada", novo_norm.data_entrada),
            ("data_saida", novo_norm.data_saida),
            ("data_compra", novo_norm.data_compra),
            ("valor", novo_norm.valor),
            ("observacoes", novo_norm.observacoes),
            ("detalhes_tecnicos", novo_norm.detalhes_tecnicos),
            ("processador", novo_norm.processador),
            ("ram", novo_norm.ram),
            ("armazenamento", novo_norm.armazenamento),
            ("sistema_operacional", novo_norm.sistema_operacional),
            ("carregador", novo_norm.carregador),
            ("teamviewer_id", novo_norm.teamviewer_id),
            ("anydesk_id", novo_norm.anydesk_id),
            ("nome_equipamento", novo_norm.nome_equipamento),
            ("hostname", novo_norm.hostname),
            ("imei_1", novo_norm.imei_1),
            ("imei_2", novo_norm.imei_2),
            ("numero_linha", novo_norm.numero_linha),
            ("operadora", novo_norm.operadora),
            ("conta_vinculada", novo_norm.conta_vinculada),
            ("polegadas", novo_norm.polegadas),
            ("resolucao", novo_norm.resolucao),
            ("tipo_painel", novo_norm.tipo_painel),
            ("entrada_video", novo_norm.entrada_video),
            ("fonte_ou_cabo", novo_norm.fonte_ou_cabo),
        ]

        set_clausulas = [f"{campo} = %s" for campo, _valor in campos_update]
        params_update = [valor for _campo, valor in campos_update]

        if resumo_movimentacao["atualizar_data_ultima_movimentacao"]:
            set_clausulas.append("data_ultima_movimentacao = NOW()")

        where_clause = "WHERE id = %s"
        if not self._usuario_eh_admin(contexto):
            where_clause = "WHERE id = %s AND empresa_id = %s"

        sql = f"UPDATE ativos SET {', '.join(set_clausulas)} {where_clause}"
        params_execucao = list(params_update)
        params_execucao.append(novo_norm.id_ativo)
        if not self._usuario_eh_admin(contexto):
            params_execucao.append(int(contexto["empresa_id"]))

        with cursor_mysql(dictionary=True) as (_conn, cur):
            cur.execute(sql, tuple(params_execucao))

            if cur.rowcount == 0:
                raise AtivoNaoEncontrado("Não foi possível atualizar o ativo.")

        ativo_atualizado = self.buscar_ativo(id_ativo=id_ativo, user_id=user_id)
        ativo_atualizado.resumo_movimentacao = resumo_movimentacao
        return ativo_atualizado

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