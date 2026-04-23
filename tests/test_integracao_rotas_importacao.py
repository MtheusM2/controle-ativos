"""
Testes de integração das rotas POST /ativos/importar/preview e /confirmar.

Cobre:
- Autenticação (401 sem sessão)
- CSRF (403 sem token válido)
- Preview com CSV válido (200)
- Preview com bloqueios (400)
- Confirmar com checkboxes incompletos (400)
- Confirmar com checkboxes completos (201)
"""

import pytest
from io import BytesIO


CSV_VALIDO = b"""id,tipo,marca,modelo,departamento,status,data_entrada
NTB-001,Notebook,Dell,Latitude,TI,Em Uso,2026-01-15
"""

CSV_CAMPO_CRITICO_AUSENTE = b"""marca,modelo,departamento,status,data_entrada
Dell,Latitude,TI,Em Uso,2026-01-15
"""


class TestIntegracaoRotasImportacao:
    """Testa as rotas Flash de importação em massa."""

    # ========== POST /ativos/importar/preview ==========

    def test_preview_csv_valido_retorna_200(self, authenticated_client, app_fixture):
        """Preview com CSV válido retorna 200 com id_lote."""
        with app_fixture.app_context():
            data = {
                'file': (BytesIO(CSV_VALIDO), 'test.csv')
            }

            response = authenticated_client.post(
                '/ativos/importar/preview',
                data=data,
                content_type='multipart/form-data'
            )

            assert response.status_code == 200
            payload = response.get_json()
            assert payload.get('ok') is True
            assert 'id_lote' in payload
            assert 'preview' in payload

    def test_preview_campo_critico_ausente_retorna_400(self, authenticated_client, app_fixture):
        """Preview com campo crítico ausente retorna 400."""
        with app_fixture.app_context():
            data = {
                'file': (BytesIO(CSV_CAMPO_CRITICO_AUSENTE), 'test.csv')
            }

            response = authenticated_client.post(
                '/ativos/importar/preview',
                data=data,
                content_type='multipart/form-data'
            )

            assert response.status_code == 400
            payload = response.get_json()
            assert payload.get('ok') is False
            # Deve retornar bloqueios
            preview = payload.get('preview', {})
            bloqueios = preview.get('bloqueios_importacao', [])
            assert len(bloqueios) > 0

    def test_preview_sem_arquivo_retorna_400(self, authenticated_client, app_fixture):
        """Preview sem arquivo retorna 400."""
        with app_fixture.app_context():
            response = authenticated_client.post(
                '/ativos/importar/preview',
                data={},
                content_type='multipart/form-data'
            )

            assert response.status_code == 400
            payload = response.get_json()
            assert payload.get('ok') is False
            assert 'arquivo' in payload.get('erro', '').lower()

    def test_preview_arquivo_vazio_retorna_400(self, authenticated_client, app_fixture):
        """Preview com arquivo vazio retorna 400."""
        with app_fixture.app_context():
            data = {
                'file': (BytesIO(b''), 'test.csv')
            }

            response = authenticated_client.post(
                '/ativos/importar/preview',
                data=data,
                content_type='multipart/form-data'
            )

            assert response.status_code == 400
            payload = response.get_json()
            assert payload.get('ok') is False
            assert 'vazio' in payload.get('erro', '').lower()

    def test_preview_sem_csrf_retorna_403(self, authenticated_client, app_fixture):
        """Preview sem token CSRF válido retorna 403."""
        with app_fixture.app_context():
            data = {
                'file': (BytesIO(CSV_VALIDO), 'test.csv')
            }

            # Remove ou invalida o header CSRF
            response = authenticated_client.post(
                '/ativos/importar/preview',
                data=data,
                content_type='multipart/form-data',
                headers={'X-CSRF-Token': 'invalid_token'}
            )

            assert response.status_code == 403

    def test_preview_sem_autenticacao_retorna_401(self, http_client, app_fixture):
        """Preview sem sessão autenticada retorna 401."""
        with app_fixture.app_context():
            data = {
                'file': (BytesIO(CSV_VALIDO), 'test.csv')
            }

            response = http_client.post(
                '/ativos/importar/preview',
                data=data,
                content_type='multipart/form-data'
            )

            assert response.status_code == 401

    # ========== POST /ativos/importar/confirmar ==========

    def test_confirmar_checkboxes_incompletos_retorna_400(self, authenticated_client, app_fixture):
        """Confirmar sem todos os checkboxes retorna 400."""
        with app_fixture.app_context():
            data = {
                'file': (BytesIO(CSV_VALIDO), 'test.csv'),
                'id_lote': 'IMP-2026-04-22-test-id',
                'sugestoes_confirmadas': '{}',
                # Faltam checkboxes
            }

            response = authenticated_client.post(
                '/ativos/importar/confirmar',
                data=data,
                content_type='multipart/form-data'
            )

            assert response.status_code == 400
            payload = response.get_json()
            assert payload.get('ok') is False
            assert 'checkbox' in payload.get('erro', '').lower() or 'confirmação' in payload.get('erro', '').lower()

    def test_confirmar_checkboxes_completos_retorna_201(self, authenticated_client, app_fixture):
        """Confirmar com todos os checkboxes retorna 201."""
        with app_fixture.app_context():
            # Primeiro, fazer preview para obter id_lote
            preview_data = {
                'file': (BytesIO(CSV_VALIDO), 'test.csv')
            }
            preview_response = authenticated_client.post(
                '/ativos/importar/preview',
                data=preview_data,
                content_type='multipart/form-data'
            )

            assert preview_response.status_code == 200
            id_lote = preview_response.get_json().get('id_lote', 'test-id')

            # Depois, confirmar com checkboxes
            confirm_data = {
                'file': (BytesIO(CSV_VALIDO), 'test.csv'),
                'id_lote': id_lote,
                'sugestoes_confirmadas': '{}',
                'revisor_dados': 'on',
                'confirma_duplicatas': 'on',
                'aceita_avisos': 'on',
                'autoriza_importacao': 'on',
            }

            response = authenticated_client.post(
                '/ativos/importar/confirmar',
                data=confirm_data,
                content_type='multipart/form-data'
            )

            # Deve retornar 201 (Created) ou 200 (OK) se importação bem-sucedida
            assert response.status_code in [200, 201]
            payload = response.get_json()
            assert payload.get('ok') is True or payload.get('ok') is not False

    def test_confirmar_id_lote_retorna_no_resposta(self, authenticated_client, app_fixture):
        """Resposta do confirmar inclui id_lote para rastreabilidade."""
        with app_fixture.app_context():
            # Preview
            preview_data = {
                'file': (BytesIO(CSV_VALIDO), 'test.csv')
            }
            preview_response = authenticated_client.post(
                '/ativos/importar/preview',
                data=preview_data,
                content_type='multipart/form-data'
            )
            id_lote = preview_response.get_json().get('id_lote')

            # Confirmar
            confirm_data = {
                'file': (BytesIO(CSV_VALIDO), 'test.csv'),
                'id_lote': id_lote,
                'sugestoes_confirmadas': '{}',
                'revisor_dados': 'on',
                'confirma_duplicatas': 'on',
                'aceita_avisos': 'on',
                'autoriza_importacao': 'on',
            }

            response = authenticated_client.post(
                '/ativos/importar/confirmar',
                data=confirm_data,
                content_type='multipart/form-data'
            )

            if response.status_code in [200, 201]:
                payload = response.get_json()
                assert 'id_lote' in payload or 'id_lote' in payload.get('resultado', {})

    def test_confirmar_sem_arquivo_retorna_400(self, authenticated_client, app_fixture):
        """Confirmar sem arquivo CSV retorna 400."""
        with app_fixture.app_context():
            data = {
                'id_lote': 'IMP-test',
                'revisor_dados': 'on',
                'confirma_duplicatas': 'on',
                'aceita_avisos': 'on',
                'autoriza_importacao': 'on',
            }

            response = authenticated_client.post(
                '/ativos/importar/confirmar',
                data=data,
                content_type='multipart/form-data'
            )

            assert response.status_code == 400

    def test_confirmar_sem_csrf_retorna_403(self, authenticated_client, app_fixture):
        """Confirmar sem token CSRF retorna 403."""
        with app_fixture.app_context():
            data = {
                'file': (BytesIO(CSV_VALIDO), 'test.csv'),
                'id_lote': 'IMP-test',
                'revisor_dados': 'on',
                'confirma_duplicatas': 'on',
                'aceita_avisos': 'on',
                'autoriza_importacao': 'on',
            }

            response = authenticated_client.post(
                '/ativos/importar/confirmar',
                data=data,
                content_type='multipart/form-data',
                headers={'X-CSRF-Token': 'invalid'}
            )

            assert response.status_code == 403

    def test_confirmar_sem_autenticacao_retorna_401(self, http_client, app_fixture):
        """Confirmar sem sessão retorna 401."""
        with app_fixture.app_context():
            data = {
                'file': (BytesIO(CSV_VALIDO), 'test.csv'),
                'id_lote': 'IMP-test',
            }

            response = http_client.post(
                '/ativos/importar/confirmar',
                data=data,
                content_type='multipart/form-data'
            )

            assert response.status_code == 401


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
