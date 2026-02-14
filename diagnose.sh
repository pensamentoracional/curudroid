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
echo "[PLAN JSON SCHEMA CHECK]"
if python - <<'PY'
import json
from pathlib import Path

required_top = {"plan_id", "version", "intent_path", "risk_estimate", "commands", "assumptions"}
plans_dir = Path("ai/plans")
files = sorted(plans_dir.glob("*.json"))

if not files:
    print("[OK] Nenhum plan JSON para validar")
    raise SystemExit(0)

for path in files:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"[FAIL] {path}: conteúdo não é objeto JSON")

    missing = required_top - set(data.keys())
    if missing:
        raise SystemExit(f"[FAIL] {path}: faltam campos {sorted(missing)}")

    if not isinstance(data["plan_id"], str):
        raise SystemExit(f"[FAIL] {path}: plan_id deve ser str")
    if data["version"] != 1:
        raise SystemExit(f"[FAIL] {path}: version deve ser 1")
    if not isinstance(data["intent_path"], str):
        raise SystemExit(f"[FAIL] {path}: intent_path deve ser str")
    if not isinstance(data["risk_estimate"], (int, float)):
        raise SystemExit(f"[FAIL] {path}: risk_estimate deve ser float")
    if not isinstance(data["assumptions"], list) or not all(isinstance(i, str) for i in data["assumptions"]):
        raise SystemExit(f"[FAIL] {path}: assumptions deve ser list[str]")

    commands = data["commands"]
    if not isinstance(commands, list):
        raise SystemExit(f"[FAIL] {path}: commands deve ser list")
    for idx, cmd in enumerate(commands):
        if not isinstance(cmd, dict):
            raise SystemExit(f"[FAIL] {path}: commands[{idx}] deve ser dict")
        if set(cmd.keys()) != {"argv", "description"}:
            raise SystemExit(f"[FAIL] {path}: commands[{idx}] deve conter argv e description")
        if not isinstance(cmd["argv"], list) or not all(isinstance(a, str) for a in cmd["argv"]):
            raise SystemExit(f"[FAIL] {path}: commands[{idx}].argv deve ser list[str]")
        if not isinstance(cmd["description"], str):
            raise SystemExit(f"[FAIL] {path}: commands[{idx}].description deve ser str")

print(f"[OK] {len(files)} plan JSON válidos")
PY
then
  true
else
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
