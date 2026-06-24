"""
smoke_test_rotas.py — teste de fumaça do fluxo de rotas.
Roda o ciclo completo (preparar -> commands -> iniciar -> resultado) contra o backend
e reporta passou/falhou em cada transição. Não substitui testes formais, serve para
validar rápido o fluxo a cada mudança, sem clicar no /docs.

Uso:
    python smoke_test_rotas.py
    python smoke_test_rotas.py https://seu-backend.onrender.com
"""
import sys
import httpx

# Windows: força UTF-8 no terminal para evitar erro cp1252
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

BASE = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "https://backend-render-l4u0.onrender.com/health"
ROUTE = "square"

# Contadores
passou = 0
falhou = 0


def checar(nome: str, condicao: bool, detalhe: str = ""):
    global passou, falhou
    if condicao:
        passou += 1
        print(f"  [OK]    {nome}")
    else:
        falhou += 1
        print(f"  [FALHA] {nome}  {detalhe}")


COMMANDS = [
    {"action": "frente",   "velocity_pct": 50, "duration_s": 1.5},
    {"action": "esquerda", "velocity_pct": 50, "duration_s": 1.5},
    {"action": "tras",     "velocity_pct": 50, "duration_s": 1.5},
    {"action": "direita",  "velocity_pct": 50, "duration_s": 1.5},
]

RESULTADO = {
    "route_id": ROUTE,
    "status": "completed",
    "battery_before": 84,
    "battery_after": 81,
    "commands_executed": [
        {**c, "rc_vector": {"lr": 0, "fb": 50, "ud": 0}} for c in COMMANDS
    ],
    "total_duration_s": 6.0,
    "errors": [],
}


def main():
    print(f"\nSmoke test de rotas  ->  {BASE}\n")

    with httpx.Client(base_url=BASE, timeout=15) as c:

        # 0. Health
        try:
            r = c.get("/health")
            checar("health responde", r.status_code == 200, f"status={r.status_code}")
        except Exception as e:
            print(f"  [FALHA] backend inacessível: {e}")
            print("\nAbortado. O backend está rodando?\n")
            sys.exit(1)

        # 1. Preparar (frontend)
        r = c.post("/rotas/preparar", json={"route_id": ROUTE})
        checar("POST /rotas/preparar", r.status_code in (200, 201), f"status={r.status_code}")
        checar("estado = preparando", r.json().get("estado") == "preparando", r.text[:120])

        # 2. Gateway puxa comando -> preparar
        r = c.get("/rotas/comando-pendente")
        j = r.json()
        checar("GET /comando-pendente = preparar",
               j.get("tipo") == "preparar" and j.get("route_id") == ROUTE, r.text[:120])

        # 3. Gateway entrega commands
        r = c.post(f"/rotas/{ROUTE}/commands", json={"route_id": ROUTE, "commands": COMMANDS})
        checar("POST /commands", r.status_code == 200, f"status={r.status_code}")
        body = r.json()
        checar("estado = pronta", body.get("estado") == "pronta", r.text[:120])
        checar("total_duration_s = 6.0", body.get("total_duration_s") == 6.0,
               f"recebido={body.get('total_duration_s')}")

        # 4. Frontend lê estado pronto
        r = c.get(f"/rotas/{ROUTE}/estado")
        j = r.json()
        checar("GET /estado = pronta", j.get("estado") == "pronta", r.text[:120])
        checar("commands presentes", isinstance(j.get("commands"), list) and len(j["commands"]) == 4,
               r.text[:120])

        # 5. Iniciar sem confirmar -> deve recusar
        r = c.post(f"/rotas/{ROUTE}/iniciar", json={"route_id": ROUTE, "confirmed": False})
        checar("iniciar sem confirmar é recusado", r.status_code == 400, f"status={r.status_code}")

        # 6. Iniciar confirmado
        r = c.post(f"/rotas/{ROUTE}/iniciar", json={"route_id": ROUTE, "confirmed": True})
        checar("POST /iniciar confirmado", r.status_code == 200, f"status={r.status_code}")
        checar("estado = iniciando", r.json().get("estado") == "iniciando", r.text[:120])

        # 7. Gateway puxa comando -> iniciar
        r = c.get("/rotas/comando-pendente")
        j = r.json()
        checar("GET /comando-pendente = iniciar", j.get("tipo") == "iniciar", r.text[:120])

        # 8. Gateway reporta resultado
        r = c.post(f"/rotas/{ROUTE}/resultado", json=RESULTADO)
        checar("POST /resultado", r.status_code == 200, f"status={r.status_code}")
        checar("estado = concluida", r.json().get("estado") == "concluida", r.text[:120])

        # 9. Estado final sem comando pendente
        r = c.get(f"/rotas/{ROUTE}/estado")
        j = r.json()
        checar("estado final = concluida", j.get("estado") == "concluida", r.text[:120])

    print(f"\n{'='*40}")
    print(f"  Passou: {passou}   Falhou: {falhou}")
    print(f"{'='*40}\n")
    sys.exit(0 if falhou == 0 else 1)


if __name__ == "__main__":
    main()