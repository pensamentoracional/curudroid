import json
import os
from datetime import datetime
from pathlib import Path

DECISION_LOG_PATH = os.path.join("logs", "decisions.log")
METRICS_FILE = Path("data/autonomy_metrics.json")
DECISIONS_FILE = Path("logs/decisions.log")


def log_decision(event: dict):
    os.makedirs("logs", exist_ok=True)

    event_record = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        **event
    }

    with open(DECISION_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(event_record) + "\n")

def load_metrics() -> dict:
    if not METRICS_FILE.exists():
        return {}

    with open(METRICS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_metrics(metrics: dict) -> None:
    os.makedirs("data", exist_ok=True)
    with open(METRICS_FILE, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)


def increment_metric(name: str, amount: int = 1) -> None:
    try:
        metrics = load_metrics()
    except Exception:
        # Fail-safe: se metrics estiver corrompido, reinicia
        metrics = {}

    current = metrics.get(name, 0)

    if not isinstance(current, int):
        current = 0

    metrics[name] = current + amount
    save_metrics(metrics)


def load_last_decisions(limit: int = 5) -> list:
    if not DECISIONS_FILE.exists():
        return []

    with open(DECISIONS_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    last_lines = lines[-limit:]
    return [json.loads(line) for line in last_lines]
