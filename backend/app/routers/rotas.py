from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from supabase import Client
from app.database.supabase_client import get_client
from app.repositories.rota_repository import RotaRepository

router = APIRouter(redirect_slashes=False)

ROTAS_VALIDAS = {"square", "road"}


# ── Schemas ───────────────────────────────────────────────────────────────────

class PrepararRota(BaseModel):
    route_id: str


class Comando(BaseModel):
    action: str
    velocity_pct: int
    duration_s: float


class CommandsRota(BaseModel):
    route_id: str
    commands: list[Comando]


class IniciarRota(BaseModel):
    route_id: str
    confirmed: bool


def get_repo(client: Client = Depends(get_client)) -> RotaRepository:
    return RotaRepository(client)


def _validar(route_id: str):
    if route_id not in ROTAS_VALIDAS:
        raise HTTPException(status_code=400, detail=f"route_id inválido: {route_id}")


# ── Frontend → Backend ────────────────────────────────────────────────────────

@router.post("/preparar", status_code=201)
def preparar(body: PrepararRota, repo: RotaRepository = Depends(get_repo)):
    _validar(body.route_id)
    return repo.preparar(body.route_id)


@router.post("/{route_id}/iniciar", status_code=200)
def iniciar(route_id: str, body: IniciarRota, repo: RotaRepository = Depends(get_repo)):
    _validar(route_id)
    if not body.confirmed:
        raise HTTPException(status_code=400, detail="Rota não confirmada")
    estado = repo.buscar_estado(route_id)
    if not estado or estado.get("estado") != "pronta":
        raise HTTPException(status_code=409, detail="Rota não está pronta para iniciar")
    return repo.iniciar(route_id)


@router.get("/{route_id}/estado")
def estado(route_id: str, repo: RotaRepository = Depends(get_repo)):
    _validar(route_id)
    dados = repo.buscar_estado(route_id)
    if not dados:
        return {"route_id": route_id, "estado": "idle", "commands": None, "total_duration_s": None}
    return {
        "route_id": route_id,
        "estado": dados.get("estado"),
        "commands": dados.get("commands"),
        "total_duration_s": dados.get("total_duration_s"),
        "resultado": dados.get("resultado"),
    }


# ── Gateway → Backend ─────────────────────────────────────────────────────────

@router.get("/comando-pendente")
def comando_pendente(repo: RotaRepository = Depends(get_repo)):
    """Gateway puxa o próximo comando (polling)."""
    return repo.comando_pendente()


@router.post("/{route_id}/commands", status_code=200)
def entregar_commands(route_id: str, body: CommandsRota, repo: RotaRepository = Depends(get_repo)):
    """Gateway entrega a sequência de comandos da rota."""
    _validar(route_id)
    commands = [c.model_dump() for c in body.commands]
    return repo.gravar_commands(route_id, commands)


@router.post("/{route_id}/resultado", status_code=200)
def reportar_resultado(route_id: str, resultado: dict, repo: RotaRepository = Depends(get_repo)):
    """Gateway reporta o resultado da execução."""
    _validar(route_id)
    return repo.gravar_resultado(route_id, resultado)
