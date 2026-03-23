from models.ativos import Ativo
from services.ativos_service import (
    AtivosService,
    AtivoErro,
    AtivoJaExiste,
    AtivoNaoEncontrado,
    PermissaoNegada
)
from utils.validators import STATUS_VALIDOS, padronizar_texto


class SistemaAtivos:
    def __init__(self, ativos_service: AtivosService, user_id: int):
        self.ativos_service = ativos_service
        self.user_id = user_id

    def _mensagem_cancelar(self):
        print("Digite 0 para cancelar e voltar ao menu.")

    def _input_obrigatorio(self, mensagem: str, nome_campo: str) -> str | None:
        while True:
            valor = input(mensagem).strip()

            if valor == "0":
                return None

            if not valor:
                print(f"O campo {nome_campo} não pode ficar vazio. Tente novamente.")
                continue

            return valor

    def _input_opcional(self, mensagem: str) -> str | None:
        valor = input(mensagem).strip()

        if valor == "0":
            return None

        return valor

    def _input_status(self, permitir_vazio: bool = False) -> str | None:
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
                print("O status não pode ficar vazio. Tente novamente.")
                continue

            valor_fmt = valor.title()

            if valor_fmt not in STATUS_VALIDOS:
                print("Status inválido. Escolha um da lista.")
                continue

            return valor_fmt

    def _confirmar(self, mensagem: str) -> str:
        while True:
            resp = input(mensagem).strip().lower()

            if resp in ("s", "n", "0"):
                return resp

            print("Resposta inválida. Digite s, n ou 0.")

    def _exibir_ativo(self, ativo: Ativo):
        print("\n--- DADOS DO ATIVO ---")
        print(f"ID: {ativo.id_ativo}")
        print(f"Tipo: {ativo.tipo}")
        print(f"Marca: {ativo.marca}")
        print(f"Modelo: {ativo.modelo}")
        print(f"Usuário: {ativo.usuario}")
        print(f"Departamento: {ativo.departamento}")
        print(f"Status: {ativo.status}")

    def cadastrar_ativo(self):
        while True:
            print("\n=== CADASTRAR ATIVO ===")
            self._mensagem_cancelar()

            id_ativo = self._input_obrigatorio("ID do ativo: ", "ID")
            if id_ativo is None:
                print("Cadastro cancelado.")
                return

            tipo = self._input_obrigatorio("Tipo do equipamento: ", "tipo")
            if tipo is None:
                print("Cadastro cancelado.")
                return

            marca = self._input_obrigatorio("Marca do equipamento: ", "marca")
            if marca is None:
                print("Cadastro cancelado.")
                return

            modelo = self._input_obrigatorio("Modelo do equipamento: ", "modelo")
            if modelo is None:
                print("Cadastro cancelado.")
                return

            usuario = self._input_obrigatorio("Nome do usuário responsável: ", "usuário")
            if usuario is None:
                print("Cadastro cancelado.")
                return

            departamento = self._input_obrigatorio("Departamento: ", "departamento")
            if departamento is None:
                print("Cadastro cancelado.")
                return

            status = self._input_status(permitir_vazio=False)
            if status is None:
                print("Cadastro cancelado.")
                return

            novo = Ativo(
                id_ativo=id_ativo,
                tipo=tipo,
                marca=marca,
                modelo=modelo,
                usuario=usuario,
                departamento=departamento,
                status=status
            )

            self._exibir_ativo(
                Ativo(
                    id_ativo=novo.id_ativo.strip(),
                    tipo=padronizar_texto(novo.tipo, "title"),
                    marca=padronizar_texto(novo.marca, "title"),
                    modelo=padronizar_texto(novo.modelo, "upper"),
                    usuario=padronizar_texto(novo.usuario, "title"),
                    departamento=padronizar_texto(novo.departamento, "title"),
                    status=padronizar_texto(novo.status, "title"),
                )
            )

            resp = self._confirmar("Confirmar cadastro? (s = salvar / n = corrigir / 0 = cancelar): ")

            if resp == "0":
                print("Cadastro cancelado.")
                return

            if resp == "n":
                print("Ok, vamos refazer o cadastro...")
                continue

            try:
                self.ativos_service.criar_ativo(novo, user_id=self.user_id)
                print("Ativo cadastrado com sucesso!")
                return
            except AtivoJaExiste as e:
                print(f"Erro: {e}")
                continue
            except AtivoErro as e:
                print(f"Erro: {e}")
                continue

    def listar_ativos(self):
        print("\n=== LISTAR ATIVOS ===")

        try:
            ativos = self.ativos_service.listar_ativos(user_id=self.user_id)
        except Exception as e:
            print(f"Erro ao listar ativos: {e}")
            return

        if not ativos:
            print("Nenhum ativo cadastrado.")
            return

        print(f"Total: {len(ativos)}")
        for a in ativos:
            self._exibir_ativo(a)

    def buscar_ativo(self):
        print("\n=== BUSCAR ATIVO ===")
        self._mensagem_cancelar()

        id_ativo = self._input_obrigatorio("Digite o ID do ativo: ", "ID")
        if id_ativo is None:
            print("Busca cancelada.")
            return

        try:
            ativo = self.ativos_service.buscar_ativo(id_ativo=id_ativo, user_id=self.user_id)
            self._exibir_ativo(ativo)
        except (AtivoNaoEncontrado, PermissaoNegada) as e:
            print(f"Erro: {e}")
        except AtivoErro as e:
            print(f"Erro: {e}")

    def editar_ativo(self):
        print("\n=== EDITAR ATIVO ===")
        self._mensagem_cancelar()

        id_ativo = self._input_obrigatorio("Digite o ID do ativo a editar: ", "ID")
        if id_ativo is None:
            print("Edição cancelada.")
            return

        try:
            atual = self.ativos_service.buscar_ativo(id_ativo=id_ativo, user_id=self.user_id)
        except AtivoErro as e:
            print(f"Erro: {e}")
            return

        while True:
            print("\nDeixe em branco e pressione Enter para manter o valor atual.")
            print("Digite 0 para cancelar.\n")

            novo_tipo = self._input_opcional(f"Tipo atual ({atual.tipo}): ")
            if novo_tipo is None:
                print("Edição cancelada.")
                return

            nova_marca = self._input_opcional(f"Marca atual ({atual.marca}): ")
            if nova_marca is None:
                print("Edição cancelada.")
                return

            novo_modelo = self._input_opcional(f"Modelo atual ({atual.modelo}): ")
            if novo_modelo is None:
                print("Edição cancelada.")
                return

            novo_usuario = self._input_opcional(f"Usuário atual ({atual.usuario}): ")
            if novo_usuario is None:
                print("Edição cancelada.")
                return

            novo_departamento = self._input_opcional(f"Departamento atual ({atual.departamento}): ")
            if novo_departamento is None:
                print("Edição cancelada.")
                return

            print(f"\nStatus atual: {atual.status}")
            print("Digite Enter para manter o status atual.")
            novo_status = self._input_status(permitir_vazio=True)
            if novo_status is None:
                print("Edição cancelada.")
                return

            dados = {}
            if novo_tipo != "":
                dados["tipo"] = novo_tipo
            if nova_marca != "":
                dados["marca"] = nova_marca
            if novo_modelo != "":
                dados["modelo"] = novo_modelo
            if novo_usuario != "":
                dados["usuario"] = novo_usuario
            if novo_departamento != "":
                dados["departamento"] = novo_departamento
            if novo_status != "":
                dados["status"] = novo_status

            preview = Ativo(
                id_ativo=atual.id_ativo,
                tipo=dados.get("tipo", atual.tipo),
                marca=dados.get("marca", atual.marca),
                modelo=dados.get("modelo", atual.modelo),
                usuario=dados.get("usuario", atual.usuario),
                departamento=dados.get("departamento", atual.departamento),
                status=dados.get("status", atual.status),
            )

            self._exibir_ativo(
                Ativo(
                    id_ativo=preview.id_ativo.strip(),
                    tipo=padronizar_texto(preview.tipo, "title"),
                    marca=padronizar_texto(preview.marca, "title"),
                    modelo=padronizar_texto(preview.modelo, "upper"),
                    usuario=padronizar_texto(preview.usuario, "title"),
                    departamento=padronizar_texto(preview.departamento, "title"),
                    status=padronizar_texto(preview.status, "title"),
                )
            )

            resp = self._confirmar("Confirmar alterações? (s = salvar / n = corrigir / 0 = cancelar): ")

            if resp == "0":
                print("Edição cancelada.")
                return

            if resp == "n":
                print("Ok, vamos refazer a edição...")
                continue

            try:
                atualizado = self.ativos_service.atualizar_ativo(
                    id_ativo=atual.id_ativo,
                    dados=dados,
                    user_id=self.user_id
                )
                print("Ativo atualizado com sucesso!")
                self._exibir_ativo(atualizado)
                return
            except AtivoErro as e:
                print(f"Erro: {e}")
                continue

    def remover_ativo(self):
        print("\n=== REMOVER ATIVO ===")
        self._mensagem_cancelar()

        id_ativo = self._input_obrigatorio("Digite o ID do ativo a remover: ", "ID")
        if id_ativo is None:
            print("Remoção cancelada.")
            return

        try:
            ativo = self.ativos_service.buscar_ativo(id_ativo=id_ativo, user_id=self.user_id)
        except AtivoErro as e:
            print(f"Erro: {e}")
            return

        self._exibir_ativo(ativo)

        resp = self._confirmar("Tem certeza que deseja remover? (s = remover / n = voltar / 0 = cancelar): ")

        if resp in ("0", "n"):
            print("Remoção cancelada.")
            return

        try:
            self.ativos_service.remover_ativo(id_ativo=id_ativo, user_id=self.user_id)
            print("Ativo removido com sucesso!")
        except AtivoErro as e:
            print(f"Erro: {e}")