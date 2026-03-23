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


def _menu_auth() -> str:
    print("\n=== AUTENTICAÇÃO ===")
    print("1 - Login")
    print("2 - Cadastrar usuário")
    print("3 - Esqueci a senha")
    print("4 - Sair")
    return input("Escolha uma opção: ").strip()


def _menu_ativos() -> str:
    print("\n=== SISTEMA DE CONTROLE DE ATIVOS ===")
    print("1 - Cadastrar ativo")
    print("2 - Listar ativos")
    print("3 - Buscar ativo")
    print("4 - Editar ativo")
    print("5 - Remover ativo")
    print("6 - Logout")
    return input("Escolha uma opção: ").strip()


def executar():
    auth = AuthService()
    ativos_service = AtivosService()
    usuario_logado = None

    while True:
        if usuario_logado is None:
            opc = _menu_auth()

            if opc == "1":
                print("\n--- LOGIN ---")
                print("Digite 0 para cancelar.")

                email = _input_cancelavel("Email: ")
                if email is None:
                    continue

                senha = _input_cancelavel("Senha: ")
                if senha is None:
                    continue

                try:
                    usuario_logado = auth.autenticar(email=email, senha=senha)
                    print(f"Login realizado com sucesso! Bem-vindo(a), {usuario_logado.email}.")
                except (UsuarioNaoEncontrado, CredenciaisInvalidas) as e:
                    print(f"Erro: {e}")
                except AuthErro as e:
                    print(f"Erro: {e}")

            elif opc == "2":
                print("\n--- CADASTRO DE USUÁRIO ---")
                print("Digite 0 para cancelar.")

                email = _input_cancelavel("Email: ")
                if email is None:
                    continue

                senha = _input_cancelavel("Senha: ")
                if senha is None:
                    continue

                senha2 = _input_cancelavel("Repita a senha: ")
                if senha2 is None:
                    continue

                if senha != senha2:
                    print("As senhas não coincidem.")
                    continue

                pergunta = _input_cancelavel("Pergunta de recuperação: ")
                if pergunta is None:
                    continue

                resposta = _input_cancelavel("Resposta de recuperação: ")
                if resposta is None:
                    continue

                try:
                    user_id = auth.registrar_usuario(
                        email=email,
                        senha=senha,
                        pergunta=pergunta,
                        resposta=resposta
                    )
                    print(f"Usuário cadastrado com sucesso! ID: {user_id}")
                    print("Agora você já pode fazer login.")
                except UsuarioJaExiste as e:
                    print(f"Erro: {e}")
                except AuthErro as e:
                    print(f"Erro: {e}")

            elif opc == "3":
                print("\n--- ESQUECI A SENHA ---")
                print("Digite 0 para cancelar.")

                email = _input_cancelavel("Email: ")
                if email is None:
                    continue

                try:
                    pergunta = auth.obter_pergunta_recuperacao(email=email)
                except UsuarioNaoEncontrado as e:
                    print(f"Erro: {e}")
                    continue
                except AuthErro as e:
                    print(f"Erro: {e}")
                    continue

                print(f"Pergunta: {pergunta}")

                resposta = _input_cancelavel("Resposta: ")
                if resposta is None:
                    continue

                nova_senha = _input_cancelavel("Nova senha: ")
                if nova_senha is None:
                    continue

                nova_senha2 = _input_cancelavel("Repita a nova senha: ")
                if nova_senha2 is None:
                    continue

                if nova_senha != nova_senha2:
                    print("As senhas não coincidem.")
                    continue

                try:
                    auth.redefinir_senha(
                        email=email,
                        resposta=resposta,
                        nova_senha=nova_senha
                    )
                    print("Senha redefinida com sucesso! Agora faça login.")
                except RecuperacaoInvalida as e:
                    print(f"Erro: {e}")
                except AuthErro as e:
                    print(f"Erro: {e}")

            elif opc == "4":
                print("Saindo...")
                break
            else:
                print("Opção inválida.")

        else:
            sistema_ativos = SistemaAtivos(
                ativos_service=ativos_service,
                user_id=int(usuario_logado.id)
            )

            opc = _menu_ativos()

            if opc == "1":
                sistema_ativos.cadastrar_ativo()
            elif opc == "2":
                sistema_ativos.listar_ativos()
            elif opc == "3":
                sistema_ativos.buscar_ativo()
            elif opc == "4":
                sistema_ativos.editar_ativo()
            elif opc == "5":
                sistema_ativos.remover_ativo()
            elif opc == "6":
                print("Logout realizado.")
                usuario_logado = None
            else:
                print("Opção inválida.")


if __name__ == "__main__":
    executar()