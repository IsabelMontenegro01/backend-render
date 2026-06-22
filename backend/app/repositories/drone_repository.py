from supabase import Client


class DroneRepository:
    """Operações de banco de dados para a tabela `drone`."""

    TABLE = "drone"

    def __init__(self, client: Client):
        self.client = client

    def criar(self, numero_serie: str, nome: str, modelo: str = "DJI Tello") -> dict:
        """Cria um novo drone e retorna o registro inserido."""
        response = (
            self.client.table(self.TABLE)
            .insert({"numero_serie": numero_serie, "nome": nome, "modelo": modelo})
            .execute()
        )
        return response.data[0]

    def listar_todos(self) -> list[dict]:
        # Kept: origin/develop new endpoint method
        response = self.client.table(self.TABLE).select("*").order("id").execute()
        return response.data

    def buscar_por_id(self, drone_id: int) -> dict | None:
        """Retorna um drone pelo seu ID, ou None se não encontrado."""
        response = (
            self.client.table(self.TABLE)
            .select("*")
            .eq("id", drone_id)
            .maybe_single()  # Kept: safer than .single()
            .execute()
        )
        return response.data

    def buscar_por_numero_serie(self, numero_serie: str) -> dict | None:
        """Retorna um drone pelo número de série."""
        response = (
            self.client.table(self.TABLE)
            .select("*")
            .eq("numero_serie", numero_serie)
            .maybe_single()  # Kept: Correct Python snake_case method
            .execute()
        )
        return response.data

    def listar_ativos(self) -> list[dict]:
        """Retorna todos os drones com status 'ativo'."""
        response = (
            self.client.table(self.TABLE)
            .select("*")
            .eq("status", "ativo")
            .execute()
        )
        return response.data

    def atualizar_status(self, drone_id: int, status: str) -> dict:
        """Atualiza o status de um drone (ex.: 'ativo', 'manutencao', 'inativo')."""
        response = (
            self.client.table(self.TABLE)
            .update({"status": status})
            .eq("id", drone_id)
            .execute()
        )
        # Kept: origin/develop error validation
        if not response.data:
            raise ValueError(f"Drone id={drone_id} não encontrado")
        return response.data[0]