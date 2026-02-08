
#!/data/data/com.termux/files/usr/bin/bash

echo "=== Curudroid :: Status Completo ==="
echo

echo "[PROCESS]"
if ps aux | grep -q "[p]ython main.py"; then
  echo "Rodando"
else
  echo "Parado"
fi

echo
echo "[STATE]"
if [ -f data/last_state.txt ]; then
  cat data/last_state.txt
else
  echo "Estado desconhecido"
fi

echo
echo "[METRICS]"
if [ -f data/metrics.txt ]; then
  cat data/metrics.txt
else
  echo "Sem métricas"
fi
