from datetime import datetime, timezone
from supabase import Client
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
logger.setLevel(logging.INFO)


class RotaRepository:
    """Operações de banco para a tabela `rota_execucao`."""

    TABLE = "rota_execucao"

    def __init__(self, client: Client):
        self.client = client

    def _upsert(self, route_id: str, campos: dict) -> dict:
        campos = {
            "route_id": route_id,
            "atualizado_em": datetime.now(timezone.utc).isoformat(),
            **campos,
        }
        response = (
            self.client.table(self.TABLE)
            .upsert(campos, on_conflict="route_id")
            .execute()
        )
        return response.data[0]

    # ── transições de estado ──────────────────────────────────────────────────

    def preparar(self, route_id: str) -> dict:
        """Frontend pediu preparar → grava comando para o gateway."""
        return self._upsert(route_id, {
            "estado": "preparando",
            "comando_pendente": {"tipo": "preparar"},
            "commands": None,
            "resultado": None,
            "total_duration_s": None,
        })

    def gravar_commands(self, route_id: str, commands: list) -> dict:
        """Gateway devolveu os comandos da rota → estado pronta."""
        total = sum(float(c.get("duration_s", 0)) for c in commands)
        return self._upsert(route_id, {
            "estado": "pronta",
            "commands": commands,
            "total_duration_s": round(total, 2),
            "comando_pendente": None,
        })

    def iniciar(self, route_id: str) -> dict:
        """Frontend confirmou → grava comando iniciar para o gateway."""
        return self._upsert(route_id, {
            "estado": "iniciando",
            "comando_pendente": {"tipo": "iniciar"},
        })

    def gravar_resultado(self, route_id: str, resultado: dict) -> dict:
        """Gateway reportou execução → estado concluida (ou erro)."""
        estado = "erro" if resultado.get("errors") else "concluida"
        return self._upsert(route_id, {
            "estado": estado,
            "resultado": resultado,
            "comando_pendente": None,
        })

    # ── consultas ─────────────────────────────────────────────────────────────

    def comando_pendente(self) -> dict:
        """Gateway puxa o próximo comando pendente de qualquer rota."""
        response = (
            self.client.table(self.TABLE)
            .select("route_id, comando_pendente")
            .not_.is_("comando_pendente", "null")
            .limit(1)
            .execute()
        )
        # Compatível com objetos reais e objetos mockados dos testes
        data = getattr(response, "data", None)
        logger.info("comando_pendente response=%r data=%r", response, data)
        print("DEBUG comando_pendente response=", repr(response), "data=", repr(data))

        if not data:
            print("DEBUG comando_pendente no data -> returning tipo=None")
            return {"tipo": None, "route_id": None}

        # Normalize into a list-like sequence to handle MagicMock wrappers
        if isinstance(data, (list, tuple)):
            seq = data
        else:
            try:
                seq = list(data)
            except Exception:
                seq = [data]

        linha = seq[0] if len(seq) > 0 else {}
        logger.info("comando_pendente linha=%r", linha)
        print("DEBUG comando_pendente linha=", repr(linha))
        if not isinstance(linha, dict):
            print("DEBUG comando_pendente linha not dict -> returning tipo=None")
            return {"tipo": None, "route_id": None}

        pend = linha.get("comando_pendente") or {}
        logger.info("comando_pendente pend=%r", pend)
        print("DEBUG comando_pendente pend=", repr(pend))
        if not isinstance(pend, dict):
            print("DEBUG comando_pendente pend not dict -> returning tipo=None")
            return {"tipo": None, "route_id": linha.get("route_id")}

        return {"tipo": pend.get("tipo"), "route_id": linha.get("route_id")}

    def limpar_comando(self, route_id: str) -> None:
        self._upsert(route_id, {"comando_pendente": None})

    def buscar_estado(self, route_id: str) -> dict | None:
        response = (
            self.client.table(self.TABLE)
            .select("*")
            .eq("route_id", route_id)
            .maybe_single()
            .execute()
        )
        return response.data if response else None
