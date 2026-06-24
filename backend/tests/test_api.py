import pytest


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_drones_crud_flow(client):
    create_payload = {"numero_serie": "SN-001", "nome": "Drone Test", "modelo": "DJI Matrice 300"}
    response = client.post("/drones/", json=create_payload)
    assert response.status_code == 201
    assert response.json()["numero_serie"] == "SN-001"

    response = client.get("/drones/")
    assert response.status_code == 200
    assert response.json()[0]["numero_serie"] == "SN-001"

    response = client.get("/drones/1")
    assert response.status_code == 200
    assert response.json()["id"] == 1

    response = client.patch("/drones/1/status", json={"status": "manutencao"})
    assert response.status_code == 200
    assert response.json()["status"] == "manutencao"


def test_voos_flow(client):
    client.post("/drones/", json={"numero_serie": "SN-002", "nome": "Drone Voo", "modelo": "DJI Matrice 300"})
    response = client.post("/voos/", json={"id_drone": 2, "area_monitorada": "linha verde"})
    assert response.status_code == 201
    assert response.json()["id_drone"] == 2

    response = client.get("/voos/1")
    assert response.status_code == 200
    assert response.json()["id"] == 1

    response = client.get("/voos/drone/2")
    assert response.status_code == 200
    assert response.json()[0]["id_drone"] == 2

    response = client.get("/voos/drone/2/em-andamento")
    assert response.status_code == 200
    assert response.json()["id_drone"] == 2

    response = client.post("/voos/1/finalizar", json={"tempo_total_motores": 120})
    assert response.status_code == 200
    assert response.json()["status_voo"] == "concluido"


def test_telemetria_batch_and_last(client):
    client.post("/drones/", json={"numero_serie": "SN-003", "nome": "Drone Telemetria", "modelo": "DJI Matrice 300"})
    client.post("/voos/", json={"id_drone": 3, "area_monitorada": "zona"})

    leituras = [
        {"latitude": -23.5505, "longitude": -46.6333, "altitude": 12.5, "velocidade": 4.2},
        {"latitude": -23.5506, "longitude": -46.6334, "altitude": 14.0, "velocidade": 5.0},
    ]
    response = client.post("/telemetria/batch", json={"id_voo": 1, "leituras": leituras})
    assert response.status_code == 201
    assert isinstance(response.json(), list)
    assert response.json()[0]["id_voo"] == 1

    response = client.get("/telemetria/voo/1/ultima")
    assert response.status_code == 200
    assert response.json()["id_voo"] == 1


def test_deteccao_consulta_alerta_flow(client):
    client.post("/drones/", json={"numero_serie": "SN-004", "nome": "Drone Deteccao", "modelo": "DJI Matrice 300"})
    client.post("/voos/", json={"id_drone": 4, "area_monitorada": "linha"})
    client.post("/telemetria/", json={"id_voo": 1, "dados": {"latitude": -23.55, "longitude": -46.63}})

    det_response = client.post("/deteccoes/", json={"id_voo": 1, "dados": {"tipo_veiculo": "carro", "placa": "ABC1D23", "confianca": 0.94}})
    assert det_response.status_code == 201
    det_id = det_response.json()["id"]

    consulta_response = client.post(
        "/consultas-pier/",
        json={"deteccao_id": det_id, "placa_consultada": "ABC1D23", "resultado": "achado", "resposta_raw": {"status": "ok"}},
    )
    assert consulta_response.status_code == 201
    consulta_id = consulta_response.json()["id"]

    alerta_response = client.post("/alertas/", json={"consulta_id": consulta_id})
    assert alerta_response.status_code == 201
    assert alerta_response.json()["id_consulta"] == consulta_id


def test_rotas_flow(client):
    response = client.post("/rotas/preparar", json={"route_id": "square"})
    assert response.status_code == 201
    assert response.json()["estado"] == "preparando"

    response = client.get("/rotas/comando-pendente")
    assert response.status_code == 200
    assert response.json()["tipo"] == "preparar"

    commands = [
        {"action": "frente", "velocity_pct": 50, "duration_s": 1.5},
        {"action": "esquerda", "velocity_pct": 50, "duration_s": 1.5},
    ]
    response = client.post("/rotas/square/commands", json={"route_id": "square", "commands": commands})
    assert response.status_code == 200
    assert response.json()["estado"] == "pronta"

    response = client.post("/rotas/square/iniciar", json={"route_id": "square", "confirmed": True})
    assert response.status_code == 200
    assert response.json()["estado"] == "iniciando"

    response = client.get("/rotas/comando-pendente")
    assert response.status_code == 200
    assert response.json()["tipo"] == "iniciar"

    resultado = {
        "route_id": "square",
        "status": "completed",
        "battery_before": 84,
        "battery_after": 81,
        "commands_executed": [{"action": "frente", "velocity_pct": 50, "duration_s": 1.5, "rc_vector": {"lr": 0, "fb": 50, "ud": 0}}],
        "total_duration_s": 1.5,
        "errors": [],
    }
    response = client.post("/rotas/square/resultado", json=resultado)
    assert response.status_code == 200
    assert response.json()["estado"] == "concluida"
