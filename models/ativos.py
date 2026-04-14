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
        serial=None,
        usuario_responsavel=None,
        departamento=None,
        nota_fiscal=None,
        garantia=None,
        status=None,
        data_entrada=None,
        data_saida=None,
        criado_por=None,
        codigo_interno=None,
        descricao=None,
        categoria=None,
        tipo_ativo=None,
        condicao=None,
        localizacao=None,
        setor=None,
        email_responsavel=None,
        data_compra=None,
        valor=None,
        observacoes=None,
        detalhes_tecnicos=None,
        processador=None,
        ram=None,
        armazenamento=None,
        sistema_operacional=None,
        carregador=None,
        teamviewer_id=None,
        anydesk_id=None,
        nome_equipamento=None,
        hostname=None,
        imei_1=None,
        imei_2=None,
        numero_linha=None,
        operadora=None,
        conta_vinculada=None,
        polegadas=None,
        resolucao=None,
        tipo_painel=None,
        entrada_video=None,
        fonte_ou_cabo=None,
        created_at=None,
        updated_at=None,
        data_ultima_movimentacao=None,
    ):
        # Identificador único do ativo no sistema.
        self.id_ativo = id_ativo

        # Campo legado mantido para compatibilidade com telas e testes antigos.
        # O campo oficial no novo cadastro é tipo_ativo.
        self.tipo = tipo

        # Marca do ativo.
        self.marca = marca

        # Modelo do ativo.
        self.modelo = modelo

        # Número de série do fabricante.
        self.serial = serial

        # Responsável pelo ativo.
        self.usuario_responsavel = usuario_responsavel

        # Campo legado mantido para compatibilidade com integrações antigas.
        # O campo oficial no novo cadastro é setor.
        self.departamento = departamento

        # Número/referência da nota fiscal.
        self.nota_fiscal = nota_fiscal

        # Número/referência da garantia do ativo.
        self.garantia = garantia

        # Status atual do ativo.
        self.status = status

        # Data de entrada do ativo.
        self.data_entrada = data_entrada

        # Data de saída do ativo, quando existir.
        self.data_saida = data_saida

        # Usuário que criou o registro.
        self.criado_por = criado_por

        # Campo patrimonial complementar ao ID automático do ativo.
        self.codigo_interno = codigo_interno

        # Campo descritivo principal do cadastro base.
        self.descricao = descricao

        # Categoria funcional usada para organização da listagem.
        self.categoria = categoria

        # Campo oficial do novo cadastro inteligente; usa fallback de tipo apenas para compatibilidade.
        self.tipo_ativo = tipo_ativo or tipo

        # Condição física/operacional do ativo.
        self.condicao = condicao

        # Localização física da unidade/estoque/sala.
        self.localizacao = localizacao

        # Campo oficial de alocação; usa fallback de departamento apenas para compatibilidade.
        self.setor = setor or departamento

        # Timestamps automáticos do ciclo de vida do ativo.
        # Os nomes novos são oficiais; os antigos ficam como alias de compatibilidade.
        self.created_at = created_at
        self.updated_at = updated_at
        self.data_ultima_movimentacao = data_ultima_movimentacao
        self.criado_em = created_at
        self.atualizado_em = updated_at

        # E-mail do responsável atual pelo ativo.
        self.email_responsavel = email_responsavel

        # Data de compra do ativo (quando disponível).
        self.data_compra = data_compra

        # Valor de aquisição declarado no cadastro.
        self.valor = valor

        # Observações gerais do ativo.
        self.observacoes = observacoes

        # Campo livre para ativos simples sem ficha técnica extensa.
        self.detalhes_tecnicos = detalhes_tecnicos

        # Especificações técnicas por tipo de ativo.
        self.processador = processador
        self.ram = ram
        self.armazenamento = armazenamento
        self.sistema_operacional = sistema_operacional
        self.carregador = carregador
        self.teamviewer_id = teamviewer_id
        self.anydesk_id = anydesk_id
        self.nome_equipamento = nome_equipamento
        self.hostname = hostname
        self.imei_1 = imei_1
        self.imei_2 = imei_2
        self.numero_linha = numero_linha
        self.operadora = operadora
        self.conta_vinculada = conta_vinculada
        self.polegadas = polegadas
        self.resolucao = resolucao
        self.tipo_painel = tipo_painel
        self.entrada_video = entrada_video
        self.fonte_ou_cabo = fonte_ou_cabo

    def to_dict(self):
        """
        Converte o objeto em dicionário.
        """
        return {
            "id_ativo": self.id_ativo,
            "tipo": self.tipo,
            "tipo_ativo": self.tipo_ativo,
            "marca": self.marca,
            "modelo": self.modelo,
            "serial": self.serial or "",
            "codigo_interno": self.codigo_interno or "",
            "descricao": self.descricao or "",
            "categoria": self.categoria or "",
            "condicao": self.condicao or "",
            "localizacao": self.localizacao or "",
            "setor": self.setor or "",
            "usuario_responsavel": self.usuario_responsavel or "",
            "email_responsavel": self.email_responsavel or "",
            "departamento": self.departamento,
            "data_compra": self.data_compra or "",
            "valor": self.valor or "",
            "nota_fiscal": self.nota_fiscal or "",
            # Mantém o campo documental nomeado como garantia no domínio.
            "garantia": self.garantia or "",
            "status": self.status,
            "data_entrada": self.data_entrada,
            "data_saida": self.data_saida or "",
            "observacoes": self.observacoes or "",
            "detalhes_tecnicos": self.detalhes_tecnicos or "",
            "processador": self.processador or "",
            "ram": self.ram or "",
            "armazenamento": self.armazenamento or "",
            "sistema_operacional": self.sistema_operacional or "",
            "carregador": self.carregador or "",
            "teamviewer_id": self.teamviewer_id or "",
            "anydesk_id": self.anydesk_id or "",
            "nome_equipamento": self.nome_equipamento or "",
            "hostname": self.hostname or "",
            "imei_1": self.imei_1 or "",
            "imei_2": self.imei_2 or "",
            "numero_linha": self.numero_linha or "",
            "operadora": self.operadora or "",
            "conta_vinculada": self.conta_vinculada or "",
            "polegadas": self.polegadas or "",
            "resolucao": self.resolucao or "",
            "tipo_painel": self.tipo_painel or "",
            "entrada_video": self.entrada_video or "",
            "fonte_ou_cabo": self.fonte_ou_cabo or "",
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "data_ultima_movimentacao": self.data_ultima_movimentacao,
            "criado_em": self.criado_em,
            "atualizado_em": self.atualizado_em,
            "criado_por": self.criado_por
        }