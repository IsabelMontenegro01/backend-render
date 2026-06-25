"""
app/services/pier_client.py — cliente HTTP para a Pier API com retry/backoff.

Estratégia de retry:
- Tentativas: até MAX_RETRIES vezes por chamada.
- Backoff exponencial com jitter: espera base * 2^tentativa + ruído aleatório,
  para evitar thundering herd quando vários workers tentam ao mesmo tempo.
- Erros retriáveis: timeouts, erros de rede, e respostas 5xx da Pier.
- Erros NÃO retriáveis: 4xx (exceto 429 Too Many Requests), que indicam
  problema na requisição em si (placa inválida, credenciais erradas etc.).
- Token: renovado automaticamente antes de expirar (singleton thread-safe).
  Se a renovação falhar, também aplica backoff.
"""

import os
import time
import random
import threading
import logging

import httpx

logger = logging.getLogger(__name__)

# ── Configuração ──────────────────────────────────────────────────────────────

PIER_URL       = os.getenv("PIER_URL", "https://gw2.stag.pier.zone")
AUTH_URL       = os.getenv(
    "PIER_AUTH_URL",
    "https://auth.stag.pier.zone/realms/pier-ext-auth-apis/protocol/openid-connect/token",
)
PIER_USERNAME  = os.getenv("PIER_USERNAME", "inteli_grupo1")
PIER_PASSWORD  = os.getenv("PIER_PASSWORD", "")
PIER_CLIENT_ID = os.getenv("PIER_CLIENT_ID", "pier-ext-auth-apis-client")
PIER_SECRET    = os.getenv("PIER_CLIENT_SECRET", "")

# Parâmetros de retry
MAX_RETRIES     = int(os.getenv("PIER_MAX_RETRIES", "4"))
BACKOFF_BASE_S  = float(os.getenv("PIER_BACKOFF_BASE_S", "1.0"))  # segundos
BACKOFF_MAX_S   = float(os.getenv("PIER_BACKOFF_MAX_S", "30.0"))  # teto do backoff
REQUEST_TIMEOUT = float(os.getenv("PIER_REQUEST_TIMEOUT_S", "15.0"))
AUTH_TIMEOUT    = float(os.getenv("PIER_AUTH_TIMEOUT_S", "15.0"))


# ── Erros customizados ────────────────────────────────────────────────────────

class PierError(Exception):
    """Erro genérico ao chamar a Pier."""

class PierAuthError(PierError):
    """Falha de autenticação com a Pier (não retriável)."""

class PierNotFoundError(PierError):
    """Recurso não encontrado na Pier (não retriável, resultado esperado)."""

class PierClientError(PierError):
    """Erro 4xx que indica problema na requisição (não retriável)."""

class PierServerError(PierError):
    """Erro 5xx ou timeout (retriável)."""


# ── Utilitário de retry ───────────────────────────────────────────────────────

def _exponential_backoff(attempt: int) -> float:
    """
    Calcula tempo de espera com backoff exponencial + jitter completo.
    Fórmula: min(base * 2^attempt, max) + random(0, base)
    O jitter evita que múltiplos workers colidam exatamente no mesmo instante.
    """
    delay = min(BACKOFF_BASE_S * (2 ** attempt), BACKOFF_MAX_S)
    jitter = random.uniform(0, BACKOFF_BASE_S)
    return delay + jitter


def _is_retryable(status_code: int) -> bool:
    """5xx e 429 (rate limit) são retriáveis; demais 4xx não."""
    return status_code >= 500 or status_code == 429


# ── Cliente Pier ──────────────────────────────────────────────────────────────

