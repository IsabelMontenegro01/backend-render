from supabase import Client


class TelemetriaRepository:
    """Operações de banco de dados para a tabela `telemetria`."""

    TABLE = "telemetria"

    def __init__(self, client: Client):
        self.client = client

    def inserir(self, voo_id: int, dados: dict) -> dict:
        """
        Insere uma leitura de telemetria vinculada a um voo.

        `dados` deve conter os campos do SDK Tello + campos vGPS:
          pitch, roll, yaw, velocidade_x/y/z, altura, altura_tof,
          barometro, bateria, temperatura_min/max,
          aceleracao_x/y/z, latitude, longitude,
          precisao_gps_m, fonte_localizacao
        """
        payload = {"id_voo": voo_id, **dados}
        response = self.client.table(self.TABLE).insert(payload).execute()
        return response.data[0]

    def inserir_batch(self, voo_id: int, leituras: list[dict]) -> list[dict]:
        """
        Insere múltiplas leituras de uma vez (otimizado para ~10 Hz do Tello).
        Cada item de `leituras` segue o mesmo contrato do método `inserir`.
        """
        # Kept: origin/develop validation to prevent empty payload errors
        if not leituras:
            return []
            
        payload = [{"id_voo": voo_id, **leitura} for leitura in leituras]
        response = self.client.table(self.TABLE).insert(payload).execute()
        return response.data

    def listar_por_voo(self, voo_id: int, limite: int = 500) -> list[dict]:
        """Retorna as últimas `limite` leituras de telemetria de um voo."""
        response = (
            self.client.table(self.TABLE)
            .select("*")
            .eq("id_voo", voo_id)
            .order("timestamp", desc=True)
            .limit(limite)
            .execute()
        )
        return response.data

    def ultima_leitura(self, voo_id: int) -> dict | None:
        """Retorna a leitura de telemetria mais recente de um voo."""
        response = (
            self.client.table(self.TABLE)
            .select("*")
            .eq("id_voo", voo_id)
            .order("timestamp", desc=True)
            .limit(1)
            .maybe_single()  # Kept: Correct Python snake_case method
            .execute()
        )
        return response.data