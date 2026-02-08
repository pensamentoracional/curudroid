
#!/data/data/com.termux/files/usr/bin/bash

echo "=== Curudroid :: Diagnóstico ==="
echo

if [ -f data/last_state.txt ]; then
  echo "[STATE] Último estado:"
  cat data/last_state.txt
else
  echo "[STATE] Nenhum estado registrado"
fi

echo
echo "[PROCESS]"
if ps aux | grep -q "[p]ython main.py"; then
  echo "Rodando"
  ps aux | grep "[p]ython main.py"
else
  echo "Parado"
fi

echo
echo "[LOGS - últimos 10]"
tail -n 10 logs/curudroid.log 2>/dev/null || echo "Sem logs"
