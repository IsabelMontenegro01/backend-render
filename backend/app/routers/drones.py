from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from supabase import Client
from app.database.supabase_client import get_client
from app.repositories.drone_repository import DroneRepository

router = APIRouter(redirect_slashes=False)


class DroneCreate(BaseModel):
    numero_serie: str
    nome: str
    modelo: str = "DJI Tello"


class DroneStatusUpdate(BaseModel):
    status: str


def get_repo(client: Client = Depends(get_client)) -> DroneRepository:
    return DroneRepository(client)


@router.post("/", status_code=201)
def criar_drone(body: DroneCreate, repo: DroneRepository = Depends(get_repo)):
    return repo.criar(body.numero_serie, body.nome, body.modelo)


@router.get("/")
def listar_drones(repo: DroneRepository = Depends(get_repo)):
    return repo.listar_todos()


@router.get("/ativos")
def listar_ativos(repo: DroneRepository = Depends(get_repo)):
    return repo.listar_ativos()


@router.get("/{drone_id}")
def buscar_drone(drone_id: int, repo: DroneRepository = Depends(get_repo)):
    drone = repo.buscar_por_id(drone_id)
    if drone is None:
        raise HTTPException(status_code=404, detail="Drone não encontrado")
    return drone


@router.patch("/{drone_id}/status")
def atualizar_status(
    drone_id: int,
    body: DroneStatusUpdate,
    repo: DroneRepository = Depends(get_repo),
):
    try:
        return repo.atualizar_status(drone_id, body.status)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
