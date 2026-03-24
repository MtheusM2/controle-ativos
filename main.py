from services.auth_service import (
    AuthService,
    AuthErro,
    UsuarioJaExiste,
    UsuarioNaoEncontrado,
    CredenciaisInvalidas,
    RecuperacaoInvalida
)
from services.ativos_service import AtivosService
from services.sistema_ativos import SistemaAtivos


def _input_cancelavel(mensagem: str) -> str | None:
    valor = input(mensagem).strip()

    if valor == "0":
        return None

    return valor


def menu_auth():
    print("\n=== AUTENTICAÇÃO ===")
    print("1 - Login")
    print("2 - Cadastro")
    print("3 - Recuperar senha")
    print("4 - Sair")
    return input("Opção: ").strip()


def menu_ativos():
    print("\n=== SISTEMA DE CONTROLE DE ATIVOS ===")
    print("1 - Cadastrar")
    print("2 - Listar")
    print("3 - Buscar por ID")
    print("4 - Filtrar e ordenar")
    print("5 - Editar")
    print("6 - Remover")
    print("7 - Logout")
    return input("Opção: ").strip()


def executar():
    auth = AuthService()
    ativos_service = AtivosService()
    usuario = None

    while True:
        if not usuario:
            op = menu_auth()

            if op == "1":
                print("\n--- LOGIN ---")
                print("Digite 0 para cancelar.")

                email = _input_cancelavel("Email: ")
                if email is None:
                    continue

                senha = _input_cancelavel("Senha: ")
                if senha is None:
                    continue

                try:
                    usuario = auth.autenticar(email, senha)
                    print(f"Login realizado com sucesso. Bem-vindo(a), {usuario.email}.")
                except (UsuarioNaoEncontrado, CredenciaisInvalidas) as erro:
                    print(f"Erro: {erro}")
                except AuthErro as erro:
                    print(f"Erro: {erro}")

            elif op == "2":
                print("\n--- CADASTRO DE USUÁRIO ---")
                print("Digite 0 para cancelar.")

                email = _input_cancelavel("Email: ")
                if email is None:
                    continue

                senha = _input_cancelavel("Senha: ")
                if senha is None:
                    continue

                senha_confirmacao = _input_cancelavel("Repita a senha: ")
                if senha_confirmacao is None:
                    continue

                if senha != senha_confirmacao:
                    print("As senhas não coincidem.")
                    continue

                pergunta = _input_cancelavel("Pergunta de recuperação: ")
                if pergunta is None:
                    continue

                resposta = _input_cancelavel("Resposta de recuperação: ")
                if resposta is None:
                    continue

                try:
                    user_id = auth.registrar_usuario(email, senha, pergunta, resposta)
                    print(f"Usuário cadastrado com sucesso. ID: {user_id}")
                except UsuarioJaExiste as erro:
                    print(f"Erro: {erro}")
                except AuthErro as erro:
                    print(f"Erro: {erro}")

            elif op == "3":
                print("\n--- RECUPERAR SENHA ---")
                print("Digite 0 para cancelar.")

                email = _input_cancelavel("Email: ")
                if email is None:
                    continue

                try:
                    pergunta = auth.obter_pergunta_recuperacao(email)
                except UsuarioNaoEncontrado as erro:
                    print(f"Erro: {erro}")
                    continue
                except AuthErro as erro:
                    print(f"Erro: {erro}")
                    continue

                print(f"Pergunta: {pergunta}")

                resposta = _input_cancelavel("Resposta: ")
                if resposta is None:
                    continue

                nova_senha = _input_cancelavel("Nova senha: ")
                if nova_senha is None:
                    continue

                confirmar_nova = _input_cancelavel("Repita a nova senha: ")
                if confirmar_nova is None:
                    continue

                if nova_senha != confirmar_nova:
                    print("As senhas não coincidem.")
                    continue

                try:
                    auth.redefinir_senha(email, resposta, nova_senha)
                    print("Senha redefinida com sucesso.")
                except RecuperacaoInvalida as erro:
                    print(f"Erro: {erro}")
                except AuthErro as erro:
                    print(f"Erro: {erro}")

            elif op == "4":
                print("Encerrando o sistema.")
                break

            else:
                print("Opção inválida.")

        else:
            sistema = SistemaAtivos(ativos_service, usuario.id)

            op = menu_ativos()

            if op == "1":
                sistema.cadastrar_ativo()
            elif op == "2":
                sistema.listar_ativos()
            elif op == "3":
                sistema.buscar_ativo()
            elif op == "4":
                sistema.filtrar_ativos()
            elif op == "5":
                sistema.editar_ativo()
            elif op == "6":
                sistema.remover_ativo()
            elif op == "7":
                usuario = None
                print("Logout realizado.")
            else:
                print("Opção inválida.")


if __name__ == "__main__":
    executar()