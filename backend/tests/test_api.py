import pytest
from fastapi.testclient import TestClient
# Certifique-se de que o import aponta para onde está o seu "app = FastAPI()"
# MUDOU AQUI: mude de "from app.main import app" para:
from main import app

client = TestClient(app)

# Dicionário global para guardar IDs criados durante o teste e usá-los nos endpoints seguintes
@pytest.fixture(scope="module")
def dados_fluxo():
    return {"drone_id": None, "voo_id": None}

# ==================== TESTES DO FLUXO DE ROTAS ====================
def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200

def test_fluxo_preparar_rota():
    response = client.post("/rotas/preparar", json={"route_id": "square"})
    assert response.status_code in (200, 201)
    assert response.json().get("estado") == "preparando"

# ==================== TESTES DOS NOVOS ENDPOINTS (PIER DRONE) ====================
def test_cadastrar_drone(dados_fluxo):
    payload = {"nome": "Drone Patrol 01", "modelo": "DJI Matrice", "status": "disponivel"}
    response = client.post("/drones/", json=payload)
    assert response.status_code in (200, 201)
    
    dados = response.json()
    assert "id" in dados
    dados_fluxo["drone_id"] = dados["id"]

def test_iniciar_voo_drone(dados_fluxo):
    drone_id = dados_fluxo.get("drone_id") or 1
    payload = {"drone_id": drone_id, "plano_voo": "Ronda Pier", "origem": "Base Alpha"}
    response = client.post("/voos/", json=payload)
    assert response.status_code in (200, 201)
    
    dados = response.json()
    dados_fluxo["voo_id"] = dados.get("id")

def test_enviar_telemetria_batch(dados_fluxo):
    voo_id = dados_fluxo.get("voo_id") or 1
    payload = [
        {"voo_id": voo_id, "latitude": -23.55, "longitude": -46.63, "altitude": 15.0, "velocidade": 5.0}
    ]
    response = client.post("/telemetria/batch", json=payload)
    assert response.status_code in (200, 201)

def test_criar_alerta_veiculo():
    payload = {"placa": "BRA2E19", "motivo": "Queixa de furto ativa no Pier", "nivel_criticidade": "alto"}
    response = client.post("/alertas/", json=payload)
    assert response.status_code in (200, 201)

def test_dashboard_resumo():
    response = client.get("/dashboard/resumo")
    assert response.status_code == 200