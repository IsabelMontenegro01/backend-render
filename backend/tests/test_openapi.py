import os
import httpx

BASE_URL = os.getenv(
    "BASE_URL",
    "https://backend-render-l4u0.onrender.com/"
)

def test_openapi_disponivel():
    response = httpx.get(
        f"{BASE_URL}/openapi.json"
    )

    assert response.status_code == 200

    schema = response.json()

    assert "/drones/" in schema["paths"]
    assert "/voos/" in schema["paths"]
    assert "/telemetria/" in schema["paths"]
    assert "/deteccoes/" in schema["paths"]
    assert "/consultas-pier/" in schema["paths"]
    assert "/alertas/" in schema["paths"]
    assert "/dashboard/resumo" in schema["paths"]