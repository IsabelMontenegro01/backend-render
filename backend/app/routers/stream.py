"""
stream.py — relay de vídeo do drone via WebSocket.
Gateway empurra frames JPEG (binário) → backend guarda o último por gateway
→ frontend recebe o último frame continuamente.

Regra de ouro: o gateway abre a conexão de saída, o frontend nunca fala com o
gateway direto. Tudo passa pelo backend.

Rotas:
  WS /stream/gateway/{gateway_id}/publish   ← gateway empurra frames
  WS /stream/gateway/{gateway_id}/watch     ← frontend recebe frames
  GET /stream/gateway/{gateway_id}/status   → util p/ saber se há stream ativo
"""
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()

# Último frame por gateway (só o mais recente, sem fila → baixa latência)
_ultimo_frame: dict[str, bytes] = {}
# Marca se há um publisher ativo por gateway
_publicando: dict[str, bool] = {}


@router.websocket("/gateway/{gateway_id}/publish")
async def publish(websocket: WebSocket, gateway_id: str):
    """Gateway conecta aqui e empurra frames JPEG binários."""
    await websocket.accept()
    _publicando[gateway_id] = True
    print(f"[STREAM] gateway {gateway_id} publicando")
    try:
        while True:
            frame = await websocket.receive_bytes()
            _ultimo_frame[gateway_id] = frame  # sobrescreve, não acumula
    except WebSocketDisconnect:
        print(f"[STREAM] gateway {gateway_id} parou de publicar")
    finally:
        _publicando[gateway_id] = False
        _ultimo_frame.pop(gateway_id, None)


@router.websocket("/gateway/{gateway_id}/watch")
async def watch(websocket: WebSocket, gateway_id: str):
    """Frontend conecta aqui e recebe o último frame continuamente."""
    await websocket.accept()
    print(f"[STREAM] viewer conectou em {gateway_id}")
    try:
        while True:
            frame = _ultimo_frame.get(gateway_id)
            if frame is not None:
                await websocket.send_bytes(frame)
            # ~20 fps de envio; ajusta latência vs banda
            await asyncio.sleep(0.05)
    except WebSocketDisconnect:
        print(f"[STREAM] viewer saiu de {gateway_id}")


@router.get("/gateway/{gateway_id}/status")
def status(gateway_id: str):
    """Frontend usa para saber se o drone está transmitindo."""
    return {
        "gateway_id": gateway_id,
        "ativo": _publicando.get(gateway_id, False),
        "tem_frame": gateway_id in _ultimo_frame,
    }
