from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from supabase import Client
from app.database.supabase_client import get_client
from app.repositories.alerta_repository import AlertaRepository

router = APIRouter(redirect_slashes=False)


class AlertaCreate(BaseModel):
    consulta_id: int
    operador_notificado: str | None = None


class AlertaStatusUpdate(BaseModel):
    status: str
    operador: str | None = None


def get_repo(client: Client = Depends(get_client)) -> AlertaRepository:
    return AlertaRepository(client)


@router.post("/", status_code=201)
def criar_alerta(body: AlertaCreate, repo: AlertaRepository = Depends(get_repo)):
    return repo.criar(body.consulta_id, body.operador_notificado)


@router.get("/pendentes")
def listar_pendentes(repo: AlertaRepository = Depends(get_repo)):
    return repo.listar_pendentes()


@router.get("/{alerta_id}")
def buscar_alerta(alerta_id: int, repo: AlertaRepository = Depends(get_repo)):
    alerta = repo.buscar_por_id(alerta_id)
    if alerta is None:
        raise HTTPException(status_code=404, detail="Alerta não encontrado")
    return alerta


@router.patch("/{alerta_id}/status")
def atualizar_status(
    alerta_id: int,
    body: AlertaStatusUpdate,
    repo: AlertaRepository = Depends(get_repo),
):
    try:
        return repo.atualizar_status(alerta_id, body.status, body.operador)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/consulta/{consulta_id}")
def listar_por_consulta(consulta_id: int, repo: AlertaRepository = Depends(get_repo)):
    return repo.listar_por_consulta(consulta_id)
