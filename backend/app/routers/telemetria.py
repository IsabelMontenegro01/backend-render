from fastapi import APIRouter, Depends
from pydantic import BaseModel
from supabase import Client
from app.database.supabase_client import get_client
from app.repositories.telemetria_repository import TelemetriaRepository

router = APIRouter(redirect_slashes=False)


class TelemetriaCreate(BaseModel):
    id_voo: int
    dados: dict


class TelemetriaBatch(BaseModel):
    id_voo: int
    leituras: list[dict]


def get_repo(client: Client = Depends(get_client)) -> TelemetriaRepository:
    return TelemetriaRepository(client)


@router.post("/", status_code=201)
def inserir_telemetria(body: TelemetriaCreate, repo: TelemetriaRepository = Depends(get_repo)):
    return repo.inserir(body.id_voo, body.dados)


@router.post("/batch", status_code=201)
def inserir_batch(body: TelemetriaBatch, repo: TelemetriaRepository = Depends(get_repo)):
    return repo.inserir_batch(body.id_voo, body.leituras)


@router.get("/voo/{voo_id}")
def listar_por_voo(
    voo_id: int,
    limite: int = 500,
    repo: TelemetriaRepository = Depends(get_repo),
):
    return repo.listar_por_voo(voo_id, limite)


@router.get("/voo/{voo_id}/ultima")
def ultima_leitura(voo_id: int, repo: TelemetriaRepository = Depends(get_repo)):
    return repo.ultima_leitura(voo_id)
