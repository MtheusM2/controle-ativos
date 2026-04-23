#!/usr/bin/env python3
"""
Script de diagnostico profundo da importacao em massa.

Objetivo: Analisar por que uma planilha real foi bloqueada na importacao web.
Mostra:
- Cada coluna e sua classificacao
- Cada linha e quais campos estao falhando
- Valores rejeitados e por que
- Recomendacoes de correcao

Uso:
  python scripts/diagnostico_profundo_importacao.py <caminho_csv>

Exemplo:
  python scripts/diagnostico_profundo_importacao.py planilha_real.csv
  python scripts/diagnostico_profundo_importacao.py "C:/Downloads/ativos.csv"
"""

import sys
import os
import csv
from collections import defaultdict
from datetime import datetime

script_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(script_dir)
sys.path.insert(0, root_dir)

from services.ativos_service import AtivosService, AtivoErro
from utils.validators import (
    STATUS_VALIDOS,
    padronizar_texto,
    validar_id_ativo,
)

# Valores validos do dominio (extraidos do schema e validadores)
# AUDITORIA 2026-04-22: Normalizado para Title Case para compatibilidade com .title() em validação
SETORES_VALIDOS = [
    "T.I", "Rh", "Adm", "Financeiro", "Vendas", "Marketing",
    "Infraestrutura", "Apoio", "Estagiarios", "Diretoria",
    "Manutencao", "Tecnica", "Logistica", "Licitacao"
]

TIPOS_ATIVO_VALIDOS = [
    "Notebook", "Desktop", "Celular", "Monitor", "Mouse",
    "Teclado", "Headset", "Adaptador", "Cabo", "Carregador", "Outro"
]

STATUS_VALIDOS_STR = [
    "Disponivel", "Em Uso", "Em Manutencao", "Reservado", "Baixado",
    # Tambem aceita com acentos
    "Disponível", "Em Manutenção",
]


def ler_csv_bruto(caminho_arquivo: str) -> tuple[list[str], list[dict]]:
    """
    Le CSV em formato bruto (sem processamento).
    Retorna: (headers, linhas como dicts)
    """
    try:
        with open(caminho_arquivo, 'r', encoding='utf-8') as f:
            leitor = csv.DictReader(f)
            headers = leitor.fieldnames
            linhas = list(leitor)
        return list(headers), linhas
    except UnicodeDecodeError:
        # Tenta com encoding diferente
        with open(caminho_arquivo, 'r', encoding='latin-1') as f:
            leitor = csv.DictReader(f)
            headers = leitor.fieldnames
            linhas = list(leitor)
        return list(headers), linhas


def classificar_coluna(header: str) -> dict:
    """
    Classifica uma coluna do CSV contra o contrato esperado.
    Retorna: {tipo, campo_esperado, motivo, recomendacao}
    """
    header_norm = header.lower().strip()

    # Mapeamento exato
    mapeamento_exato = {
        "tipo_ativo": "tipo_ativo",
        "tipo": "tipo_ativo",
        "marca": "marca",
        "modelo": "modelo",
        "serial": "serial",
        "codigo_interno": "codigo_interno",
        "setor": "setor",
        "departamento": "departamento",
        "status": "status",
        "data_entrada": "data_entrada",
        "usuario_responsavel": "usuario_responsavel",
        "responsavel": "usuario_responsavel",
        "email_responsavel": "email_responsavel",
        "teamviewer_id": "teamviewer_id",
        "anydesk_id": "anydesk_id",
        "numero_linha": "numero_linha",
        "operadora": "operadora",
        "imei": "BLOQUEADA",
        "imei_1": "BLOQUEADA",
        "imei_2": "BLOQUEADA",
        "pc": "IGNORADA",
        "password": "BLOQUEADA (sensivel)",
        "senha": "BLOQUEADA (sensivel)",
        "pin": "BLOQUEADA (sensivel)",
    }

    # Verificar correspondencia exata
    if header_norm in mapeamento_exato:
        campo = mapeamento_exato[header_norm]
        if campo == "BLOQUEADA":
            return {
                "tipo": "BLOQUEADA",
                "campo": None,
                "motivo": "Coluna nao faz parte do dominio",
                "recomendacao": "Remover do CSV"
            }
        elif campo == "IGNORADA":
            return {
                "tipo": "IGNORADA",
                "campo": None,
                "motivo": "Coluna ignora conforme contrato",
                "recomendacao": "Pode manter (sera ignorada)"
            }
        elif campo.startswith("BLOQUEADA"):
            return {
                "tipo": "BLOQUEADA",
                "campo": None,
                "motivo": campo,
                "recomendacao": "Remover do CSV"
            }
        else:
            return {
                "tipo": "EXATA",
                "campo": campo,
                "motivo": "Correspondencia exata",
                "recomendacao": None
            }

    # Mapeamento sugerido (semantico)
    sugestoes = {
        "teamviewer id": "teamviewer_id",
        "teamviewer_id": "teamviewer_id",
        "anydesk id": "anydesk_id",
        "anydesk_id": "anydesk_id",
        "responsavel_por": "usuario_responsavel",
        "responsavel": "usuario_responsavel",
        "responsavel por": "usuario_responsavel",
        "email responsavel": "email_responsavel",
    }

    if header_norm in sugestoes:
        return {
            "tipo": "SUGERIDA",
            "campo": sugestoes[header_norm],
            "motivo": "Semelhanca de nomenclatura",
            "recomendacao": "Requer confirmacao do usuario"
        }

    # Se chegou aqui, coluna nao tem correspondencia valida
    return {
        "tipo": "SEM_CORRESPONDENCIA",
        "campo": None,
        "motivo": "Nenhuma correspondencia encontrada",
        "recomendacao": "Renomear coluna conforme contrato ou remover"
    }


