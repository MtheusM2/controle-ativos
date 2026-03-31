# services/sistema_ativos.py

# Interface de linha de comando (CLI) do módulo de ativos.
# Apesar de o nome atual estar em "services", este arquivo se comporta
# como camada de interface. Em uma refatoração futura, o ideal é mover
# isso para uma pasta própria de CLI.

from models.ativos import Ativo
from services.ativos_service import (
    AtivosService,
    AtivoErro,
    AtivoJaExiste,
    AtivoNaoEncontrado,
    PermissaoNegada
)
from utils.validators import STATUS_VALIDOS


class SistemaAtivos:
    """
    Interface de terminal responsável por intermediar a interação do usuário
    com o módulo de ativos.
    """

    def __init__(self, ativos_service: AtivosService, user_id: int):
        # Service de domínio dos ativos.
        self.ativos_service = ativos_service

        # ID do usuário autenticado.
        self.user_id = user_id

    def _mensagem_cancelar(self):
        """
        Exibe instrução padrão de cancelamento.
        """
        print("Digite 0 para cancelar e voltar ao menu.")

    def _input_obrigatorio(self, mensagem, nome):
        """
        Solicita um campo obrigatório ao usuário.
        """
        while True:
            valor = input(mensagem).strip()

            if valor == "0":
                return None

            if not valor:
                print(f"O campo {nome} não pode ficar vazio.")
                continue

            return valor

    def _input_opcional(self, mensagem):
        """
        Solicita um campo opcional ao usuário.
        """
        valor = input(mensagem).strip()

        if valor == "0":
            return None

        return valor

    def _input_status(self, permitir_vazio=False):
        """
        Solicita o status do ativo exibindo as opções válidas.
        """
        while True:
            print("\nStatus disponíveis:")
            for s in STATUS_VALIDOS:
                print(f"- {s}")

            valor = input("Status: ").strip()

            if valor == "0":
                return None

            if permitir_vazio and valor == "":
                return ""

            if not valor:
                print("O status não pode ficar vazio.")
                continue

            return valor

    def _confirmar(self, mensagem):
        """
        Solicita confirmação simples ao usuário.
        """
        while True:
            r = input(mensagem).strip().lower()

            if r in ("s", "n", "0"):
                return r

            print("Digite s, n ou 0.")

    def _exibir_ativo(self, ativo: Ativo):
        """
        Exibe os dados de um ativo no terminal.
        """
        print("\n--- ATIVO ---")
        print(f"ID: {ativo.id_ativo}")
        print(f"Tipo: {ativo.tipo}")
        print(f"Marca: {ativo.marca}")
        print(f"Modelo: {ativo.modelo}")
        print(f"Responsável: {ativo.usuario_responsavel or '-'}")
        print(f"Departamento: {ativo.departamento}")
        print(f"Nota fiscal: {ativo.nota_fiscal or '-'}")
        print(f"Seguro: {ativo.seguro or '-'}")
        print(f"Status: {ativo.status}")
        print(f"Entrada: {ativo.data_entrada}")
        print(f"Saída: {ativo.data_saida or '-'}")

    def cadastrar_ativo(self):
        """
        Fluxo CLI de cadastro de ativo.
        """
        while True:
            print("\n=== CADASTRO DE ATIVO ===")
            self._mensagem_cancelar()

            id_ativo = self._input_obrigatorio("ID: ", "ID")
            if id_ativo is None:
                print("Cadastro cancelado.")
                return

            tipo = self._input_obrigatorio("Tipo: ", "tipo")
            if tipo is None:
                print("Cadastro cancelado.")
                return

            marca = self._input_obrigatorio("Marca: ", "marca")
            if marca is None:
                print("Cadastro cancelado.")
                return

            modelo = self._input_obrigatorio("Modelo: ", "modelo")
            if modelo is None:
                print("Cadastro cancelado.")
                return

            usuario_responsavel = self._input_opcional(
                "Responsável (opcional; obrigatório para status 'Em Uso'): "
            )
            if usuario_responsavel is None:
                print("Cadastro cancelado.")
                return

            departamento = self._input_obrigatorio("Departamento: ", "departamento")
            if departamento is None:
                print("Cadastro cancelado.")
                return

            nota_fiscal = self._input_opcional(
                "Nota fiscal (opcional, mas NF ou seguro deve existir): "
            )
            if nota_fiscal is None:
                print("Cadastro cancelado.")
                return

            seguro = self._input_opcional(
                "Seguro (opcional, mas NF ou seguro deve existir): "
            )
            if seguro is None:
                print("Cadastro cancelado.")
                return

            status = self._input_status()
            if status is None:
                print("Cadastro cancelado.")
                return

            data_entrada = self._input_obrigatorio(
                "Data entrada (YYYY-MM-DD): ",
                "data_entrada"
            )
            if data_entrada is None:
                print("Cadastro cancelado.")
                return

            data_saida = self._input_opcional(
                "Data saída (YYYY-MM-DD) ou Enter para vazio: "
            )
            if data_saida is None:
                print("Cadastro cancelado.")
                return

            ativo = Ativo(
                id_ativo=id_ativo,
                tipo=tipo,
                marca=marca,
                modelo=modelo,
                usuario_responsavel=usuario_responsavel or None,
                departamento=departamento,
                nota_fiscal=nota_fiscal or None,
                seguro=seguro or None,
                status=status,
                data_entrada=data_entrada,
                data_saida=data_saida or None,
                criado_por=self.user_id
            )

            self._exibir_ativo(ativo)

            confirm = self._confirmar("Confirmar cadastro? (s/n/0): ")

            if confirm == "0":
                print("Cadastro cancelado.")
                return

            if confirm == "n":
                print("Refazendo cadastro.")
                continue

            try:
                self.ativos_service.criar_ativo(ativo, self.user_id)
                print("Cadastrado com sucesso.")
                return
            except (AtivoErro, AtivoJaExiste) as erro:
                print(f"Erro: {erro}")

    def listar_ativos(self):
        """
        Lista os ativos do usuário autenticado.
        """
        print("\n=== LISTAGEM DE ATIVOS ===")

        try:
            ativos = self.ativos_service.listar_ativos(self.user_id)
        except Exception as erro:
            print(f"Erro ao listar ativos: {erro}")
            return

        if not ativos:
            print("Nenhum ativo.")
            return

        for ativo in ativos:
            self._exibir_ativo(ativo)

    def buscar_ativo(self):
        """
        Busca um ativo por ID.
        """
        print("\n=== BUSCA POR ID ===")
        self._mensagem_cancelar()

        id_ativo = self._input_obrigatorio("ID: ", "ID")
        if id_ativo is None:
            return

        try:
            ativo = self.ativos_service.buscar_ativo(id_ativo, self.user_id)
            self._exibir_ativo(ativo)
        except (AtivoErro, AtivoNaoEncontrado, PermissaoNegada) as erro:
            print(f"Erro: {erro}")

    def filtrar_ativos(self):
        """
        Filtra ativos com base em critérios informados pelo usuário.
        """
        print("\n=== FILTRAR ATIVOS ===")
        print("Deixe vazio para ignorar um filtro.")
        self._mensagem_cancelar()

        id_ativo = self._input_opcional("Filtrar por ID: ")
        if id_ativo is None:
            return

        usuario_responsavel = self._input_opcional("Filtrar por responsável: ")
        if usuario_responsavel is None:
            return

        departamento = self._input_opcional("Filtrar por departamento: ")
        if departamento is None:
            return

        nota_fiscal = self._input_opcional("Filtrar por nota fiscal: ")
        if nota_fiscal is None:
            return

        seguro = self._input_opcional("Filtrar por seguro: ")
        if seguro is None:
            return

        status = self._input_opcional("Filtrar por status: ")
        if status is None:
            return

        data_entrada_inicial = self._input_opcional("Data entrada inicial (YYYY-MM-DD): ")
        if data_entrada_inicial is None:
            return

        data_entrada_final = self._input_opcional("Data entrada final (YYYY-MM-DD): ")
        if data_entrada_final is None:
            return

        data_saida_inicial = self._input_opcional("Data saída inicial (YYYY-MM-DD): ")
        if data_saida_inicial is None:
            return

        data_saida_final = self._input_opcional("Data saída final (YYYY-MM-DD): ")
        if data_saida_final is None:
            return

        print("\nOrdenação disponível:")
        print("id, tipo, marca, modelo, usuario_responsavel, departamento, nota_fiscal, seguro, status, data_entrada, data_saida")

        ordenar_por = input("Ordenar por (Enter para id): ").strip() or "id"
        ordem = input("Ordem (asc/desc, Enter para asc): ").strip().lower() or "asc"

        filtros = {
            "id_ativo": id_ativo or None,
            "usuario_responsavel": usuario_responsavel or None,
            "departamento": departamento or None,
            "nota_fiscal": nota_fiscal or None,
            "seguro": seguro or None,
            "status": status or None,
            "data_entrada_inicial": data_entrada_inicial or None,
            "data_entrada_final": data_entrada_final or None,
            "data_saida_inicial": data_saida_inicial or None,
            "data_saida_final": data_saida_final or None,
        }

        try:
            ativos = self.ativos_service.filtrar_ativos(
                user_id=self.user_id,
                filtros=filtros,
                ordenar_por=ordenar_por,
                ordem=ordem
            )
        except AtivoErro as erro:
            print(f"Erro: {erro}")
            return

        if not ativos:
            print("Nenhum ativo encontrado.")
            return

        for ativo in ativos:
            self._exibir_ativo(ativo)

    def editar_ativo(self):
        """
        Fluxo CLI de edição de ativo.
        """
        print("\n=== EDITAR ATIVO ===")
        self._mensagem_cancelar()

        id_ativo = self._input_obrigatorio("ID: ", "ID")
        if id_ativo is None:
            return

        try:
            atual = self.ativos_service.buscar_ativo(id_ativo, self.user_id)
        except AtivoErro as erro:
            print(f"Erro: {erro}")
            return

        while True:
            print("\nDeixe em branco para manter o valor atual.")

            novo_tipo = self._input_opcional(f"Tipo atual ({atual.tipo}): ")
            if novo_tipo is None:
                return

            nova_marca = self._input_opcional(f"Marca atual ({atual.marca}): ")
            if nova_marca is None:
                return

            novo_modelo = self._input_opcional(f"Modelo atual ({atual.modelo}): ")
            if novo_modelo is None:
                return

            valor_responsavel = atual.usuario_responsavel or "-"
            novo_usuario = self._input_opcional(
                f"Responsável atual ({valor_responsavel}) [opcional]: "
            )
            if novo_usuario is None:
                return

            novo_departamento = self._input_opcional(f"Departamento atual ({atual.departamento}): ")
            if novo_departamento is None:
                return

            valor_nf = atual.nota_fiscal or "-"
            nova_nota_fiscal = self._input_opcional(f"Nota fiscal atual ({valor_nf}): ")
            if nova_nota_fiscal is None:
                return

            valor_seguro = atual.seguro or "-"
            novo_seguro = self._input_opcional(f"Seguro atual ({valor_seguro}): ")
            if novo_seguro is None:
                return

            print(f"\nStatus atual: {atual.status}")
            novo_status = self._input_status(True)
            if novo_status is None:
                return

            nova_data_entrada = self._input_opcional(f"Data entrada atual ({atual.data_entrada}): ")
            if nova_data_entrada is None:
                return

            valor_saida = atual.data_saida if atual.data_saida else "-"
            nova_data_saida = self._input_opcional(f"Data saída atual ({valor_saida}): ")
            if nova_data_saida is None:
                return

            dados = {}

            if novo_tipo != "":
                dados["tipo"] = novo_tipo

            if nova_marca != "":
                dados["marca"] = nova_marca

            if novo_modelo != "":
                dados["modelo"] = novo_modelo

            if novo_usuario != "":
                dados["usuario_responsavel"] = novo_usuario

            if novo_departamento != "":
                dados["departamento"] = novo_departamento

            if nova_nota_fiscal != "":
                dados["nota_fiscal"] = nova_nota_fiscal

            if novo_seguro != "":
                dados["seguro"] = novo_seguro

            if novo_status != "":
                dados["status"] = novo_status

            if nova_data_entrada != "":
                dados["data_entrada"] = nova_data_entrada

            if nova_data_saida != "":
                dados["data_saida"] = nova_data_saida

            preview = Ativo(
                id_ativo=atual.id_ativo,
                tipo=dados.get("tipo", atual.tipo),
                marca=dados.get("marca", atual.marca),
                modelo=dados.get("modelo", atual.modelo),
                usuario_responsavel=dados.get("usuario_responsavel", atual.usuario_responsavel),
                departamento=dados.get("departamento", atual.departamento),
                nota_fiscal=dados.get("nota_fiscal", atual.nota_fiscal),
                seguro=dados.get("seguro", atual.seguro),
                status=dados.get("status", atual.status),
                data_entrada=dados.get("data_entrada", atual.data_entrada),
                data_saida=dados.get("data_saida", atual.data_saida),
                criado_por=atual.criado_por
            )

            self._exibir_ativo(preview)

            confirm = self._confirmar("Confirmar alterações? (s/n/0): ")

            if confirm == "0":
                print("Edição cancelada.")
                return

            if confirm == "n":
                print("Refazendo edição.")
                continue

            try:
                atualizado = self.ativos_service.atualizar_ativo(
                    id_ativo=atual.id_ativo,
                    dados=dados,
                    user_id=self.user_id
                )
                print("Atualizado.")
                self._exibir_ativo(atualizado)
                return
            except AtivoErro as erro:
                print(f"Erro: {erro}")

    def remover_ativo(self):
        """
        Fluxo CLI de remoção de ativo.
        """
        print("\n=== REMOVER ATIVO ===")
        self._mensagem_cancelar()

        id_ativo = self._input_obrigatorio("ID: ", "ID")
        if id_ativo is None:
            return

        try:
            ativo = self.ativos_service.buscar_ativo(id_ativo, self.user_id)
            self._exibir_ativo(ativo)
        except AtivoErro as erro:
            print(f"Erro: {erro}")
            return

        confirm = self._confirmar("Remover? (s/n/0): ")

        if confirm != "s":
            print("Remoção cancelada.")
            return

        try:
            self.ativos_service.remover_ativo(id_ativo, self.user_id)
            print("Removido.")
        except AtivoErro as erro:
            print(f"Erro: {erro}")