class PierClient:
    """
    Singleton thread-safe para chamadas à Pier API.

    Gerencia token OAuth2 com renovação automática e aplica retry/backoff
    exponencial em falhas transientes (rede, timeouts, 5xx, 429).
    """

    _instance = None
    _lock     = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    inst = super().__new__(cls)
                    inst._token      = None
                    inst._expira_em  = 0.0
                    inst._token_lock = threading.Lock()
                    cls._instance = inst
        return cls._instance

    # ── Gerenciamento de token ────────────────────────────────────────────────

    def _obter_token(self) -> str:
        """
        Autentica na Pier e armazena o access_token.
        Aplica retry/backoff em falhas de rede ou 5xx do servidor de auth.
        """
        last_err: Exception | None = None

        for attempt in range(MAX_RETRIES):
            try:
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
                    timeout=AUTH_TIMEOUT,
                )

                if resp.status_code == 401:
                    raise PierAuthError("Credenciais inválidas para autenticação na Pier.")

                if not _is_retryable(resp.status_code):
                    resp.raise_for_status()   # levanta para 4xx inesperados

                if resp.status_code >= 500 or resp.status_code == 429:
                    raise PierServerError(f"Auth server retornou {resp.status_code}")

                data = resp.json()
                self._token     = data["access_token"]
                # Renova 30s antes de expirar para evitar uso de token vencido
                self._expira_em = time.monotonic() + data.get("expires_in", 300) - 30
                logger.info("Token Pier obtido com sucesso (tentativa %d).", attempt + 1)
                return self._token

            except PierAuthError:
                raise   # credenciais erradas: sem retry

            except (httpx.TimeoutException, httpx.NetworkError, PierServerError) as exc:
                last_err = exc
                wait = _exponential_backoff(attempt)
                logger.warning(
                    "Falha ao obter token Pier (tentativa %d/%d): %s. Aguardando %.2fs.",
                    attempt + 1, MAX_RETRIES, exc, wait,
                )
                if attempt < MAX_RETRIES - 1:
                    time.sleep(wait)

        raise PierError(f"Não foi possível obter token após {MAX_RETRIES} tentativas: {last_err}")

    def _token_valido(self) -> str:
        """Retorna o token atual, renovando se necessário (thread-safe)."""
        with self._token_lock:
            if not self._token or time.monotonic() >= self._expira_em:
                return self._obter_token()
            return self._token

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._token_valido()}",
            "Content-Type":  "application/json",
        }

    # ── Chamadas com retry ────────────────────────────────────────────────────

    def _request(self, method: str, url: str, **kwargs) -> dict:
        """
        Executa uma requisição HTTP com retry/backoff.

        Em caso de 401 (token expirado no meio da execução), renova o token
        uma vez e tenta novamente antes de iniciar o ciclo de retry.
        """
        last_err: Exception | None = None
        token_renovado = False

        for attempt in range(MAX_RETRIES):
            try:
                resp = httpx.request(
                    method, url,
                    headers=self._headers(),
                    timeout=REQUEST_TIMEOUT,
                    **kwargs,
                )

                # Token expirou durante a execução → renova e tenta mais uma vez
                if resp.status_code == 401 and not token_renovado:
                    logger.info("Token expirado em meio à requisição; renovando.")
                    with self._token_lock:
                        self._expira_em = 0.0   # força renovação
                    token_renovado = True
                    continue

                if resp.status_code == 404:
                    raise PierNotFoundError(f"Recurso não encontrado: {url}")

                if resp.status_code == 401:
                    raise PierAuthError("Não autorizado após renovação de token.")

                if not _is_retryable(resp.status_code):
                    if 400 <= resp.status_code < 500:
                        raise PierClientError(
                            f"Erro de cliente Pier ({resp.status_code}): {resp.text[:200]}"
                        )
                    resp.raise_for_status()

                if _is_retryable(resp.status_code):
                    raise PierServerError(f"Pier retornou {resp.status_code}")

                return resp.json()

            except (PierNotFoundError, PierAuthError, PierClientError):
                raise   # erros não-retriáveis: propaga imediatamente

            except (httpx.TimeoutException, httpx.NetworkError, PierServerError) as exc:
                last_err = exc
                wait = _exponential_backoff(attempt)
                logger.warning(
                    "[%s %s] Falha transiente (tentativa %d/%d): %s. Aguardando %.2fs.",
                    method, url, attempt + 1, MAX_RETRIES, exc, wait,
                )
                if attempt < MAX_RETRIES - 1:
                    time.sleep(wait)

        raise PierError(
            f"Requisição {method} {url} falhou após {MAX_RETRIES} tentativas: {last_err}"
        )

    # ── Endpoints Pier ────────────────────────────────────────────────────────

    def consultar_placa(self, placa: str, latitude: float, longitude: float) -> dict:
        """
        Consulta um veículo pela placa.

        Retorna:
            dict com os dados do veículo se encontrado.
            {"status": "not_found"} se a placa não constar na base da Pier.

        Raises:
            PierAuthError: credenciais inválidas.
            PierClientError: requisição malformada.
            PierError: falha após esgotar retries.
        """
        try:
            return self._request(
                "POST",
                f"{PIER_URL}/v1/inteli/vehicle-lookups",
                json={
                    "license_plate": placa,
                    "geolocation": {"latitude": latitude, "longitude": longitude},
                },
            )
        except PierNotFoundError:
            # 404 é resultado de negócio esperado, não erro de infraestrutura
            return {"status": "not_found"}

    def confirmar_lookup(self, vehicle_lookup_id: str, is_correct: bool = True) -> dict:
        """
        Confirma (ou rejeita) o resultado de um vehicle-lookup.

        Raises:
            PierAuthError, PierClientError, PierError.
        """
        return self._request(
            "POST",
            f"{PIER_URL}/v1/inteli/vehicle-lookups/{vehicle_lookup_id}/confirmation",
            json={"is_correct": is_correct},
        )


# Instância global (singleton)
pier_client = PierClient()