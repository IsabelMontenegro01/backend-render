from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from supabase import Client
from app.database.supabase_client import get_client
from app.repositories.voo_repository import VooRepository

router = APIRouter(redirect_slashes=False)


class VooIniciar(BaseModel):
    id_drone: int
    area_monitorada: str | None = None


class VooFinalizar(BaseModel):
    tempo_total_motores: int | None = None


def get_repo(client: Client = Depends(get_client)) -> VooRepository:
    return VooRepository(client)


@router.post("/", status_code=201)
def iniciar_voo(body: VooIniciar, repo: VooRepository = Depends(get_repo)):
    return repo.iniciar(body.id_drone, body.area_monitorada)


@router.post("/{voo_id}/finalizar")
def finalizar_voo(voo_id: int, body: VooFinalizar, repo: VooRepository = Depends(get_repo)):
    try:
        return repo.finalizar(voo_id, body.tempo_total_motores)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/{voo_id}")
def buscar_voo(voo_id: int, repo: VooRepository = Depends(get_repo)):
    voo = repo.buscar_por_id(voo_id)
    if voo is None:
        raise HTTPException(status_code=404, detail="Voo não encontrado")
    return voo


@router.get("/drone/{drone_id}")
def listar_por_drone(drone_id: int, repo: VooRepository = Depends(get_repo)):
    return repo.listar_por_drone(drone_id)


@router.get("/drone/{drone_id}/em-andamento")
def buscar_em_andamento(drone_id: int, repo: VooRepository = Depends(get_repo)):
    return repo.buscar_em_andamento(drone_id)
