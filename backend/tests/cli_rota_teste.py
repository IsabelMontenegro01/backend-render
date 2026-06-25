"""
cli_rota_teste.py — simula o frontend para testar rotas pela linha de comando.
Dispara preparar -> aguarda pronta -> inicia, e o tello_detector (já rodando) executa.

NÃO conecta no drone. Só fala com o backend. Pode rodar em outro terminal,
com o tello_detector.py ligado em paralelo.

Uso:
    python cli_rota_teste.py                      # rota square, backend local
    python cli_rota_teste.py road                 # rota road
    python cli_rota_teste.py square https://backend-render-l4u0.onrender.com
"""
import sys
import time
import httpx

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROUTE = sys.argv[1] if len(sys.argv) > 1 else "square"
BASE  = (sys.argv[2] if len(sys.argv) > 2 else "https://backend-render-l4u0.onrender.com").rstrip("/")


def estado_atual(c):
    try:
        return c.get(f"/rotas/{ROUTE}/estado").json().get("estado")
    except Exception:
        return "?"


def main():
    print(f"\n=== Teste de rota '{ROUTE}'  ->  {BASE} ===\n")

    with httpx.Client(base_url=BASE, timeout=15) as c:
        # checa backend
        try:
            if c.get("/health").status_code != 200:
                print("[X] /health não respondeu 200. Backend no ar?")
                return
        except Exception as e:
            print(f"[X] Backend inacessível: {e}")
            return

        # 1. PREPARAR (papel do frontend)
        print("[1] Enviando PREPARAR...")
        r = c.post("/rotas/preparar", json={"route_id": ROUTE})
        if r.status_code not in (200, 201):
            print(f"[X] preparar falhou: {r.status_code} {r.text[:120]}")
            return
        print(f"    estado = {r.json().get('estado')}")
        print("    (o gateway vai puxar o comando e programar a rota)")

        # 2. AGUARDAR o gateway deixar a rota PRONTA
        print("\n[2] Aguardando o gateway preparar a rota...")
        for tentativa in range(20):   # ~20s
            time.sleep(1)
            est = estado_atual(c)
            print(f"    estado = {est}")
            if est == "pronta":
                break
        else:
            print("[X] A rota não ficou pronta. O tello_detector está rodando?")
            print("    (ele é quem responde os comandos da rota)")
            return

        # mostra os comandos que o gateway programou
        dados = c.get(f"/rotas/{ROUTE}/estado").json()
        print(f"\n    Comandos da rota ({dados.get('total_duration_s')}s no total):")
        for cmd in (dados.get("commands") or []):
            print(f"      - {cmd['action']:9} vel {cmd['velocity_pct']}%  {cmd['duration_s']}s")

        # 3. Confirmação humana antes de mover o drone
        print()
        resp = input(f"[3] Iniciar a rota '{ROUTE}' no drone? (s/n): ").strip().lower()
        if resp != "s":
            print("    Cancelado. (a rota fica pronta, não inicia)")
            return

        # 4. INICIAR (papel do frontend)
        print("\n[4] Enviando INICIAR...")
        r = c.post(f"/rotas/{ROUTE}/iniciar", json={"route_id": ROUTE, "confirmed": True})
        if r.status_code != 200:
            print(f"[X] iniciar falhou: {r.status_code} {r.text[:120]}")
            return
        print(f"    estado = {r.json().get('estado')}")
        print("    (o gateway vai puxar e o drone começa a se mover)")

        # 5. Acompanhar até concluir
        print("\n[5] Acompanhando execução...")
        for tentativa in range(40):   # ~40s
            time.sleep(1)
            est = estado_atual(c)
            print(f"    estado = {est}")
            if est in ("concluida", "erro"):
                break

        final = c.get(f"/rotas/{ROUTE}/estado").json()
        print(f"\n=== Fim: estado = {final.get('estado')} ===")
        if final.get("resultado"):
            res = final["resultado"]
            print(f"    bateria: {res.get('battery_before')}% -> {res.get('battery_after')}%")
            print(f"    duração: {res.get('total_duration_s')}s")
            if res.get("errors"):
                print(f"    erros: {res['errors']}")
        print()


if __name__ == "__main__":
    main()