import sys

try:
    from djitellopy import Tello
    TELLO_AVAILABLE = True
except ImportError as e:
    TELLO_AVAILABLE = False
    TELLO_IMPORT_ERROR = str(e)
else:
    TELLO_IMPORT_ERROR = None

DISTANCIA = 50

COMANDOS_VALIDOS = ["frente", "tras", "esquerda", "direita", "subir", "descer"]

AJUDA = """
Comandos disponíveis:
  frente    — move para frente
  tras      — move para trás
  esquerda  — move para a esquerda
  direita   — move para a direita
  subir     — sobe
  descer    — desce
  fim       — executa a rota
  cancelar  — cancela e sai
  ajuda     — mostra esta mensagem
"""


def executar_comando(drone, comando: str, simulado: bool):
    print(f"  → Executando: {comando}...")
    if simulado:
        return

    if comando == "frente":
        drone.move_forward(DISTANCIA)
    elif comando == "tras":
        drone.move_back(DISTANCIA)
    elif comando == "esquerda":
        drone.move_left(DISTANCIA)
    elif comando == "direita":
        drone.move_right(DISTANCIA)
    elif comando == "subir":
        drone.move_up(DISTANCIA)
    elif comando == "descer":
        drone.move_down(DISTANCIA)


def confirmar_rota(rota: list) -> bool:
    print("\nRota definida:")
    for i, cmd in enumerate(rota, 1):
        print(f"  {i}. {cmd}")

    while True:
        resposta = input("\nExecutar a rota? (s/n): ").strip().lower()
        if resposta == "s":
            return True
        elif resposta == "n":
            return False
        print("Digite 's' para sim ou 'n' para não.")


def escolher_modo() -> bool:
    print("\nModo de execução:")
    print("  1. Simulado  — testa a rota sem conectar ao drone")
    print("  2. Real      — conecta ao Tello e executa de verdade")

    while True:
        escolha = input("\nEscolha (1 ou 2): ").strip()
        if escolha == "1":
            return True
        elif escolha == "2":
            if not TELLO_AVAILABLE:
                print(f"\nErro ao importar djitellopy: {TELLO_IMPORT_ERROR}")
                print("Voltando para modo simulado.\n")
                return True
            return False
        print("Digite 1 ou 2.")


def main():
    print("=" * 40)
    print("   Controle de Rota — DJI Tello")
    print("=" * 40)
    print(AJUDA)

    simulado = escolher_modo()

    if simulado:
        print("\n[MODO SIMULADO] Os comandos não serão enviados ao drone.\n")
    else:
        print("\n[MODO REAL] O drone executará os comandos.\n")

    rota = []
    print("Digite os comandos da rota. Digite 'fim' para executar.\n")

    while True:
        try:
            entrada = input("> ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print("\nCancelado.")
            sys.exit(0)

        if entrada == "":
            continue
        elif entrada == "ajuda":
            print(AJUDA)
        elif entrada == "cancelar":
            print("Rota cancelada.")
            sys.exit(0)
        elif entrada == "fim":
            if not rota:
                print("Nenhum comando adicionado ainda.")
                continue
            break
        elif entrada in COMANDOS_VALIDOS:
            rota.append(entrada)
            print(f"  + {entrada} adicionado ({len(rota)} comando(s) na rota)")
        else:
            print(f"  Comando '{entrada}' não reconhecido. Digite 'ajuda' para ver os comandos.")

    if not confirmar_rota(rota):
        print("Rota cancelada.")
        sys.exit(0)

    drone = None

    if not simulado:
        print("\nConectando ao Tello...")
        try:
            drone = Tello()
            drone.connect()
            print(f"Bateria: {drone.get_battery()}%")
            print("Decolando...")
            drone.takeoff()
        except Exception as e:
            print(f"Erro ao conectar: {e}")
            sys.exit(1)

    print("\nExecutando rota...\n")

    try:
        for comando in rota:
            executar_comando(drone, comando, simulado)

        if not simulado:
            print("\nPousando...")
            drone.land()

        print("\nRota concluída com sucesso!")

    except Exception as e:
        print(f"\nErro durante execução: {e}")
        if drone:
            print("Tentando pousar por segurança...")
            try:
                drone.land()
            except:
                pass
        sys.exit(1)

    finally:
        if drone:
            drone.end()


if __name__ == "__main__":
    main()