def validar_linha_contra_dominio(linha: dict, numero_linha: int, headers: list[str]) -> tuple[bool, list[str]]:
    """
    Valida uma linha contra o dominio esperado.
    Retorna: (valida, lista_de_erros)
    """
    erros = []

    # Campos obrigatorios
    campos_obrigatorios = {
        "tipo_ativo": ("tipo_ativo", TIPOS_ATIVO_VALIDOS),
        "status": ("status", STATUS_VALIDOS_STR),
        "data_entrada": ("data_entrada", None),  # Validacao especial
        "setor": ("setor", SETORES_VALIDOS),
    }

    for header in headers:
        header_norm = header.lower().strip()
        valor = linha.get(header, "").strip()

        # Pular colunas vazias
        if not valor:
            continue

        # Validar tipo_ativo
        if header_norm == "tipo_ativo" or header_norm == "tipo":
            if valor not in TIPOS_ATIVO_VALIDOS:
                erros.append(
                    f"Campo 'tipo_ativo': valor '{valor}' invalido. "
                    f"Esperado um destes: {', '.join(TIPOS_ATIVO_VALIDOS)}"
                )

        # Validar status
        elif header_norm == "status":
            # Normalizacao: aceita com ou sem acento
            status_encontrado = False
            for status_valido in STATUS_VALIDOS_STR:
                if valor.lower() == status_valido.lower():
                    status_encontrado = True
                    break

            if not status_encontrado:
                erros.append(
                    f"Campo 'status': valor '{valor}' invalido. "
                    f"Esperado um destes: {', '.join(set(STATUS_VALIDOS_STR))}"
                )

        # Validar setor
        elif header_norm == "setor":
            if valor not in SETORES_VALIDOS:
                # Tenta busca fuzzy
                matches = [s for s in SETORES_VALIDOS if s.lower() == valor.lower()]
                if not matches:
                    erros.append(
                        f"Campo 'setor': valor '{valor}' invalido. "
                        f"Esperado um destes: {', '.join(SETORES_VALIDOS)}"
                    )

        # Validar data_entrada (formato YYYY-MM-DD)
        elif header_norm == "data_entrada":
            if valor:
                try:
                    partes = valor.split('-')
                    if len(partes) != 3:
                        raise ValueError()
                    ano = int(partes[0])
                    mes = int(partes[1])
                    dia = int(partes[2])
                    if not (1 <= mes <= 12 and 1 <= dia <= 31):
                        raise ValueError()
                except (ValueError, IndexError):
                    erros.append(
                        f"Campo 'data_entrada': valor '{valor}' invalido. "
                        f"Formato esperado: YYYY-MM-DD (ex: 2026-04-17)"
                    )

        # Validar IMEI (deve estar ausente)
        elif header_norm in ["imei", "imei_1", "imei_2"]:
            # Nao e erro, mas aviso
            pass

    return len(erros) == 0, erros


