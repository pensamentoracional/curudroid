import json
from pathlib import Path
from typing import List, Dict


INTENT_QUEUE_FILE = Path("data/intents_queue.json")


class IntentQueue:
    def __init__(self):
        INTENT_QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> List[Dict]:
        if not INTENT_QUEUE_FILE.exists():
            return []
        return json.loads(INTENT_QUEUE_FILE.read_text(encoding="utf-8"))

    def save(self, intents: List[Dict]):
        INTENT_QUEUE_FILE.write_text(
            json.dumps(intents, indent=2),
            encoding="utf-8"
        )

    def enqueue(self, intent: Dict):
        intents = self.load()

        # Garantir campos minimos
        intent.setdefault("id", f"intent_{len(intents)+1}")
        intent.setdefault("priority", 1)
        intent.setdefault("status", "pending")

        intents.append(intent)

        # Ordenar por prioridade (maior primeiro)
        intents.sort(key=lambda x: x.get("priority", 1), reverse=True)

        self.save(intents)


    def dequeue(self) -> Dict | None:
        intents = self.load()
        if not intents:
            return None

        for intent in intents:
            if intent.get("status") == "pending":
                intent["status"] = "processing"
                self.save(intents)
                return intent

        return None
