import pytest
from fastapi.testclient import TestClient
# Substitua 'main' pelo nome do arquivo principal do seu FastAPI se for diferente
from main import app 

client = TestClient(app)

@pytest.fixture(scope="module")
def dados_fluxo():
    # Compartilha os IDs gerados dinamicamente entre os testes do mesmo ciclo
    return {"drone_id": None, "voo_id": None}

def test_health_check():
    response = client.get("/health")  # ou o seu endpoint de health check
    assert response.status_code == 200

def test_fluxo_preparar_rota():
    # Mantido conforme o seu teste que já estava passando
    response = client.get("/dashboard/resumo") # exemplo de rota de preparação se houver
    assert response.status_code == 200

def test_cadastrar_drone(dados_fluxo):
    payload = {
        "numero_serie": "DRN-2026-XYZ",
        "nome": "Drone Patrol 01",
        "modelo": "DJI Tello"
    }
    response = client.post("/drones/", json=payload)
    assert response.status_code in (200, 201)
    
    # Guarda o ID retornado pela API para usar no próximo teste
    # Se a sua API retornar outra chave (ex: 'drone_id'), mude aqui
    dados_fluxo["drone_id"] = response.json().get("id") or 1

def test_iniciar_voo_drone(dados_fluxo):
    # Usa o ID do drone cadastrado ou assume 1 como fallback
    drone_id = dados_fluxo.get("drone_id") or 1
    payload = {
        "drone_id": drone_id
    }
    response = client.post("/voos/", json=payload)
    assert response.status_code in (200, 201)
    
    # Guarda o ID do voo retornado pela API para a telemetria
    # Se a sua API retornar outra chave (ex: 'voo_id'), mude aqui
    dados_fluxo["voo_id"] = response.json().get("id") or 1

def test_enviar_telemetria_batch(dados_fluxo):
    # Usa o ID do voo iniciado ou assume 1 como fallback
    voo_id = dados_fluxo.get("voo_id") or 1
    payload = {
        "id_voo": voo_id,
        "leituras": [
            {
                "latitude": -23.55,
                "longitude": -46.63,
                "altitude": 15.0,
                "velocidade": 5.0
            }
        ]
    }
    response = client.post("/telemetria/batch", json=payload)
    assert response.status_code in (200, 201)

def test_criar_alerta_veiculo():
    payload = {
        "consulta_id": 1,
        "operador_notificado": "Operador Central Centro-Oeste"
    }
    response = client.post("/alertas/", json=payload)
    assert response.status_code in (200, 201)

def test_dashboard_resumo():
    response = client.get("/dashboard/resumo")
    assert response.status_code == 200