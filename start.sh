#!/data/data/com.termux/files/usr/bin/bash

set -u

echo "[INFO] Iniciando Curudroid..."

# Preflight primeiro para falhar cedo com diagnóstico previsível.
python -m ai.preflight
PRECHECK_EXIT=$?
if [ "$PRECHECK_EXIT" -ne 0 ]; then
  echo "[ERROR] Preflight falhou (exit=$PRECHECK_EXIT). Abortando inicialização."
  exit "$PRECHECK_EXIT"
fi

python main.py "$@"
echo "[INFO] Curudroid encerrado."
