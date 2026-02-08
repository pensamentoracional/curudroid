from datetime import datetime
import argparse
import os
import signal
import sys
import time

from ai.config import AppConfig, config_summary, load_config, validate_config
from ai.preflight import run_preflight

running = True


class RuntimePaths:
    def __init__(self, config: AppConfig):
        self.log_dir = config.log_dir
        self.data_dir = config.data_dir
        self.log_file = os.path.join(self.log_dir, "curudroid.log")
        self.state_file = os.path.join(self.data_dir, "last_state.txt")
        self.metrics_file = os.path.join(self.data_dir, "metrics.txt")


RUNTIME_PATHS: RuntimePaths | None = None


# ---------- Logging ----------
def log(msg: str):
    timestamp = datetime.now().isoformat(timespec="seconds")
    line = f"[{timestamp}] {msg}"
    print(line)

    if RUNTIME_PATHS is None:
        return

    try:
        with open(RUNTIME_PATHS.log_file, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception as e:
        print(f"[WARN] Falha ao gravar log: {e}")


def setup_runtime_paths(config: AppConfig) -> bool:
    """Cria diretórios somente após preflight para evitar side-effects no import-time."""
    global RUNTIME_PATHS

    try:
        os.makedirs(config.log_dir, exist_ok=True)
        os.makedirs(config.data_dir, exist_ok=True)
    except Exception as exc:
        log(f"ERROR Falha ao preparar diretórios de runtime: {exc}")
        return False

    RUNTIME_PATHS = RuntimePaths(config)
    return True


# ---------- Estado ----------
def set_state(state: str):
    if RUNTIME_PATHS is None:
        return
    try:
        with open(RUNTIME_PATHS.state_file, "w", encoding="utf-8") as f:
            f.write(state)
    except Exception as e:
        log(f"WARN Falha ao gravar estado: {e}")


# ---------- Métricas ----------
def init_metrics():
    if RUNTIME_PATHS is None:
        return
    try:
        with open(RUNTIME_PATHS.metrics_file, "w", encoding="utf-8") as f:
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


def run_startup_preflight(config: AppConfig) -> bool:
    """Preflight com logs previsíveis para startup (sem warning barulhento)."""
    report = run_preflight(config)

    for info in report.infos:
        log(f"INFO {info}")

    for warning in report.warnings:
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
    config = load_config()

    if not skip_preflight and not run_startup_preflight(config):
        return 1

    if skip_preflight:
        errors, warnings = validate_config(config)
        log(f"INFO {config_summary(config)}")
        for warning in warnings:
            if warning.startswith("Telegram:") or warning.startswith("IA:"):
                log(f"INFO {warning}")
        if errors:
            for err in errors:
                log(f"ERROR Configuração inválida: {err}")
            return 1

    if not setup_runtime_paths(config):
        return 1

    set_state("STARTING")
    init_metrics()

    log("INFO Curudroid iniciado (modo residente)")
    log(f"INFO Python: {sys.version.split()[0]}")
    log("INFO Autonomia: DESATIVADA")

    set_state("RUNNING")

    start_time = time.time()
    heartbeat_count = 0
    runtime_paths = RUNTIME_PATHS
    if runtime_paths is None:
        log("ERROR Runtime não inicializado")
        return 1

    while running:
        heartbeat_count += 1
        uptime = int(time.time() - start_time)
        now = datetime.now().isoformat(timespec="seconds")

        try:
            with open(runtime_paths.metrics_file, "w", encoding="utf-8") as f:
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
