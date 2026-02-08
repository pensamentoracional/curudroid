
import json
from pathlib import Path
from jsonschema import validate, ValidationError

INTENTS = Path("ai/intents")
APPROVED = Path("ai/approved")
REJECTED = Path("ai/rejected")

SCHEMA = json.loads(Path("ai/intent_schema.json").read_text(encoding="utf-8"))

def main():
    for intent_file in INTENTS.glob("*.json"):
        data = json.loads(intent_file.read_text(encoding="utf-8"))

        try:
            validate(instance=data, schema=SCHEMA)
            target = APPROVED / intent_file.name
            print(f"✔ Válida: {intent_file.name}")
        except ValidationError as e:
            target = REJECTED / intent_file.name
            print(f"✖ Inválida: {intent_file.name} → {e.message}")

        intent_file.rename(target)

if __name__ == "__main__":
    main()
