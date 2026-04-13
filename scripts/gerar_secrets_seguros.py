#!/usr/bin/env python3
"""
Gera valores seguros para secrets em producao.

Uso:
    python scripts/gerar_secrets_seguros.py

Saída:
    - FLASK_SECRET_KEY: chave para sessao Flask
    - APP_PEPPER: pepper para hash de senha
    - DB_PASSWORD: senha do banco de dados (opcional)

Todos os valores sao aleatórios e seguros.
"""

import secrets
import sys


def gerar_token_hex(tamanho: int = 32) -> str:
    """Gera token hexadecimal seguro."""
    return secrets.token_hex(tamanho)


def gerar_senha_urlsafe(tamanho: int = 32) -> str:
    """Gera senha URL-safe segura."""
    return secrets.token_urlsafe(tamanho)


def main():
    """Gera e exibe secrets seguros."""
    print("=" * 80)
    print("GERADOR DE SECRETS SEGUROS PARA PRODUCAO")
    print("=" * 80)
    print()

    # FLASK_SECRET_KEY - usar para sessao Flask
    flask_secret = gerar_token_hex(32)
    print("FLASK_SECRET_KEY (para sessao e cookies):")
    print(flask_secret)
    print()

    # APP_PEPPER - usar para hash de senha
    app_pepper = gerar_token_hex(32)
    print("APP_PEPPER (para hash de senha com PBKDF2):")
    print(app_pepper)
    print()

    # DB_PASSWORD - senha do banco (mais restritivo que token_hex)
    db_password = gerar_senha_urlsafe(32)
    print("DB_PASSWORD (para autenticacao no banco):")
    print(db_password)
    print()

    print("=" * 80)
    print("PROXIMOS PASSOS:")
    print("=" * 80)
    print()
    print("1. Copie os valores acima")
    print()
    print("2. Configure como variaveis de ambiente do Windows (Admin):")
    print()
    print("   setx FLASK_SECRET_KEY \"<valor_acima>\" /M")
    print("   setx APP_PEPPER \"<valor_acima>\" /M")
    print("   setx DB_PASSWORD \"<valor_acima>\" /M")
    print()
    print("3. Altere a senha do usuario 'opus_app' no MySQL:")
    print()
    print("   mysql -u root -p")
    print("   ALTER USER 'opus_app'@'localhost' IDENTIFIED BY '<DB_PASSWORD_acima>';")
    print("   FLUSH PRIVILEGES;")
    print()
    print("4. Reinicie o servico Windows ou abra novo terminal para validar carregamento.")
    print()
    print("=" * 80)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
