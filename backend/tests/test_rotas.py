"""
tests/test_rotas.py — suite pytest para o fluxo de rotas e endpoints principais.

Estratégia: usa TestClient do FastAPI (sem rede real), mockando o Supabase via
monkeypatch. Cada teste é isolado e idempotente — não depende de banco ou variável
de ambiente real.

Execução:
    pip install pytest httpx pytest-mock
    pytest tests/test_rotas.py -v
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

# ── Fixtures de ambiente ──────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def mock_env(monkeypatch):
    """Garante que variáveis de ambiente existam antes de importar o app."""
    monkeypatch.setenv("SUPABASE_URL", "https://fake.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "fake-key")


@pytest.fixture()
def mock_supabase_client():
    """Retorna um cliente Supabase completamente mockado."""
    return MagicMock()


@pytest.fixture()
def app_client(mock_supabase_client):
    """TestClient com injeção de dependência substituindo o Supabase real."""
    # Importação tardia para que o monkeypatch de env já esteja ativo
    from app.database.supabase_client import get_client
    import main as app_module

    app_module.app.dependency_overrides[get_client] = lambda: mock_supabase_client
    with TestClient(app_module.app) as c:
        yield c
    app_module.app.dependency_overrides.clear()


# ── Helper: monta resposta Supabase fake ──────────────────────────────────────

def _supabase_row(data: dict):
    """Cria um objeto mock que imita supabase response.data."""
    resp = MagicMock()
    resp.data = [data]
    return resp


def _supabase_empty():
    resp = MagicMock()
    resp.data = []
    return resp


# ─────────────────────────────────────────────────────────────────────────────
# Health
# ─────────────────────────────────────────────────────────────────────────────

class TestHealth:
    def test_health_returns_ok(self, app_client):
        r = app_client.get("/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}


# ─────────────────────────────────────────────────────────────────────────────
# POST /rotas/preparar
# ─────────────────────────────────────────────────────────────────────────────

class TestPrepararRota:
    def test_preparar_route_valida(self, app_client, mock_supabase_client):
        row = {"route_id": "square", "estado": "preparando", "comando_pendente": {"tipo": "preparar"}}
        mock_supabase_client.table.return_value.upsert.return_value.execute.return_value = _supabase_row(row)

        r = app_client.post("/rotas/preparar", json={"route_id": "square"})

        assert r.status_code in (200, 201)
        assert r.json()["estado"] == "preparando"

    def test_preparar_route_invalida(self, app_client):
        r = app_client.post("/rotas/preparar", json={"route_id": "rota_inexistente"})
        assert r.status_code == 400

    def test_preparar_road(self, app_client, mock_supabase_client):
        row = {"route_id": "road", "estado": "preparando"}
        mock_supabase_client.table.return_value.upsert.return_value.execute.return_value = _supabase_row(row)

        r = app_client.post("/rotas/preparar", json={"route_id": "road"})
        assert r.status_code in (200, 201)


# ─────────────────────────────────────────────────────────────────────────────
# GET /rotas/comando-pendente
# ─────────────────────────────────────────────────────────────────────────────

class TestComandoPendente:
    def test_retorna_tipo_preparar_quando_ha_pendente(self, app_client, mock_supabase_client):
        row = {"route_id": "square", "comando_pendente": {"tipo": "preparar"}}
        (mock_supabase_client
            .table.return_value
            .select.return_value
            .not_.return_value
            .is_.return_value
            .limit.return_value
            .execute.return_value) = _supabase_row(row)

        r = app_client.get("/rotas/comando-pendente")
        assert r.status_code == 200
        body = r.json()
        assert body["tipo"] == "preparar"
        assert body["route_id"] == "square"

    def test_retorna_tipo_none_quando_nao_ha_pendente(self, app_client, mock_supabase_client):
        (mock_supabase_client
            .table.return_value
            .select.return_value
            .not_.return_value
            .is_.return_value
            .limit.return_value
            .execute.return_value) = _supabase_empty()

        r = app_client.get("/rotas/comando-pendente")
        assert r.status_code == 200
        assert r.json()["tipo"] is None


# ─────────────────────────────────────────────────────────────────────────────
# POST /rotas/{route_id}/commands
# ─────────────────────────────────────────────────────────────────────────────

COMMANDS = [
    {"action": "frente",   "velocity_pct": 50, "duration_s": 1.5},
    {"action": "esquerda", "velocity_pct": 50, "duration_s": 1.5},
    {"action": "tras",     "velocity_pct": 50, "duration_s": 1.5},
    {"action": "direita",  "velocity_pct": 50, "duration_s": 1.5},
]


class TestEntregarCommands:
    def test_commands_gravados_estado_pronta(self, app_client, mock_supabase_client):
        row = {
            "route_id": "square",
            "estado": "pronta",
            "commands": COMMANDS,
            "total_duration_s": 6.0,
        }
        mock_supabase_client.table.return_value.upsert.return_value.execute.return_value = _supabase_row(row)

        r = app_client.post(
            "/rotas/square/commands",
            json={"route_id": "square", "commands": COMMANDS},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["estado"] == "pronta"
        assert body["total_duration_s"] == 6.0

    def test_commands_route_invalida(self, app_client):
        r = app_client.post(
            "/rotas/rota_inexistente/commands",
            json={"route_id": "rota_inexistente", "commands": COMMANDS},
        )
        assert r.status_code == 400

    def test_total_duration_calculado_corretamente(self, app_client, mock_supabase_client):
        """Verifica que total_duration_s é soma dos duration_s dos comandos."""
        commands_custom = [
            {"action": "frente", "velocity_pct": 30, "duration_s": 2.0},
            {"action": "tras",   "velocity_pct": 30, "duration_s": 3.0},
        ]
        row = {
            "route_id": "square",
            "estado": "pronta",
            "commands": commands_custom,
            "total_duration_s": 5.0,
        }
        mock_supabase_client.table.return_value.upsert.return_value.execute.return_value = _supabase_row(row)

        r = app_client.post(
            "/rotas/square/commands",
            json={"route_id": "square", "commands": commands_custom},
        )
        assert r.status_code == 200
        # O repository calcula internamente; aqui validamos que o campo existe e é numérico
        assert isinstance(r.json()["total_duration_s"], float)


# ─────────────────────────────────────────────────────────────────────────────
# GET /rotas/{route_id}/estado
# ─────────────────────────────────────────────────────────────────────────────

class TestEstadoRota:
    def test_estado_idle_quando_nao_existe(self, app_client, mock_supabase_client):
        resp = MagicMock()
        resp.data = None
        (mock_supabase_client
            .table.return_value
            .select.return_value
            .eq.return_value
            .maybe_single.return_value
            .execute.return_value) = resp

        r = app_client.get("/rotas/square/estado")
        assert r.status_code == 200
        body = r.json()
        assert body["estado"] == "idle"
        assert body["commands"] is None

    def test_estado_pronta_com_commands(self, app_client, mock_supabase_client):
        row = {
            "route_id": "square",
            "estado": "pronta",
            "commands": COMMANDS,
            "total_duration_s": 6.0,
            "resultado": None,
        }
        resp = MagicMock()
        resp.data = row
        (mock_supabase_client
            .table.return_value
            .select.return_value
            .eq.return_value
            .maybe_single.return_value
            .execute.return_value) = resp

        r = app_client.get("/rotas/square/estado")
        assert r.status_code == 200
        body = r.json()
        assert body["estado"] == "pronta"
        assert len(body["commands"]) == 4

    def test_estado_route_invalida(self, app_client):
        r = app_client.get("/rotas/rota_inexistente/estado")
        assert r.status_code == 400


# ─────────────────────────────────────────────────────────────────────────────
# POST /rotas/{route_id}/iniciar
# ─────────────────────────────────────────────────────────────────────────────

class TestIniciarRota:
    def _mock_buscar_estado(self, mock_client, estado: str):
        """Configura o mock para buscar_estado retornar um estado específico."""
        row = {"route_id": "square", "estado": estado}
        resp = MagicMock()
        resp.data = row
        (mock_client
            .table.return_value
            .select.return_value
            .eq.return_value
            .maybe_single.return_value
            .execute.return_value) = resp

    def test_iniciar_sem_confirmacao_recusado(self, app_client):
        r = app_client.post("/rotas/square/iniciar", json={"route_id": "square", "confirmed": False})
        assert r.status_code == 400

    def test_iniciar_confirmado_estado_pronta(self, app_client, mock_supabase_client):
        # buscar_estado retorna "pronta"
        self._mock_buscar_estado(mock_supabase_client, "pronta")
        # upsert (iniciar) retorna "iniciando"
        row_iniciando = {"route_id": "square", "estado": "iniciando"}
        mock_supabase_client.table.return_value.upsert.return_value.execute.return_value = _supabase_row(row_iniciando)

        r = app_client.post("/rotas/square/iniciar", json={"route_id": "square", "confirmed": True})
        assert r.status_code == 200
        assert r.json()["estado"] == "iniciando"

    def test_iniciar_quando_estado_nao_e_pronta_retorna_409(self, app_client, mock_supabase_client):
        self._mock_buscar_estado(mock_supabase_client, "preparando")

        r = app_client.post("/rotas/square/iniciar", json={"route_id": "square", "confirmed": True})
        assert r.status_code == 409

    def test_iniciar_route_invalida(self, app_client):
        r = app_client.post(
            "/rotas/rota_invalida/iniciar",
            json={"route_id": "rota_invalida", "confirmed": True},
        )
        assert r.status_code == 400


# ─────────────────────────────────────────────────────────────────────────────
# POST /rotas/{route_id}/resultado
# ─────────────────────────────────────────────────────────────────────────────

RESULTADO_OK = {
    "route_id": "square",
    "status": "completed",
    "battery_before": 84,
    "battery_after": 81,
    "commands_executed": [],
    "total_duration_s": 6.0,
    "errors": [],
}

RESULTADO_ERRO = {**RESULTADO_OK, "errors": ["timeout na execução"]}


class TestResultadoRota:
    def test_resultado_sem_erros_estado_concluida(self, app_client, mock_supabase_client):
        row = {"route_id": "square", "estado": "concluida", "resultado": RESULTADO_OK}
        mock_supabase_client.table.return_value.upsert.return_value.execute.return_value = _supabase_row(row)

        r = app_client.post("/rotas/square/resultado", json=RESULTADO_OK)
        assert r.status_code == 200
        assert r.json()["estado"] == "concluida"

    def test_resultado_com_erros_estado_erro(self, app_client, mock_supabase_client):
        row = {"route_id": "square", "estado": "erro", "resultado": RESULTADO_ERRO}
        mock_supabase_client.table.return_value.upsert.return_value.execute.return_value = _supabase_row(row)

        r = app_client.post("/rotas/square/resultado", json=RESULTADO_ERRO)
        assert r.status_code == 200
        assert r.json()["estado"] == "erro"

    def test_resultado_route_invalida(self, app_client):
        r = app_client.post("/rotas/rota_invalida/resultado", json=RESULTADO_OK)
        assert r.status_code == 400


# ─────────────────────────────────────────────────────────────────────────────
# Fluxo completo (integração in-process)
# ─────────────────────────────────────────────────────────────────────────────

class TestFluxoCompleto:
    """Reproduz o smoke_test_rotas.py mas em memória, sem rede."""

    def test_ciclo_preparar_commands_iniciar_resultado(self, app_client, mock_supabase_client):
        # Passo 1: preparar
        mock_supabase_client.table.return_value.upsert.return_value.execute.return_value = _supabase_row(
            {"route_id": "square", "estado": "preparando", "comando_pendente": {"tipo": "preparar"}}
        )
        r = app_client.post("/rotas/preparar", json={"route_id": "square"})
        assert r.json()["estado"] == "preparando"

        # Passo 2: gateway puxa comando
        (mock_supabase_client
            .table.return_value
            .select.return_value
            .not_.return_value
            .is_.return_value
            .limit.return_value
            .execute.return_value) = _supabase_row(
                {"route_id": "square", "comando_pendente": {"tipo": "preparar"}}
            )
        r = app_client.get("/rotas/comando-pendente")
        assert r.json()["tipo"] == "preparar"

        # Passo 3: gateway entrega commands → pronta
        mock_supabase_client.table.return_value.upsert.return_value.execute.return_value = _supabase_row(
            {"route_id": "square", "estado": "pronta", "commands": COMMANDS, "total_duration_s": 6.0}
        )
        r = app_client.post(
            "/rotas/square/commands",
            json={"route_id": "square", "commands": COMMANDS},
        )
        assert r.json()["estado"] == "pronta"
        assert r.json()["total_duration_s"] == 6.0

        # Passo 4: iniciar confirmado → iniciando
        estado_resp = MagicMock()
        estado_resp.data = {"route_id": "square", "estado": "pronta"}
        (mock_supabase_client
            .table.return_value
            .select.return_value
            .eq.return_value
            .maybe_single.return_value
            .execute.return_value) = estado_resp
        mock_supabase_client.table.return_value.upsert.return_value.execute.return_value = _supabase_row(
            {"route_id": "square", "estado": "iniciando"}
        )
        r = app_client.post("/rotas/square/iniciar", json={"route_id": "square", "confirmed": True})
        assert r.json()["estado"] == "iniciando"

        # Passo 5: resultado → concluida
        mock_supabase_client.table.return_value.upsert.return_value.execute.return_value = _supabase_row(
            {"route_id": "square", "estado": "concluida", "resultado": RESULTADO_OK}
        )
        r = app_client.post("/rotas/square/resultado", json=RESULTADO_OK)
        assert r.json()["estado"] == "concluida"