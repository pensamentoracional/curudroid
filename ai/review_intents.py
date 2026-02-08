
import json
import os
import shutil

INTENTS_DIR = "ai/intents"
APPROVED_DIR = "ai/approved"
REJECTED_DIR = "ai/rejected"

os.makedirs(APPROVED_DIR, exist_ok=True)
os.makedirs(REJECTED_DIR, exist_ok=True)

def review():
    files = sorted(f for f in os.listdir(INTENTS_DIR) if f.endswith(".json"))

    if not files:
        print("Nenhuma intenção pendente.")
        return

    for fname in files:
        path = os.path.join(INTENTS_DIR, fname)
        with open(path, "r", encoding="utf-8") as f:
            intent = json.load(f)

        print("\n--- INTENÇÃO DETECTADA ---")
        for k, v in intent.items():
            print(f"{k}: {v}")

        choice = input("\nAprovar esta intenção? [a]provar / [r]ejeitar / [s]kip: ").lower().strip()

        if choice == "a":
            shutil.move(path, os.path.join(APPROVED_DIR, fname))
            print("✔ Intenção APROVADA.")
        elif choice == "r":
            shutil.move(path, os.path.join(REJECTED_DIR, fname))
            print("✖ Intenção REJEITADA.")
        else:
            print("⏭ Pulada.")

if __name__ == "__main__":
    review()
