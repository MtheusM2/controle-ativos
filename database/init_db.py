from pathlib import Path

from database.connection import conexao_mysql


def inicializar_banco():
    schema_path = Path(__file__).with_name("schema.sql")
    sql = schema_path.read_text(encoding="utf-8")

    comandos = [cmd.strip() for cmd in sql.split(";") if cmd.strip()]

    with conexao_mysql(com_database=False) as conn:
        cur = conn.cursor()
        try:
            for comando in comandos:
                cur.execute(comando)
            print("Banco e tabelas criados com sucesso.")
        except Exception as e:
            print("Erro ao criar banco/tabelas:")
            print(e)
            raise
        finally:
            cur.close()


if __name__ == "__main__":
    inicializar_banco()