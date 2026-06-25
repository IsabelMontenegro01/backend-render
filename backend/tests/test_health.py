import os
import httpx

BASE_URL = os.getenv(
    "BASE_URL",
    "https://backend-render-l4u0.onrender.com/"
)

def test_health():
    response = httpx.get(f"{BASE_URL}/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"