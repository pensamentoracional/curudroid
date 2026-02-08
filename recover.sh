
#!/data/data/com.termux/files/usr/bin/bash

echo "[INFO] Recuperação manual do Curudroid"

# Se já estiver rodando, não faz nada
if ps aux | grep -q "[p]ython main.py"; then
  echo "[INFO] Curudroid já está em execução. Nada a fazer."
  exit 0
fi

# Diagnóstico rápido
./diagnose.sh

echo
read -p "Deseja iniciar o Curudroid agora? (y/N) " resp
if [[ "$resp" =~ ^[Yy]$ ]]; then
  ./start.sh
else
  echo "[INFO] Recuperação abortada pelo operador."
fi
