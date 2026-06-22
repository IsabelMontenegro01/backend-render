import os
import time
import threading
import httpx

PIER_URL       = os.getenv("PIER_URL", "https://gw2.stag.pier.zone")
AUTH_URL       = os.getenv(
    "PIER_AUTH_URL",
    "https://auth.stag.pier.zone/realms/pier-ext-auth-apis/protocol/openid-connect/token",
)
PIER_USERNAME  = os.getenv("PIER_USERNAME", "inteli_grupo1")
PIER_PASSWORD  = os.getenv("PIER_PASSWORD", "")
PIER_CLIENT_ID = os.getenv("PIER_CLIENT_ID", "pier-ext-auth-apis-client")
PIER_SECRET    = os.getenv("PIER_CLIENT_SECRET", "")


class PierClient:
    _instance = None
    _lock     = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._token = None
                    cls._instance._expira_em = 0.0
        return cls._instance

    # ── token ─────────────────────────────────────────────────────────────────

    def _obter_token(self) -> str:
        resp = httpx.post(
            AUTH_URL,
            data={
                "grant_type":    "password",
                "username":      PIER_USERNAME,
                "password":      PIER_PASSWORD,
                "client_id":     PIER_CLIENT_ID,
                "client_secret": PIER_SECRET,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        # Renova 30s antes de expirar
        self._token     = data["access_token"]
        self._expira_em = time.time() + data.get("expires_in", 300) - 30
        return self._token

    def _token_valido(self) -> str:
        if not self._token or time.time() >= self._expira_em:
            return self._obter_token()
        return self._token

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._token_valido()}",
            "Content-Type": "application/json",
        }

    # ── chamadas Pier ─────────────────────────────────────────────────────────

    def consultar_placa(self, placa: str, latitude: float, longitude: float) -> dict:
        resp = httpx.post(
            f"{PIER_URL}/v1/inteli/vehicle-lookups",
            json={"license_plate": placa, "geolocation": {"latitude": latitude, "longitude": longitude}},
            headers=self._headers(),
            timeout=15,
        )
        # 404 = placa não encontrada (esperado, não é erro)
        if resp.status_code == 404:
            return {"status": "not_found"}
        resp.raise_for_status()
        return resp.json()

    def confirmar_lookup(self, vehicle_lookup_id: str, is_correct: bool = True) -> dict:
        resp = httpx.post(
            f"{PIER_URL}/v1/inteli/vehicle-lookups/{vehicle_lookup_id}/confirmation",
            json={"is_correct": is_correct},
            headers=self._headers(),
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()


pier_client = PierClient()
