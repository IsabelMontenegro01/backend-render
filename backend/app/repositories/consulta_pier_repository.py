from supabase import Client


class ConsultaPierRepository:
    """Operações de banco de dados para a tabela `consulta_pier`."""

    TABLE = "consulta_pier"

    def __init__(self, client: Client):
        self.client = client

    def registrar(
        self,
        deteccao_id: int | None,  # Mantido: origin/develop (permite consultas manuais sem uma detecção direta do drone)
        placa_consultada: str,
        resultado: str,
        resposta_raw: dict,
    ) -> dict:
        """
        Persiste o resultado de uma consulta à API Pier.

        Args:
            deteccao_id: FK para a detecção que originou a consulta.
            placa_consultada: Placa enviada à Pier.
            resultado: 'achado' ou 'nao_achado'.
            resposta_raw: JSON completo devolvido pela Pier API.
        """
        response = (
            self.client.table(self.TABLE)
            .insert(
                {
                    "id_deteccao": deteccao_id,
                    "placa_consultada": placa_consultada.upper(),
                    "resultado": resultado,
                    "resposta_raw": resposta_raw,
                }
            )
            .execute()
        )
        return response.data[0]

    def buscar_por_id(self, consulta_id: int) -> dict | None:
        """Retorna uma consulta Pier pelo ID."""
        response = (
            self.client.table(self.TABLE)
            .select("*")
            .eq("id", consulta_id)
            .maybe_single()  # Mantido: origin/develop (evita travar se o ID não existir)
            .execute()
        )
        return response.data

    def listar_por_deteccao(self, deteccao_id: int) -> list[dict]:
        """Retorna todas as consultas vinculadas a uma detecção."""
        response = (
            self.client.table(self.TABLE)
            .select("*")
            .eq("id_deteccao", deteccao_id)
            .order("timestamp_consulta", desc=True)
            .execute()
        )
        return response.data

    def listar_achados(self) -> list[dict]:
        """Retorna todas as consultas onde o resultado foi 'achado' (veículo furtado)."""
        response = (
            self.client.table(self.TABLE)
            .select("*, deteccao(*)")
            .eq("resultado", "achado")
            .order("timestamp_consulta", desc=True)
            .execute()
        )
        return response.data