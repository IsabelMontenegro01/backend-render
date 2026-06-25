import os
import httpx

BASE_URL = os.getenv(
    "BASE_URL",
    "https://backend-render-l4u0.onrender.com"
)

ROTAS = [
    "/health",
    "/openapi.json",
    "/drones/",
    "/drones/ativos",
    "/consultas-pier/achados",
    "/alertas/pendentes",
    "/dashboard/resumo",
]

def test_rotas_principais():
    with httpx.Client(timeout=20) as client:

        for rota in ROTAS:

            response = client.get(
                f"{BASE_URL}{rota}"
            )

            assert response.status_code < 500