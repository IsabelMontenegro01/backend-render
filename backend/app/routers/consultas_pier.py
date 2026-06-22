from typing import Dict, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from supabase import Client
from app.database.supabase_client import get_client
from app.repositories.consulta_pier_repository import ConsultaPierRepository

router = APIRouter(redirect_slashes=False)

STATUS_MAP = {"found": "achado", "not_found": "nao_achado"}


class VeiculoDados(BaseModel):
    make: Optional[str] = None
    model: Optional[str] = None
    fabrication_year: Optional[int] = None


class RespostaPierUnica(BaseModel):
    vehicle_lookup_id: Optional[str] = None
    vehicle: Optional[VeiculoDados] = None
    status: str


class ConsultaCreate(BaseModel):
    deteccao_id: int
    placa_consultada: str
    resultado: str
    resposta_raw: dict


def get_repo(client: Client = Depends(get_client)) -> ConsultaPierRepository:
    return ConsultaPierRepository(client)


@router.post("/", status_code=201)
def registrar_consulta(body: ConsultaCreate, repo: ConsultaPierRepository = Depends(get_repo)):
    return repo.registrar(
        body.deteccao_id,
        body.placa_consultada,
        body.resultado,
        body.resposta_raw,
    )


@router.post("/batch", status_code=201)
def salvar_consultas_pier_batch(
    payload: Dict[str, RespostaPierUnica],
    id_deteccao: Optional[int] = Query(None),
    repo: ConsultaPierRepository = Depends(get_repo),
):
    """
    Recebe o mock da Pier no formato {placa: {status, vehicle, ...}} e
    persiste uma linha por placa, convertendo status → resultado.
    `id_deteccao` é opcional: vincula todas as consultas à mesma detecção.
    """
    if not payload:
        return []

    salvos = []
    for placa, dados in payload.items():
        resultado = STATUS_MAP.get(dados.status, "nao_achado")
        resposta_raw = dados.model_dump()
        registro = repo.registrar(
            deteccao_id=id_deteccao,
            placa_consultada=placa,
            resultado=resultado,
            resposta_raw=resposta_raw,
        )
        salvos.append(registro)
    return salvos


@router.get("/achados")
def listar_achados(repo: ConsultaPierRepository = Depends(get_repo)):
    return repo.listar_achados()


@router.get("/{consulta_id}")
def buscar_consulta(consulta_id: int, repo: ConsultaPierRepository = Depends(get_repo)):
    consulta = repo.buscar_por_id(consulta_id)
    if consulta is None:
        raise HTTPException(status_code=404, detail="Consulta não encontrada")
    return consulta


@router.get("/deteccao/{deteccao_id}")
def listar_por_deteccao(deteccao_id: int, repo: ConsultaPierRepository = Depends(get_repo)):
    return repo.listar_por_deteccao(deteccao_id)
