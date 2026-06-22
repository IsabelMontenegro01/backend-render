from pathlib import Path
from dotenv import load_dotenv

_backend_dir = Path(__file__).resolve().parent
load_dotenv(_backend_dir / ".env")
load_dotenv(_backend_dir.parent / ".env")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.routers import drones, voos, telemetria, deteccoes, consultas_pier, alertas, dashboard


app = FastAPI(
    title="Pier Drone API",
    description=(
        "API responsável por:\n"
        "- Gerenciar drones e voos\n"
        "- Receber e salvar leituras de telemetria\n"
        "- Registrar detecções de veículos capturados pelo drone\n"
        "- Salvar resultados de consultas à Pier API\n"
        "- Gerenciar alertas de veículos furtados\n"
        "- Endpoints agregados para o frontend (dashboard)"
    ),
    version="2.1.0",
    redirect_slashes=False,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(drones.router,         prefix="/drones",          tags=["Drones"])
app.include_router(voos.router,           prefix="/voos",            tags=["Voos"])
app.include_router(telemetria.router,     prefix="/telemetria",      tags=["Telemetria"])
app.include_router(deteccoes.router,      prefix="/deteccoes",       tags=["Detecções"])
app.include_router(consultas_pier.router, prefix="/consultas-pier",  tags=["Consultas Pier"])
app.include_router(alertas.router,        prefix="/alertas",         tags=["Alertas"])
app.include_router(dashboard.router,      prefix="/dashboard",       tags=["Dashboard"])


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}


_frontend = Path(__file__).resolve().parent.parent / "frontend"
if _frontend.is_dir():
    app.mount("/ui", StaticFiles(directory=str(_frontend), html=True), name="frontend")
