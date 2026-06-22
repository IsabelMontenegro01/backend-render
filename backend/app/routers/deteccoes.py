from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from supabase import Client

from app.database.supabase_client import get_client
from app.repositories.deteccao_repository import DeteccaoRepository
from app.services.processamento_deteccao import ProcessamentoDeteccaoService

router = APIRouter(redirect_slashes=False)


# ── Schemas ──────────────────────────────────────────────────────────────────

class DeteccaoCreate(BaseModel):
    id_voo: int
    id_telemetria: Optional[int] = None
    dados: dict


class DeteccaoBatchItem(BaseModel):
    id_voo: int
    id_telemetria: Optional[int] = None
    dados: dict


class VlmResultado(BaseModel):
    cor:             Optional[str]   = None
    marca:           Optional[str]   = None
    modelo:          Optional[str]   = None
    ano_aproximado:  Optional[str]   = None
    dano_detectado:  Optional[bool]  = None
    descricao_dano:  Optional[str]   = None
    latency_ms:      Optional[float] = None


# ── Dep ───────────────────────────────────────────────────────────────────────

def get_repo(client: Client = Depends(get_client)) -> DeteccaoRepository:
    return DeteccaoRepository(client)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/", status_code=201)
async def registrar_deteccao(body: DeteccaoCreate):
    return await ProcessamentoDeteccaoService.processar(
        id_voo=body.id_voo,
        id_telemetria=body.id_telemetria,
        dados=body.dados,
    )


@router.post("/batch", status_code=201)
async def registrar_batch(itens: list[DeteccaoBatchItem]):
    """Drena fila SQLite offline: aceita lista de detecções pendentes."""
    resultados = []
    for item in itens:
        resultado = await ProcessamentoDeteccaoService.processar(
            id_voo=item.id_voo,
            id_telemetria=item.id_telemetria,
            dados=item.dados,
        )
        resultados.append(resultado)
    return resultados


@router.post("/{deteccao_id}/vlm-resultado", status_code=200)
def registrar_vlm(
    deteccao_id: int,
    body: VlmResultado,
    repo: DeteccaoRepository = Depends(get_repo),
):
    """Recebe resultado do Moondream2 e atualiza a detecção."""
    atualizado = repo.atualizar_vlm(deteccao_id, body.model_dump(exclude_none=True))
    if atualizado is None:
        raise HTTPException(status_code=404, detail="Detecção não encontrada")
    return atualizado


@router.get("/historico/placas")
def historico_placas(limite: int = 200, repo: DeteccaoRepository = Depends(get_repo)):
    return repo.listar_historico_placas(limite)


@router.get("/voo/{voo_id}")
def listar_por_voo(voo_id: int, repo: DeteccaoRepository = Depends(get_repo)):
    return repo.listar_por_voo(voo_id)


@router.get("/placa/{placa}")
def buscar_por_placa(placa: str, repo: DeteccaoRepository = Depends(get_repo)):
    return repo.buscar_por_placa(placa)


@router.get("/{deteccao_id}")
def buscar_deteccao(deteccao_id: int, repo: DeteccaoRepository = Depends(get_repo)):
    deteccao = repo.buscar_por_id(deteccao_id)
    if deteccao is None:
        raise HTTPException(status_code=404, detail="Detecção não encontrada")
    return deteccao
