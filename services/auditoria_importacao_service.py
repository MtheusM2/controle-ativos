# services/auditoria_importacao_service.py
#
# Serviço de auditoria e reversão de importações.
# Gerencia log de importações, detecção de duplicatas e reversão segura.
#
# Responsabilidades:
# - Criar registro de auditoria para cada importação
# - Detectar duplicatas e IDs existentes
# - Registrar linhas rejeitadas
# - Permitir reversão por 7 dias (apenas admin)
# - Gerar relatórios de importação
#

import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from uuid import uuid4

from database.connection import cursor_mysql


class AuditoriaImportacaoService:
    """Gerencia logs e reversão de importações"""

    @staticmethod
    def gerar_id_lote() -> str:
        """
        Gera ID único para lote de importação.
        Formato: IMP-2026-04-22-14-32-10-XXXX
        """
        agora = datetime.utcnow()
        uuid_curto = str(uuid4())[:8].upper()
        return f"IMP-{agora.strftime('%Y-%m-%d-%H-%M-%S')}-{uuid_curto}"

    @staticmethod
    def iniciar_auditoria(
        usuario_id: int,
        empresa_id: int,
        hash_arquivo: str,
        nome_arquivo: str,
        tamanho_bytes: int,
        endereco_ip: str,
        user_agent: str,
        total_linhas: int = 0
    ) -> str:
        """
        Cria registro inicial de auditoria (status: pendente).

        Args:
            total_linhas: Total de linhas do arquivo (padrão: 0, atualizado em registrar_preview_gerado)

        Returns:
            id_lote para rastreabilidade
        """
        id_lote = AuditoriaImportacaoService.gerar_id_lote()

        with cursor_mysql() as (conn, cur):
            cur.execute("""
                INSERT INTO auditoria_importacoes (
                    id_lote, usuario_id, empresa_id,
                    hash_arquivo, nome_arquivo_original, tamanho_arquivo_bytes,
                    total_linhas_arquivo,
                    status, endereco_ip, user_agent, timestamp_inicio
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """, [
                id_lote, usuario_id, empresa_id,
                hash_arquivo, nome_arquivo, tamanho_bytes,
                total_linhas,
                'pendente', endereco_ip, user_agent
            ])

        return id_lote

    @staticmethod
    def registrar_preview_gerado(
        id_lote: str,
        delimitador: str,
        numero_linha_cabecalho: int,
        score_deteccao_cabecalho: float,
        total_linhas: int,
        dados_bloqueios: Optional[List] = None,
        dados_avisos: Optional[List] = None
    ) -> None:
        """
        Atualiza registro após preview gerado.
        """
        with cursor_mysql() as (conn, cur):
            status = 'bloqueado' if dados_bloqueios else 'preview_ok'

            cur.execute("""
                UPDATE auditoria_importacoes
                SET
                    delimitador_csv = %s,
                    numero_linha_cabecalho = %s,
                    score_deteccao_cabecalho = %s,
                    total_linhas_arquivo = %s,
                    dados_bloqueios = %s,
                    dados_avisos = %s,
                    status = %s,
                    timestamp_preview_gerado = NOW()
                WHERE id_lote = %s
            """, [
                delimitador,
                numero_linha_cabecalho,
                score_deteccao_cabecalho,
                total_linhas,
                json.dumps(dados_bloqueios or []),
                json.dumps(dados_avisos or []),
                status,
                id_lote
            ])

    @staticmethod
    def registrar_confirmacao(
        id_lote: str,
        modo_duplicata: str
    ) -> None:
        """
        Registra confirmação do usuário (4 checkboxes).
        """
        with cursor_mysql() as (conn, cur):
            cur.execute("""
                UPDATE auditoria_importacoes
                SET
                    modo_duplicata = %s,
                    status = 'importando',
                    timestamp_confirmacao = NOW()
                WHERE id_lote = %s
            """, [modo_duplicata, id_lote])

    @staticmethod
    def registrar_resultado_importacao(
        id_lote: str,
        linhas_importadas: int,
        linhas_rejeitadas: int,
        linhas_com_aviso: int,
        linhas_atualizadas: int,
        ids_ativos_afetados: List[str],
        mensagem_erro: Optional[str] = None
    ) -> None:
        """
        Atualiza registro após importação concluída.
        """
        if mensagem_erro:
            status = 'erro'
        elif linhas_rejeitadas > 0:
            status = 'sucesso_parcial'
        else:
            status = 'sucesso'

        with cursor_mysql() as (conn, cur):
            cur.execute("""
                UPDATE auditoria_importacoes
                SET
                    linhas_importadas = %s,
                    linhas_rejeitadas = %s,
                    linhas_com_aviso = %s,
                    linhas_atualizadas = %s,
                    ids_ativos_afetados = %s,
                    status = %s,
                    mensagem_erro = %s,
                    timestamp_conclusao = NOW(),
                    pode_reverter = 1
                WHERE id_lote = %s
            """, [
                linhas_importadas,
                linhas_rejeitadas,
                linhas_com_aviso,
                linhas_atualizadas,
                json.dumps(ids_ativos_afetados),
                status,
                mensagem_erro,
                id_lote
            ])

    @staticmethod
    def registrar_linha_rejeitada(
        id_lote: str,
        numero_linha: int,
        id_ativo_csv: Optional[str],
        motivo: str,
        avisos: Optional[List] = None,
        campos_processados: Optional[Dict] = None
    ) -> None:
        """
        Registra linha individual que foi rejeitada.
        """
        with cursor_mysql() as (conn, cur):
            cur.execute("""
                INSERT INTO auditoria_importacoes_linhas (
                    id_lote, numero_linha, status,
                    id_ativo_csv, motivo_rejeicao,
                    avisos, campos_processados
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, [
                id_lote, numero_linha, 'rejeitada',
                id_ativo_csv, motivo,
                json.dumps(avisos or []),
                json.dumps(campos_processados or {})
            ])

    @staticmethod
    def registrar_linha_importada(
        id_lote: str,
        numero_linha: int,
        id_ativo_csv: str,
        id_ativo_criado: str,
        operacao: str,  # 'INSERT' ou 'UPDATE'
        avisos: Optional[List] = None
    ) -> None:
        """
        Registra linha que foi importada com sucesso.
        """
        with cursor_mysql() as (conn, cur):
            cur.execute("""
                INSERT INTO auditoria_importacoes_linhas (
                    id_lote, numero_linha, status,
                    id_ativo_csv, id_ativo_criado, avisos
                ) VALUES (%s, %s, %s, %s, %s, %s)
            """, [
                id_lote, numero_linha,
                'atualizada' if operacao == 'UPDATE' else 'importada',
                id_ativo_csv, id_ativo_criado,
                json.dumps(avisos or [])
            ])

    @staticmethod
    def detectar_duplicatas(
        ids_csv: List[str],
        empresa_id: int
    ) -> Dict[str, List[str]]:
        """
        Detecta IDs que já existem no banco para esta empresa.

        Returns:
            {id_csv: [id_existente_similar, ...], ...}
        """
        if not ids_csv:
            return {}

        duplicatas = {}

        with cursor_mysql() as (conn, cur):
            # Match exato por ID
            placeholders = ','.join(['%s'] * len(ids_csv))
            cur.execute(f"""
                SELECT id FROM ativos
                WHERE empresa_id = %s AND id IN ({placeholders})
            """, [empresa_id] + ids_csv)

            existentes = {row['id'] for row in cur.fetchall()}

            for id_csv in ids_csv:
                if id_csv in existentes:
                    duplicatas[id_csv] = [id_csv]

        return duplicatas

    @staticmethod
    def detectar_seriais_duplicados(
        seriais_csv: List[str],
        empresa_id: int
    ) -> Dict[str, str]:
        """
        Detecta seriais que já existem (possível equipamento mesmo).

        Returns:
            {serial_csv: id_ativo_existente, ...}
        """
        if not seriais_csv:
            return {}

        seriais_unicos = [s for s in seriais_csv if s and s.strip()]
        if not seriais_unicos:
            return {}

        duplicatas = {}

        with cursor_mysql() as (conn, cur):
            placeholders = ','.join(['%s'] * len(seriais_unicos))
            cur.execute(f"""
                SELECT id, serial FROM ativos
                WHERE empresa_id = %s AND serial IN ({placeholders})
            """, [empresa_id] + seriais_unicos)

            for row in cur.fetchall():
                serial = row['serial']
                if serial in seriais_unicos:
                    duplicatas[serial] = row['id']

        return duplicatas

    @staticmethod
    def obter_usuarios_validos(empresa_id: int) -> set:
        """
        Retorna set de nomes de usuários válidos para esta empresa.
        Usado para validar usuario_responsavel.
        """
        with cursor_mysql() as (conn, cur):
            cur.execute("""
                SELECT nome FROM usuarios WHERE empresa_id = %s
            """, [empresa_id])

            return {row['nome'] for row in cur.fetchall()}

    @staticmethod
    def reverter_lote(
        id_lote: str,
        usuario_admin_id: int,
        motivo: str
    ) -> Dict:
        """
        Reverte uma importação completa (deleta ativos criados).

        Pré-requisitos:
        - Usuário é admin
        - Lote foi importado há < 7 dias
        - Status = sucesso ou sucesso_parcial

        Returns:
            {ok: bool, mensagem: str, ids_deletados: [...]}

        Raises:
            ValueError se pré-requisitos não atendidos
            PermissionError se usuário não é admin
        """
        with cursor_mysql() as (conn, cur):
            # 1. Buscar lote
            cur.execute("""
                SELECT * FROM auditoria_importacoes WHERE id_lote = %s
            """, [id_lote])

            lote = cur.fetchone()
            if not lote:
                raise ValueError(f"Lote {id_lote} não encontrado")

            # 2. Validar status
            if lote['status'] not in ('sucesso', 'sucesso_parcial'):
                raise ValueError(f"Lote {id_lote} não pode ser revertido (status={lote['status']})")

            # 3. Validar prazo (< 7 dias)
            tempo_decorrido = datetime.utcnow() - lote['timestamp_conclusao']
            if tempo_decorrido.days >= 7:
                raise ValueError(f"Prazo de reversão expirado (>{7} dias)")

            # 4. Extrair IDs afetados
            ids_afetados = json.loads(lote['ids_ativos_afetados'] or '[]')
            if not ids_afetados:
                raise ValueError(f"Nenhum ID registrado para reversão em {id_lote}")

            # 5. Deletar em transação
            try:
                for ativo_id in ids_afetados:
                    # Usar variável de sessão para registrar quem deletou
                    cur.execute("SET @usuario_id = %s", [usuario_admin_id])
                    cur.execute("SET @id_lote = %s", [id_lote])

                    cur.execute("""
                        DELETE FROM ativos
                        WHERE id = %s AND empresa_id = %s
                    """, [ativo_id, lote['empresa_id']])

                # 6. Registrar reversão
                cur.execute("""
                    UPDATE auditoria_importacoes
                    SET
                        status = 'revertido',
                        reversao_em = NOW(),
                        reversao_por = %s,
                        reversao_motivo = %s,
                        pode_reverter = 0
                    WHERE id_lote = %s
                """, [usuario_admin_id, motivo, id_lote])

            except Exception as e:
                raise ValueError(f"Erro ao reverter lote: {str(e)}")

        return {
            "ok": True,
            "mensagem": f"Lote {id_lote} revertido. {len(ids_afetados)} ativos deletados.",
            "ids_deletados": ids_afetados
        }

    @staticmethod
    def obter_relatorio_importacao(id_lote: str) -> Dict:
        """
        Retorna relatório completo de importação.
        """
        with cursor_mysql() as (conn, cur):
            cur.execute("""
                SELECT * FROM auditoria_importacoes WHERE id_lote = %s
            """, [id_lote])

            lote = cur.fetchone()
            if not lote:
                return {"ok": False, "erro": f"Lote {id_lote} não encontrado"}

            # Buscar linhas rejeitadas
            cur.execute("""
                SELECT * FROM auditoria_importacoes_linhas
                WHERE id_lote = %s AND status = 'rejeitada'
                LIMIT 50
            """, [id_lote])

            linhas_rejeitadas = cur.fetchall()

            return {
                "ok": True,
                "lote": {
                    "id_lote": lote['id_lote'],
                    "usuario_id": lote['usuario_id'],
                    "empresa_id": lote['empresa_id'],
                    "status": lote['status'],
                    "total_linhas": lote['total_linhas_arquivo'],
                    "importadas": lote['linhas_importadas'],
                    "rejeitadas": lote['linhas_rejeitadas'],
                    "com_aviso": lote['linhas_com_aviso'],
                    "atualizadas": lote['linhas_atualizadas'],
                    "taxa_erro": f"{(lote['linhas_rejeitadas'] / lote['total_linhas_arquivo'] * 100):.1f}%"
                        if lote['total_linhas_arquivo'] else "0%",
                    "timestamp_conclusao": lote['timestamp_conclusao'].isoformat()
                        if lote['timestamp_conclusao'] else None,
                    "pode_reverter": bool(lote['pode_reverter']),
                    "dias_reversao_restantes": lote['dias_reverter_restantes'],
                    "mensagem_erro": lote['mensagem_erro']
                },
                "rejeicoes": [
                    {
                        "numero_linha": r['numero_linha'],
                        "id_ativo": r['id_ativo_csv'],
                        "motivo": r['motivo_rejeicao']
                    }
                    for r in linhas_rejeitadas
                ]
            }

    @staticmethod
    def obter_importacoes_usuario(
        usuario_id: int,
        empresa_id: int,
        limite: int = 20
    ) -> List[Dict]:
        """
        Retorna últimas importações de um usuário.
        """
        with cursor_mysql() as (conn, cur):
            cur.execute("""
                SELECT
                    id_lote, status, total_linhas_arquivo,
                    linhas_importadas, linhas_rejeitadas,
                    timestamp_conclusao
                FROM auditoria_importacoes
                WHERE usuario_id = %s AND empresa_id = %s
                ORDER BY timestamp_conclusao DESC
                LIMIT %s
            """, [usuario_id, empresa_id, limite])

            return cur.fetchall()
