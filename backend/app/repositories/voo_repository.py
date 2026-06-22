from datetime import datetime, timezone
from supabase import Client


class VooRepository:
    """Operações de banco de dados para a tabela `voo`."""

    TABLE = "voo"

    def __init__(self, client: Client):
        self.client = client

    def iniciar(self, drone_id: int, area_monitorada: str | None = None) -> dict:
        """Cria um novo voo com status 'em_andamento' e retorna o registro."""
        response = (
            self.client.table(self.TABLE)
            .insert(
                {
                    "id_drone": drone_id,
                    "area_monitorada": area_monitorada,
                    "status_voo": "em_andamento",
                }
            )
            .execute()
        )
        return response.data[0]

    def finalizar(self, voo_id: int, tempo_total_motores: int | None = None) -> dict:
        """Encerra um voo, registra timestamp_fim e tempo total de motores."""
        response = (
            self.client.table(self.TABLE)
            .update(
                {
                    "timestamp_fim": datetime.now(timezone.utc).isoformat(),  # Kept: timezone-aware UTC
                    "status_voo": "concluido",
                    "tempo_total_motores": tempo_total_motores,
                }
            )
            .eq("id", voo_id)
            .execute()
        )
        # Kept: origin/develop error validation
        if not response.data:
            raise ValueError(f"Voo id={voo_id} não encontrado")
        return response.data[0]

    def buscar_por_id(self, voo_id: int) -> dict | None:
        """Retorna um voo pelo seu ID."""
        response = (
            self.client.table(self.TABLE)
            .select("*")
            .eq("id", voo_id)
            .maybe_single()  # Kept: safer than .single()
            .execute()
        )
        return response.data

    def listar_por_drone(self, drone_id: int) -> list[dict]:
        """Retorna todos os voos de um drone, ordenados do mais recente."""
        response = (
            self.client.table(self.TABLE)
            .select("*")
            .eq("id_drone", drone_id)
            .order("timestamp_inicio", desc=True)
            .execute()
        )
        return response.data

    def buscar_em_andamento(self, drone_id: int) -> dict | None:
        """Retorna o voo ativo de um drone, se houver."""
        response = (
            self.client.table(self.TABLE)
            .select("*")
            .eq("id_drone", drone_id)
            .eq("status_voo", "em_andamento")
            .maybe_single()  # Kept: Correct Python snake_case method
            .execute()
        )
        return response.data if response else None