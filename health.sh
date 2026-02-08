
#!/data/data/com.termux/files/usr/bin/bash

if ! ps aux | grep -q "[p]ython main.py"; then
  echo "[CRITICAL] Curudroid NÃO está rodando"
  exit 2
fi

if [ ! -f data/metrics.txt ]; then
  echo "[WARN] Métricas não encontradas"
  exit 1
fi

last=$(grep last_heartbeat data/metrics.txt | cut -d= -f2)
echo "[OK] Curudroid ativo"
echo "Último heartbeat: $last"
exit 0
