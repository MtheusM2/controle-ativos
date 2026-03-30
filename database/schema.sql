# main.py

# Ponto de entrada da interface CLI do sistema.
# Nesta etapa, o cadastro via terminal passa a exigir a escolha
# da empresa do usuário, alinhando CLI e web com o novo modelo
# corporativo de acesso.

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
from services.empresa_service import EmpresaService


def _input_cancelavel(mensagem: str) -> str | None:
    """
    Lê um valor do terminal e permite cancelamento com 0.
    """
    valor = input(mensagem).strip()

    if valor == "0":
        return None

    return valor


def _selecionar_empresa_cli(empresa_service: EmpresaService) -> int | None:
    """
    Exibe as empresas disponíveis e solicita ao usuário
    o ID da empresa desejada.
    """
    empresas = empresa_service.listar_empresas_ativas()

    if not empresas:
        print("Nenhuma empresa ativa cadastrada no sistema.")
        return None

    print("\nEmpresas disponíveis:")
    for empresa in empresas:
        print(f"{empresa['id']} - {empresa['nome']} ({empresa['codigo']})")

    empresa_id = _input_cancelavel("ID da empresa: ")
    if empresa_id is None:
        return None

    try:
        return int(empresa_id)
    except ValueError:
        print("ID de empresa inválido.")
        return None


def menu_auth():
    """
    Exibe o menu principal de autenticação.
    """
    print("\n=== AUTENTICAÇÃO ===")
    print("1 - Login")
    print("2 - Cadastro")
    print("3 - Recuperar senha")
    print("4 - Sair")
    return input("Opção: ").strip()


def menu_ativos():
    """
    Exibe o menu do módulo de ativos.
    """
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
    """
    Loop principal do sistema CLI.
    """
    auth = AuthService()
    ativos_service = AtivosService()
    empresa_service = EmpresaService()
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
                    print(
                        "Login realizado com sucesso. "
                        f"Bem-vindo(a), {usuario.email}. "
                        f"Perfil: {usuario.perfil}. "
                        f"Empresa: {usuario.empresa_nome}."
                    )
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

                empresa_id = _selecionar_empresa_cli(empresa_service)
                if empresa_id is None:
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
                    user_id = auth.registrar_usuario(
                        email=email,
                        senha=senha,
                        pergunta=pergunta,
                        resposta=resposta,
                        empresa_id=empresa_id,
                        perfil="usuario"
                    )
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