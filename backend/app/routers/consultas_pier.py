import sys
import os
import pytest
from fastapi.testclient import TestClient

# 1. Ajusta o path para garantir que o Python localize os módulos corretamente
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

# 2. Solução para a Importação Circular: 
# Forçamos a inicialização completa dos submódulos do pacote antes de puxar o 'app'.
# Isso quebra o ciclo de dependência na memória do Python exclusivamente durante o teste.
import app.routers.__init__

from main import app 

client = TestClient(app)

@pytest.fixture(scope="module")
def dados_fluxo():
    """Compartilha os IDs criados dinamicamente ao longo do fluxo de testes."""
    return {
        "id_drone": None,
        "id_voo": None,
        "id_deteccao": None,
        "id_consulta": None
    }

def test_health_check():
    response = client.get("/drones/")
    assert response.status_code == 200

def test_dashboard_resumo():
    response = client.get("/dashboard/resumo")
    assert response.status_code == 200

def test_cadastrar_drone(dados_fluxo):
    payload = {
        "numero_serie": "DRN-2026-TESTE-LIVIA",
        "nome": "Drone de Patrulha Pier",
        "modelo": "DJI Tello"
    }
    response = client.post("/drones/", json=payload)
    assert response.status_code in (200, 201)
    
    dados = response.json()
    dados_fluxo["id_drone"] = dados.get("id") or dados.get("id_drone")

def test_iniciar_voo_drone(dados_fluxo):
    id_drone = dados_fluxo.get("id_drone") or 1
    payload = {
        "id_drone": id_drone,
        "area_monitorada": "Pier Setor Sul"
    }
    response = client.post("/voos/", json=payload)
    assert response.status_code in (200, 201)
    
    dados = response.json()
    dados_fluxo["id_voo"] = dados.get("id") or dados.get("id_voo")

def test_enviar_telemetria_batch(dados_fluxo):
    id_voo = dados_fluxo.get("id_voo") or 1
    payload = {
        "id_voo": id_voo,
        "leituras": [
            {
                "latitude": -23.5500000,
                "longitude": -46.6300000,
                "altura": 15,
                "velocidade_x": 5.0,
                "velocidade_y": 0.0,
                "velocidade_z": 0.0,
                "bateria": 85
            }
        ]
    }
    response = client.post("/telemetria/batch", json=payload)
    assert response.status_code in (200, 201)

def test_criar_deteccao_e_consulta_pier(dados_fluxo):
    id_voo = dados_fluxo.get("id_voo") or 1
    
    payload_deteccao = {
        "id_voo": id_voo,
        "dados": {
            "placa_lida": "ABC1D23",
            "confianca_ocr": 0.98,
            "marca_veiculo": "Toyota",
            "modelo_veiculo": "Corolla"
        }
    }
    resp_det = client.post("/deteccoes/", json=payload_deteccao)
    assert resp_det.status_code in (200, 201)
    
    id_det = resp_det.json().get("id") if isinstance(resp_det.json(), dict) else None

    payload_pier = {
        "ABC1D23": {
            "status": "found",
            "vehicle_lookup_id": "pier-lkp-123",
            "vehicle": {
                "make": "Toyota",
                "model": "Corolla",
                "fabrication_year": 2024
            }
        }
    }
    
    url_consulta = "/consultas_pier/batch"
    if id_det:
        url_consulta += f"?id_deteccao={id_det}"
        
    resp_cons = client.post(url_consulta, json=payload_pier)
    assert resp_cons.status_code in (200, 201)
    
    lista_consultas = resp_cons.json()
    if lista_consultas and isinstance(lista_consultas, list):
        dados_fluxo["id_consulta"] = lista_consultas[0].get("id")

def test_criar_alerta_veiculo(dados_fluxo):
    id_consulta = dados_fluxo.get("id_consulta") or 1
    
    payload = {
        "consulta_id": id_consulta,
        "operador_notificado": "Operador Central Centro-Oeste"
    }
    response = client.post("/alertas/", json=payload)
    assert response.status_code in (200, 201)