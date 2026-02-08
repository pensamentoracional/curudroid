from datetime import datetime
import argparse
import os
import signal
import sys
import time

from ai.config import config_summary, load_config, validate_config
from ai.preflight import run_preflight

running = True

# Configuração central
CONFIG = load_config()
LOG_DIR = CONFIG.log_dir
DATA_DIR = CONFIG.data_dir

LOG_FILE = os.path.join(LOG_DIR, "curudroid.log")
STATE_FILE = os.path.join(DATA_DIR, "last_state.txt")
METRICS_FILE = os.path.join(DATA_DIR, "metrics.txt")

os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)


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
    del frame
    global running
    log(f"INFO Sinal recebido ({signum}). Encerrando com segurança.")
    running = False


def run_startup_preflight() -> bool:
    """Preflight com logs previsíveis para startup (sem warning barulhento)."""
    report = run_preflight(CONFIG)

    for info in report.infos:
        log(f"INFO {info}")

    for warning in report.warnings:
        # Integrações opcionais ausentes não devem poluir com WARN.
        if warning.startswith("Telegram:") or warning.startswith("IA:"):
            log(f"INFO {warning}")
        else:
            log(f"WARN {warning}")

    for error in report.errors:
        log(f"ERROR {error}")

    if report.ok:
        log("INFO Preflight: OK")
        return True

    log("ERROR Preflight: FALHOU")
    return False


# ---------- Main ----------
def main(skip_preflight: bool = False):
    if not skip_preflight and not run_startup_preflight():
        return 1

    if skip_preflight:
        errors, warnings = validate_config(CONFIG)
        log(f"INFO {config_summary(CONFIG)}")
        for warning in warnings:
            if warning.startswith("Telegram:") or warning.startswith("IA:"):
                log(f"INFO {warning}")
        if errors:
            for err in errors:
                log(f"ERROR Configuração inválida: {err}")
            return 1

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
    return 0


# ---------- Entrypoint ----------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Curudroid")
    parser.add_argument(
        "--no-preflight",
        action="store_true",
        help="Pula checagens de preflight no startup",
    )
    args = parser.parse_args()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    raise SystemExit(main(skip_preflight=args.no_preflight))
