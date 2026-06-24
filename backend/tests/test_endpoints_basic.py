def test_full_basic_flow(client):
    # Health
    response = client.get("/health")
    assert response.status_code == 200

    # Criar drone
    response = client.post("/drones/", json={"numero_serie": "SN-100", "nome": "Drone Test", "modelo": "TestModel"})
    assert response.status_code == 201
    drone_id = response.json()["id"]

    # Iniciar voo
    response = client.post("/voos/", json={"id_drone": drone_id, "area_monitorada": "teste"})
    assert response.status_code == 201
    voo_id = response.json()["id"]

    # Telemetria batch
    leituras = [
        {"latitude": -23.55, "longitude": -46.63, "altitude": 10.0, "velocidade": 3.3},
        {"latitude": -23.551, "longitude": -46.631, "altitude": 11.0, "velocidade": 3.8},
    ]
    response = client.post("/telemetria/batch", json={"id_voo": voo_id, "leituras": leituras})
    assert response.status_code == 201

    # Registrar detecção
    response = client.post("/deteccoes/", json={"id_voo": voo_id, "dados": {"tipo_veiculo": "carro", "placa": "TEST1234", "confianca": 0.9}})
    assert response.status_code == 201

    # Dashboard
    response = client.get("/dashboard/resumo")
    assert response.status_code == 200
    assert isinstance(response.json(), dict)
