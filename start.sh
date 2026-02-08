#!/data/data/com.termux/files/usr/bin/bash

set -u

echo "[INFO] Iniciando Curudroid..."
# Modelo A: preflight padrão fica no main.py; --no-preflight continua funcional.
python main.py "$@"
echo "[INFO] Curudroid encerrado."
