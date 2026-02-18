from __future__ import annotations

import json
from urllib import request


class OpenAIProvider:
    provider_name = "openai"

    def __init__(self, api_key: str, model: str, timeout_seconds: float = 5.0):
        self.api_key = api_key
        self.model_name = model
        self.timeout_seconds = timeout_seconds

    def recommend(self, plan: dict, context: dict) -> dict | None:
        if not self.api_key:
            return None

        payload = {
            "model": self.model_name,
            "input": [
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                "You are a consultative safety advisor. "
                                "Never suggest direct execution commands. "
                                "Respond only in JSON with keys: suggested_action, "
                                "risk_assessment, confidence, explanation."
                            ),
                        }
                    ],
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": json.dumps({"plan": plan, "context": context}),
                        }
                    ],
                },
            ],
        }

        req = request.Request(
            "https://api.openai.com/v1/responses",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        with request.urlopen(req, timeout=self.timeout_seconds) as response:
            body = json.loads(response.read().decode("utf-8"))

        for item in body.get("output", []):
            for content in item.get("content", []):
                text = content.get("text")
                if text:
                    data = json.loads(text)

                    #  Validaao explicita de tipo
                    if not isinstance(data, dict):
                        raise ValueError("AI response must be a JSON object")

                    return data

        return None
