import os

from app.database.supabase_client import get_client
from app.repositories.deteccao_repository import DeteccaoRepository
from app.repositories.consulta_pier_repository import ConsultaPierRepository
from app.repositories.alerta_repository import AlertaRepository
from app.services.pier_client import pier_client

USE_MOCK_PIER = os.getenv("USE_MOCK_PIER", "false").lower() == "true"


class ProcessamentoDeteccaoService:

    @staticmethod
    async def processar(id_voo: int, id_telemetria: int | None, dados: dict) -> dict:
        client        = get_client()
        deteccao_repo = DeteccaoRepository(client)
        consulta_repo = ConsultaPierRepository(client)
        alerta_repo   = AlertaRepository(client)

        placa     = (dados.get("placa_lida") or "").upper()
        latitude  = dados.get("latitude")  or -23.5505
        longitude = dados.get("longitude") or -46.6333

        # 1. Salva detecção (sempre)
        deteccao = deteccao_repo.registrar(
            id_voo, id_telemetria,
            {
                "id_veiculo":    dados.get("id_veiculo"),
                "placa_lida":    placa,
                "confianca_ocr": dados.get("confianca_ocr"),
            },
        )
        deteccao_id = deteccao["id"]

        # 2. Consulta Pier (token auto-gerenciado) ou mock controlado por flag
        if USE_MOCK_PIER:
            from app.mock_pier import veiculos_mock
            pier_data = veiculos_mock.get(placa, {"status": "not_found"})
        else:
            try:
                pier_data = pier_client.consultar_placa(placa, latitude, longitude)
            except Exception as e:
                print(f"[PIER][ERRO] consultar_placa placa={placa}: {type(e).__name__}: {e}")
                pier_data = {"status": "not_found", "error": str(e)}

        if pier_data.get("status") != "found":
            print(f"[PIER][DEBUG] placa={placa} status!=found raw={pier_data}")

        achado    = pier_data.get("status") == "found"
        resultado = "achado" if achado else "nao_achado"

        # 3. Persiste consulta
        consulta = consulta_repo.registrar(
            deteccao_id=deteccao_id,
            placa_consultada=placa,
            resultado=resultado,
            resposta_raw=pier_data,
        )

        if not achado:
            return {"status": "pier_not_found", "deteccao_id": deteccao_id, "precisa_vlm": False}

        # 4. Confirma lookup + cria alerta
        vehicle_lookup_id = pier_data.get("vehicle_lookup_id")
        if not USE_MOCK_PIER:
            try:
                pier_client.confirmar_lookup(vehicle_lookup_id, True)
            except Exception:
                pass
        alerta_repo.criar(consulta_id=consulta["id"])

        return {
            "status": "pier_found",
            "deteccao_id": deteccao_id,
            "vehicle_lookup_id": vehicle_lookup_id,
            "precisa_vlm": True,
        }
