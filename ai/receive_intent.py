
import json
import sys
from datetime import datetime
from pathlib import Path

INTENTS_DIR = Path("ai/intents")

def main():
    if len(sys.argv) != 2:
        print("Uso: python receive_intent.py '<json>'")
        sys.exit(1)

    try:
        data = json.loads(sys.argv[1])
    except json.JSONDecodeError as e:
        print(f"JSON inválido: {e}")
        sys.exit(1)

    filename = datetime.now().strftime("%Y%m%dT%H%M%S") + ".json"
    path = INTENTS_DIR / filename

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Intenção registrada em {path}")

if __name__ == "__main__":
    main()
