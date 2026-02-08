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

echo
echo "[TESTES RÁPIDOS]"
if python -m unittest -q; then
  echo "[OK] Testes rápidos passaram"
else
  echo "[FAIL] Testes rápidos falharam"
  exit 1
fi

echo
echo "[UNICODE BIDI CHECK]"
if rg -nP "[\x{202A}-\x{202E}\x{2066}-\x{2069}]" . >/dev/null; then
  echo "[FAIL] Caracteres bidi invisíveis detectados"
  rg -nP "[\x{202A}-\x{202E}\x{2066}-\x{2069}]" .
  exit 1
else
  echo "[OK] Sem caracteres bidi invisíveis"
fi
