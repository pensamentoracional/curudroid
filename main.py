
from datetime import datetime
import os
import sys
import time
import signal

# Diretórios e arquivos
LOG_DIR = "logs"
DATA_DIR = "data"

LOG_FILE = os.path.join(LOG_DIR, "curudroid.log")
STATE_FILE = os.path.join(DATA_DIR, "last_state.txt")
METRICS_FILE = os.path.join(DATA_DIR, "metrics.txt")

os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

running = True

# ---------- Logging ----------
def log(msg: str):
    timestamp = datetime.now().isoformat(timespec="seconds")
    line = f"[{timestamp}] {msg}"
    print(line)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception as e:
        print(f"[WARN] Falha ao gravar log: {e}")

# ---------- Estado ----------
def set_state(state: str):
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            f.write(state)
    except Exception as e:
        log(f"WARN Falha ao gravar estado: {e}")

# ---------- Métricas ----------
def init_metrics():
    try:
        with open(METRICS_FILE, "w", encoding="utf-8") as f:
            f.write("uptime_seconds=0\n")
            f.write("heartbeats=0\n")
            f.write("last_heartbeat=never\n")
    except Exception as e:
        log(f"WARN Falha ao inicializar métricas: {e}")

# ---------- Sinais ----------
def handle_signal(signum, frame):
    global running
    log(f"INFO Sinal recebido ({signum}). Encerrando com segurança.")
    running = False

# ---------- Main ----------
def main():
    set_state("STARTING")
    init_metrics()

    log("INFO Curudroid iniciado (modo residente)")
    log(f"INFO Python: {sys.version.split()[0]}")
    log("INFO Autonomia: DESATIVADA")

    set_state("RUNNING")

    start_time = time.time()
    heartbeat_count = 0

    while running:
        heartbeat_count += 1
        uptime = int(time.time() - start_time)
        now = datetime.now().isoformat(timespec="seconds")

        try:
            with open(METRICS_FILE, "w", encoding="utf-8") as f:
                f.write(f"uptime_seconds={uptime}\n")
                f.write(f"heartbeats={heartbeat_count}\n")
                f.write(f"last_heartbeat={now}\n")
        except Exception as e:
            log(f"WARN Falha ao atualizar métricas: {e}")

        log("INFO Heartbeat — sistema ativo")
        time.sleep(10)

    set_state("STOPPING")
    log("INFO Curudroid finalizado de forma graciosa")
    set_state("STOPPED")

# ---------- Entrypoint ----------
if __name__ == "__main__":
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    main()