class DiagnosticadorProfundo:
    """
    Diagnostico profundo e estruturado de um CSV de importacao.
    """

    def __init__(self, caminho_arquivo: str):
        self.caminho = caminho_arquivo
        self.headers = []
        self.linhas = []
        self.relatorio = {
            "arquivo": caminho_arquivo,
            "timestamp": datetime.now().isoformat(),
            "analise_colunas": {},
            "analise_linhas": {},
            "resumo_erros": defaultdict(list),
            "recomendacoes": [],
        }

    def executar(self):
        """Executa diagnostico completo."""
        print(f"\n{'='*80}")
        print(f"DIAGNOSTICO PROFUNDO DE IMPORTACAO")
        print(f"Arquivo: {self.caminho}")
        print(f"{'='*80}\n")

        # Verificar existencia
        if not os.path.exists(self.caminho):
            print(f"ERRO: Arquivo nao encontrado: {self.caminho}")
            return False

        # Ler CSV
        print("[1/4] Lendo arquivo CSV...")
        try:
            self.headers, self.linhas = ler_csv_bruto(self.caminho)
            print(f"  OK: {len(self.headers)} colunas, {len(self.linhas)} linhas de dados")
        except Exception as e:
            print(f"  ERRO: {e}")
            return False

        # Analisar colunas
        print("\n[2/4] Analisando colunas...")
        self._analisar_colunas()

        # Analisar linhas
        print("\n[3/4] Validando linhas contra dominio...")
        self._validar_linhas()

        # Gerar relatorio
        print("\n[4/4] Gerando relatorio...")
        self._gerar_relatorio()

        return True

    def _analisar_colunas(self):
        """Classifica cada coluna do CSV."""
        exatas = []
        sugeridas = []
        ignoradas = []
        bloqueadas = []
        sem_correspondencia = []

        for header in self.headers:
            classificacao = classificar_coluna(header)
            self.relatorio["analise_colunas"][header] = classificacao

            tipo = classificacao["tipo"]
            if tipo == "EXATA":
                exatas.append((header, classificacao["campo"]))
            elif tipo == "SUGERIDA":
                sugeridas.append((header, classificacao["campo"]))
            elif tipo == "IGNORADA":
                ignoradas.append(header)
            elif tipo == "BLOQUEADA":
                bloqueadas.append((header, classificacao["motivo"]))
            else:
                sem_correspondencia.append(header)

        # Exibir resultado
        print(f"\n  COLUNAS EXATAS ({len(exatas)}):")
        if exatas:
            for orig, dest in exatas:
                print(f"    [OK] {orig} -> {dest}")
        else:
            print("    (nenhuma)")

        print(f"\n  COLUNAS SUGERIDAS ({len(sugeridas)}):")
        if sugeridas:
            for orig, dest in sugeridas:
                print(f"    [~] {orig} -> {dest} (requer confirmacao)")
        else:
            print("    (nenhuma)")

        print(f"\n  COLUNAS IGNORADAS ({len(ignoradas)}):")
        if ignoradas:
            for col in ignoradas:
                print(f"    [-] {col}")
        else:
            print("    (nenhuma)")

        print(f"\n  COLUNAS BLOQUEADAS ({len(bloqueadas)}):")
        if bloqueadas:
            for col, motivo in bloqueadas:
                print(f"    [BLOQ] {col} ({motivo})")
        else:
            print("    (nenhuma)")

        print(f"\n  COLUNAS SEM CORRESPONDENCIA ({len(sem_correspondencia)}):")
        if sem_correspondencia:
            for col in sem_correspondencia:
                print(f"    [?] {col}")
        else:
            print("    (nenhuma)")

    def _validar_linhas(self):
        """Valida cada linha contra o dominio."""
        total_linhas = len(self.linhas)
        linhas_validas = 0
        linhas_com_erro = 0
        erros_por_tipo = defaultdict(int)

        for idx, linha in enumerate(self.linhas, start=2):  # Comeca em 2 (header é 1)
            valida, erros = validar_linha_contra_dominio(linha, idx, self.headers)

            if valida:
                linhas_validas += 1
                self.relatorio["analise_linhas"][idx] = {
                    "valida": True,
                    "erros": []
                }
            else:
                linhas_com_erro += 1
                self.relatorio["analise_linhas"][idx] = {
                    "valida": False,
                    "erros": erros
                }
                # Agrupar erros
                for erro in erros:
                    tipo_erro = erro.split(":")[0]
                    self.relatorio["resumo_erros"][tipo_erro].append((idx, erro))
                    erros_por_tipo[tipo_erro] += 1

        # Exibir resultado
        print(f"\n  Linhas validas: {linhas_validas}/{total_linhas} ({100*linhas_validas//total_linhas}%)")
        print(f"  Linhas com erro: {linhas_com_erro}/{total_linhas} ({100*linhas_com_erro//total_linhas}%)")

        if erros_por_tipo:
            print(f"\n  ERROS ENCONTRADOS:")
            for tipo_erro, count in sorted(erros_por_tipo.items(), key=lambda x: -x[1]):
                print(f"    - {tipo_erro}: {count} linhas afetadas")

    def _gerar_relatorio(self):
        """Gera e exibe relatorio detalhado."""
        print(f"\n{'='*80}")
        print(f"RELATORIO DETALHADO")
        print(f"{'='*80}")

        # Resumo por tipo de erro
        if self.relatorio["resumo_erros"]:
            print(f"\nERROS AGRUPADOS POR TIPO:")
            for tipo_erro in sorted(self.relatorio["resumo_erros"].keys()):
                erros = self.relatorio["resumo_erros"][tipo_erro]
                print(f"\n  [{tipo_erro}] - {len(erros)} ocorrencias:")
                # Mostrar primeiras 5
                for linha_num, erro in erros[:5]:
                    print(f"    Linha {linha_num}: {erro}")
                if len(erros) > 5:
                    print(f"    ... e mais {len(erros) - 5} linhas com este erro")

        # Detalhes de algumas linhas falhando
        print(f"\nEXEMPLOS DE LINHAS COM ERRO:")
        erros_para_mostrar = list(self.relatorio["analise_linhas"].items())
        linhas_com_erro = [l for l, info in erros_para_mostrar if not info["valida"]][:3]

        for num_linha in linhas_com_erro:
            info = self.relatorio["analise_linhas"][num_linha]
            print(f"\n  Linha {num_linha}:")
            for erro in info["erros"]:
                print(f"    - {erro}")

        # Recomendacoes
        self._gerar_recomendacoes()

    def _gerar_recomendacoes(self):
        """Gera recomendacoes baseado na analise."""
        recomendacoes = []

        # Verificar bloqueadas
        bloqueadas = [h for h, c in self.relatorio["analise_colunas"].items()
                     if c["tipo"] == "BLOQUEADA"]
        if bloqueadas:
            recomendacoes.append(
                f"REMOVER {len(bloqueadas)} COLUNA(S) BLOQUEADA(S): {', '.join(bloqueadas)}"
            )

        # Verificar sem correspondencia
        sem_corr = [h for h, c in self.relatorio["analise_colunas"].items()
                   if c["tipo"] == "SEM_CORRESPONDENCIA"]
        if sem_corr:
            recomendacoes.append(
                f"RENOMEAR OU REMOVER {len(sem_corr)} COLUNA(S) SEM CORRESPONDENCIA: {', '.join(sem_corr)}"
            )

        # Verificar sugeridas
        sugeridas = [h for h, c in self.relatorio["analise_colunas"].items()
                    if c["tipo"] == "SUGERIDA"]
        if sugeridas:
            recomendacoes.append(
                f"CONFIRMAR SUGESTOES: {len(sugeridas)} coluna(s) serao mapeadas se confirmado"
            )

        # Verificar erros de dominio
        if self.relatorio["resumo_erros"]:
            total_erro_dominio = sum(len(v) for k, v in self.relatorio["resumo_erros"].items()
                                    if "invalido" in k.lower())
            if total_erro_dominio > 0:
                recomendacoes.append(
                    f"CORRIGIR VALORES DE DOMINIO: {total_erro_dominio} linhas tem valores invalidos"
                )

        print(f"\n{'='*80}")
        print(f"RECOMENDACOES")
        print(f"{'='*80}\n")

        if recomendacoes:
            for i, rec in enumerate(recomendacoes, 1):
                print(f"{i}. {rec}\n")
        else:
            print("Nenhuma recomendacao (planilha parece estar OK)")

        self.relatorio["recomendacoes"] = recomendacoes


def main():
    """Ponto de entrada."""
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nUsage:")
        print(f"  python {sys.argv[0]} <caminho_csv>")
        print(f"\nExemplo:")
        print(f"  python {sys.argv[0]} planilha_real.csv")
        print(f"  python {sys.argv[0]} \"C:/Downloads/ativos.csv\"")
        return 1

    caminho = sys.argv[1]
    diag = DiagnosticadorProfundo(caminho)
    sucesso = diag.executar()

    return 0 if sucesso else 1


if __name__ == "__main__":
    sys.exit(main())
