from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from supabase import Client
from app.database.supabase_client import get_client

router = APIRouter(redirect_slashes=False)


def _count(client: Client, table: str, filtros: dict | None = None) -> int:
    q = client.table(table).select("id", count="exact")
    for k, v in (filtros or {}).items():
        q = q.eq(k, v)
    return q.execute().count or 0


@router.get("/resumo")
def resumo(client: Client = Depends(get_client)):
    """Tela Home — KPIs gerais."""
    hoje = datetime.now(timezone.utc).date().isoformat()

    total_voos     = _count(client, "voo")
    total_deteccoes = (
        client.table("deteccao").select("id", count="exact")
        .gte("timestamp", hoje).execute().count or 0
    )
    total_alertas  = _count(client, "alerta", {"status_alerta": "pendente"})
    total_pier     = _count(client, "consulta_pier", {"resultado": "achado"})

    ultimo = (
        client.table("voo").select("*")
        .order("timestamp_inicio", desc=True).limit(1).execute().data
    )

    return {
        "total_voos": total_voos,
        "total_deteccoes_hoje": total_deteccoes,
        "total_alertas_pendentes": total_alertas,
        "total_placas_pier_confirmadas": total_pier,
        "ultimo_voo": ultimo[0] if ultimo else None,
    }


@router.get("/voo-ativo/{drone_id}")
def voo_ativo(drone_id: int, client: Client = Depends(get_client)):
    """Tela Monitor — estado em tempo real do voo ativo."""
    voo_resp = (
        client.table("voo").select("*")
        .eq("id_drone", drone_id).eq("status_voo", "em_andamento")
        .maybe_single().execute()
    )
    voo = voo_resp.data if voo_resp else None
    if not voo:
        return {"voo_id": None, "status_voo": "sem_voo_ativo"}

    voo_id = voo["id"]

    tel = (
        client.table("telemetria").select("*")
        .eq("id_voo", voo_id).order("timestamp", desc=True).limit(1).execute().data
    )

    deteccoes = (
        client.table("deteccao")
        .select("*, consulta_pier(resultado), alerta:consulta_pier(alerta(id))")
        .eq("id_voo", voo_id).order("timestamp", desc=True).limit(10).execute().data
    )

    recentes = []
    for d in deteccoes:
        cp = d.get("consulta_pier") or []
        pier_status = cp[0]["resultado"] if cp else None
        recentes.append({
            "id": d["id"],
            "placa_lida": d.get("placa_lida"),
            "confianca_ocr": d.get("confianca_ocr"),
            "timestamp": d.get("timestamp"),
            "marca_veiculo": d.get("marca_veiculo"),
            "modelo_veiculo": d.get("modelo_veiculo"),
            "cor": d.get("cor"),
            "pier_status": pier_status,
        })

    return {
        "voo_id": voo_id,
        "status_voo": voo["status_voo"],
        "area_monitorada": voo.get("area_monitorada"),
        "timestamp_inicio": voo.get("timestamp_inicio"),
        "telemetria": tel[0] if tel else None,
        "deteccoes_recentes": recentes,
    }
