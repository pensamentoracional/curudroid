from datetime import datetime
import argparse
import os
import signal
import sys
import time

from ai.config import AppConfig, config_summary, load_config, validate_config
from ai.preflight import run_preflight
from core.executor import execute_plan, PlanExecutionError
from core.ledger_verify import verify_ledger, LedgerIntegrityError, recover_ledger
from core.policy_lock import (
    initialize_policy_lock,
    verify_policy_locked,
    PolicyLockError,
)


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
    global RUNTIME_PATHS

    try:
        os.makedirs(config.log_dir, exist_ok=True)
        os.makedirs(config.data_dir, exist_ok=True)
    except Exception as exc:
        log(f"ERROR Falha ao preparar diretorios de runtime: {exc}")
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


# ---------- Metricas ----------
def init_metrics():
    if RUNTIME_PATHS is None:
        return
    try:
        with open(RUNTIME_PATHS.metrics_file, "w", encoding="utf-8") as f:
            f.write("uptime_seconds=0\n")
            f.write("heartbeats=0\n")
            f.write("last_heartbeat=never\n")
    except Exception as e:
        log(f"WARN Falha ao inicializar metricas: {e}")


# ---------- Sinais ----------
def handle_signal(signum, frame):
    del frame
    global running
    log(f"INFO Sinal recebido ({signum}). Encerrando com segurana.")
    running = False


def run_startup_preflight(config: AppConfig) -> bool:
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
def main(
    skip_preflight: bool = False,
    execute_plan_path: str | None = None,
    apply: bool = False,
    verify_ledger_flag: bool = False,
    ledger_recover: bool = False,
    force_recover: bool = False,
    policy_maintenance: bool = False,
    policy_lock_init: bool = False,
):

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
                log(f"ERROR Configuraao invalida: {err}")
            return 1

    if not setup_runtime_paths(config):
        return 1

    # ---------- Policy Lock Initialization ----------
    if policy_lock_init:
        if not policy_maintenance:
            log("ERROR Policy lock init requer --policy-maintenance")
            return 1

        initialize_policy_lock()
        log("INFO Policy lock inicializado com sucesso")
        return 0

    # ---------- Policy Lock Verification (Modo Normal) ----------
    if not policy_maintenance:
        try:
            verify_policy_locked()
        except PolicyLockError as e:
            log(f"CRITICAL Policy violada  {e}")
            set_state("POLICY_VIOLATION")
            return 1

    # ---------- Verificaao do Ledger ----------
    if verify_ledger_flag:
        log("INFO Modo Verificaao de Ledger ativado")
        try:
            result = verify_ledger()
            log(f"INFO Ledger OK  entries={result['entries']}")
            return 0
        except LedgerIntegrityError as e:
            log(f"ERROR Ledger FALHOU  {e}")
            return 1
    # ---------- Ledger Recovery ----------
    if ledger_recover:
        if not force_recover:
            log("ERROR --ledger-recover requer --force-recover")
            return 1

        log("WARNING Iniciando recuperaao formal do ledger")

        result = recover_ledger()

        log(f"INFO {result['message']}")
        log(f"INFO Backup criado em {result.get('backup_created')}")
        set_state("LEDGER_RECOVERED")
        return 0

    # ---------- Executor Assistido ----------
    if execute_plan_path:
        log("INFO Modo Executor Assistido ativado")
        log(f"INFO Plano solicitado: {execute_plan_path}")
        log(f"INFO Modo: {'APPLY' if apply else 'DRY-RUN'}")

        # ---------- Fail-Closed: Verificar Ledger antes de Apply ----------
        if apply:
            try:
                verify_ledger()
            except LedgerIntegrityError as e:
                log(f"CRITICAL Ledger comprometido  {e}")
                set_state("LEDGER_TAMPERED")
                return 1

        try:
            report = execute_plan(execute_plan_path, apply=apply)
            log(f"INFO Execuao concluida  plano {report['plan_id']}")
            return 0
        except PlanExecutionError as e:
            log(f"ERROR Execuao falhou: {e}")
            return 1

    # ---------- Modo Residente ----------
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
            with open(RUNTIME_PATHS.metrics_file, "w", encoding="utf-8") as f:
                f.write(f"uptime_seconds={uptime}\n")
                f.write(f"heartbeats={heartbeat_count}\n")
                f.write(f"last_heartbeat={now}\n")
        except Exception as e:
            log(f"WARN Falha ao atualizar metricas: {e}")

        log("INFO Heartbeat  sistema ativo")
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

    parser.add_argument(
        "--execute",
        type=str,
        help="Executa plano aprovado (Executor Assistido)",
    )

    parser.add_argument(
        "--apply",
        action="store_true",
        help="Aplica execuao real (sem dry-run)",
    )

    parser.add_argument(
        "--verify-ledger",
        action="store_true",
        help="Verifica integridade do historico encadeado (ledger)",
    )

    parser.add_argument(
        "--ledger-recover",
        action="store_true",
        help="Recupera ledger comprometido (modo seguro)",
    )

    parser.add_argument(
        "--force-recover",
        action="store_true",
        help="Confirma recuperaao forada do ledger",
    )

    parser.add_argument(
        "--policy-maintenance",
        action="store_true",
        help="Ativa modo manutenao para atualizar policy",
    )

    parser.add_argument(
        "--policy-lock-init",
        action="store_true",
        help="Inicializa ou reinicializa o lock da policy",
    )


    args = parser.parse_args()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    raise SystemExit(
        main(
            skip_preflight=args.no_preflight,
            execute_plan_path=args.execute,
            apply=args.apply,
            verify_ledger_flag=args.verify_ledger,
            ledger_recover=args.ledger_recover,
            force_recover=args.force_recover,
            policy_maintenance=args.policy_maintenance,
            policy_lock_init=args.policy_lock_init,
        )
    )
