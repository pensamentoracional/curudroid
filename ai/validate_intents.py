import json
from datetime import datetime
from pathlib import Path

from ai.plugins.registry import validate_plugins

INTENTS = Path("ai/intents")
APPROVED = Path("ai/approved")
REJECTED = Path("ai/rejected")
SCHEMA_PATH = Path("ai/intent_schema.json")


def load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def known_plugin_ids() -> set[str]:
    report = validate_plugins()
    return {result.plugin_id for result in report.results}


def validate_intent_payload(payload: dict, schema: dict, plugins: set[str]) -> tuple[bool, str]:
    required = schema.get("required", [])
    for field in required:
        if field not in payload:
            return False, f"campo obrigatório ausente: {field}"

    intent_name = payload.get("intent")
    if intent_name not in schema["properties"]["intent"]["enum"]:
        return False, "intent fora da whitelist"

    if not isinstance(payload.get("reason"), str) or len(payload["reason"]) < 5:
        return False, "reason inválido"

    confidence = payload.get("confidence")
    if not isinstance(confidence, (int, float)) or not (0.0 <= confidence <= 1.0):
        return False, "confidence inválido"

    created_at = payload.get("created_at")
    if not isinstance(created_at, str):
        return False, "created_at inválido"
    try:
        datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    except ValueError:
        return False, "created_at deve estar em ISO-8601"

    if intent_name not in plugins:
        return False, f"intent sem plugin mapeado: {intent_name}"

    return True, "ok"


def main():
    APPROVED.mkdir(parents=True, exist_ok=True)
    REJECTED.mkdir(parents=True, exist_ok=True)
    schema = load_schema()
    plugins = known_plugin_ids()

    for intent_file in INTENTS.glob("*.json"):
        data = json.loads(intent_file.read_text(encoding="utf-8"))
        is_valid, reason = validate_intent_payload(data, schema, plugins)
        if is_valid:
            target = APPROVED / intent_file.name
            print(f"✔ Válida: {intent_file.name}")
        else:
            target = REJECTED / intent_file.name
            print(f"✖ Inválida: {intent_file.name} → {reason}")

        intent_file.rename(target)


if __name__ == "__main__":
    main()
