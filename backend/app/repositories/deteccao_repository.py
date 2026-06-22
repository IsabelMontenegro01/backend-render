from supabase import Client


class DeteccaoRepository:
    TABLE = "deteccao"

    def __init__(self, client: Client):
        self.client = client

    def registrar(self, voo_id: int, telemetria_id: int | None, dados: dict) -> dict:
        payload = {"id_voo": voo_id, "id_telemetria": telemetria_id, **dados}
        response = self.client.table(self.TABLE).insert(payload).execute()
        return response.data[0]

    def atualizar_vlm(self, deteccao_id: int, dados: dict) -> dict | None:
        """Grava resultado do Moondream2 (marca, modelo, ano, dano)."""
        mapa = {
            "cor":            dados.get("cor"),
            "marca_veiculo":  dados.get("marca"),
            "modelo_veiculo": dados.get("modelo"),
            "ano_veiculo":    dados.get("ano_aproximado"),
        }
        payload = {k: v for k, v in mapa.items() if v is not None}
        if not payload:
            return self.buscar_por_id(deteccao_id)
        response = (
            self.client.table(self.TABLE)
            .update(payload)
            .eq("id", deteccao_id)
            .execute()
        )
        return response.data[0] if response.data else None

    def buscar_por_id(self, deteccao_id: int) -> dict | None:
        response = (
            self.client.table(self.TABLE)
            .select("*")
            .eq("id", deteccao_id)
            .maybe_single()
            .execute()
        )
        return response.data

    def listar_por_voo(self, voo_id: int) -> list[dict]:
        response = (
            self.client.table(self.TABLE)
            .select("*")
            .eq("id_voo", voo_id)
            .order("timestamp", desc=True)
            .execute()
        )
        return response.data

    def buscar_por_placa(self, placa: str) -> list[dict]:
        response = (
            self.client.table(self.TABLE)
            .select("*")
            .eq("placa_lida", placa.upper())
            .execute()
        )
        return response.data

    def listar_historico_placas(self, limite: int = 200) -> list[dict]:
        response = (
            self.client.table(self.TABLE)
            .select("*, consulta_pier(*)")
            .order("timestamp", desc=True)
            .limit(limite)
            .execute()
        )
        return response.data
