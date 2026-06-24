def test_rotas_flow(client):
    route_id = "square"

    response = client.post("/rotas/preparar", json={"route_id": route_id})
    assert response.status_code == 201
    assert response.json()["estado"] == "preparando"

    response = client.get("/rotas/comando-pendente")
    assert response.status_code == 200
    assert response.json()["tipo"] == "preparar"
    assert response.json()["route_id"] == route_id

    commands = [
        {"action": "frente", "velocity_pct": 50, "duration_s": 1.5},
        {"action": "esquerda", "velocity_pct": 50, "duration_s": 1.5},
    ]
    response = client.post(f"/rotas/{route_id}/commands", json={"route_id": route_id, "commands": commands})
    assert response.status_code == 200
    assert response.json()["estado"] == "pronta"
    assert response.json()["total_duration_s"] == 3.0

    response = client.get(f"/rotas/{route_id}/estado")
    assert response.status_code == 200
    assert response.json()["estado"] == "pronta"
    assert isinstance(response.json()["commands"], list)

    response = client.post(f"/rotas/{route_id}/iniciar", json={"route_id": route_id, "confirmed": False})
    assert response.status_code == 400

    response = client.post(f"/rotas/{route_id}/iniciar", json={"route_id": route_id, "confirmed": True})
    assert response.status_code == 200
    assert response.json()["estado"] == "iniciando"

    response = client.get("/rotas/comando-pendente")
    assert response.status_code == 200
    assert response.json()["tipo"] == "iniciar"

    resultado = {
        "route_id": route_id,
        "status": "completed",
        "battery_before": 84,
        "battery_after": 81,
        "commands_executed": [
            {"action": "frente", "velocity_pct": 50, "duration_s": 1.5, "rc_vector": {"lr": 0, "fb": 50, "ud": 0}}
        ],
        "total_duration_s": 1.5,
        "errors": [],
    }
    response = client.post(f"/rotas/{route_id}/resultado", json=resultado)
    assert response.status_code == 200
    assert response.json()["estado"] == "concluida"

    response = client.get(f"/rotas/{route_id}/estado")
    assert response.status_code == 200
    assert response.json()["estado"] == "concluida"
