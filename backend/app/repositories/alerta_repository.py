from supabase import Client


class AlertaRepository:
    """Operações de banco de dados para a tabela `alerta`."""

    TABLE = "alerta"

    def __init__(self, client: Client):
        self.client = client

    def criar(self, consulta_id: int, operador_notificado: str | None = None) -> dict:
        """
        Cria um alerta vinculado a uma consulta Pier com resultado 'achado'.

        Args:
            consulta_id: FK para a consulta que gerou o alerta.
            operador_notificado: Identificador do operador notificado (opcional).
        """
        response = (
            self.client.table(self.TABLE)
            .insert(
                {
                    "id_consulta": consulta_id,
                    "status_alerta": "pendente",
                    "operador_notificado": operador_notificado,
                }
            )
            .execute()
        )
        return response.data[0]

    def buscar_por_id(self, alerta_id: int) -> dict | None:
        """Retorna um alerta pelo ID."""
        response = (
            self.client.table(self.TABLE)
            .select("*")
            .eq("id", alerta_id)
            .maybe_single()  # Mantido: origin/develop (mais seguro contra falhas de ID inexistente)
            .execute()
        )
        return response.data

    def listar_pendentes(self) -> list[dict]:
        """Retorna todos os alertas com status 'pendente' (não confirmados)."""
        response = (
            self.client.table(self.TABLE)
            .select("*, consulta_pier(*, deteccao(*, voo(*)))")
            .eq("status_alerta", "pendente")
            .order("timestamp", desc=True)
            .execute()
        )
        return response.data

    def atualizar_status(
        self, alerta_id: int, status: str, operador: str | None = None
    ) -> dict:
        """
        Atualiza o status de um alerta.

        Args:
            alerta_id: ID do alerta a atualizar.
            status: Novo status ('confirmado', 'descartado', 'pendente').
            operador: Operador que realizou a ação (opcional).
        """
        payload: dict = {"status_alerta": status}
        if operador:
            payload["operador_notificado"] = operador

        response = (
            self.client.table(self.TABLE)
            .update(payload)
            .eq("id", alerta_id)
            .execute()
        )
        # Mantido: origin/develop (validação de erro robusta)
        if not response.data:
            raise ValueError(f"Alerta id={alerta_id} não encontrado")
        return response.data[0]

    def listar_por_consulta(self, consulta_id: int) -> list[dict]:
        """Retorna todos os alertas gerados por uma consulta Pier."""
        response = (
            self.client.table(self.TABLE)
            .select("*")
            .eq("id_consulta", consulta_id)
            .order("timestamp", desc=True)
            .execute()
        )
        return response.data