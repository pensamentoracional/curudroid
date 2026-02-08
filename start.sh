#!/data/data/com.termux/files/usr/bin/bash

set -u

echo "[INFO] Iniciando Curudroid..."

# Preflight explícito no start para falhar cedo com diagnóstico previsível.
python -m ai.preflight
PRECHECK_EXIT=$?
if [ "$PRECHECK_EXIT" -ne 0 ]; then
  echo "[ERROR] Preflight falhou (exit=$PRECHECK_EXIT). Abortando inicialização."
  exit "$PRECHECK_EXIT"
fi

# Evita preflight duplicado no entrypoint mantendo uma única execução do app.
python main.py --no-preflight "$@"
echo "[INFO] Curudroid encerrado."
