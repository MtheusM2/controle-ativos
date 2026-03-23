import os
import base64
import hashlib
import hmac

PBKDF2_ALG = "sha256"
PBKDF2_ITERATIONS = int(os.getenv("PBKDF2_ITERATIONS", "600000"))
SALT_BYTES = 16


def _pepper() -> str:
    return os.getenv("APP_PEPPER", "")


def normalizar_resposta_recuperacao(resposta: str) -> str:
    return resposta.strip().lower()


def gerar_hash(segredo: str) -> str:
    salt = os.urandom(SALT_BYTES)
    segredo_bytes = (segredo + _pepper()).encode("utf-8")

    dk = hashlib.pbkdf2_hmac(
        PBKDF2_ALG,
        segredo_bytes,
        salt,
        PBKDF2_ITERATIONS
    )

    salt_b64 = base64.b64encode(salt).decode("utf-8")
    dk_b64 = base64.b64encode(dk).decode("utf-8")

    return f"pbkdf2_{PBKDF2_ALG}${PBKDF2_ITERATIONS}${salt_b64}${dk_b64}"


def verificar_hash(segredo: str, hash_armazenado: str) -> bool:
    try:
        esquema, iteracoes_str, salt_b64, dk_b64 = hash_armazenado.split("$", 3)
    except ValueError:
        return False

    if not esquema.startswith("pbkdf2_"):
        return False

    alg = esquema.replace("pbkdf2_", "", 1)

    try:
        iteracoes = int(iteracoes_str)
    except ValueError:
        return False

    try:
        salt = base64.b64decode(salt_b64.encode("utf-8"))
        dk_esperado = base64.b64decode(dk_b64.encode("utf-8"))
    except Exception:
        return False

    segredo_bytes = (segredo + _pepper()).encode("utf-8")
    dk_calculado = hashlib.pbkdf2_hmac(alg, segredo_bytes, salt, iteracoes)

    return hmac.compare_digest(dk_calculado, dk_esperado)