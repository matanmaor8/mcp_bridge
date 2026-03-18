import json

from llm_client import OpenAIAgentClient


class DummyResponse:
    def __init__(self, payload):
        self.output_text = json.dumps(payload)


class DummyResponsesAPI:
    def __init__(self, payloads):
        self.payloads = payloads
        self.index = 0

    def create(self, **kwargs):
        payload = self.payloads[self.index]
        self.index += 1
        return DummyResponse(payload)


class DummyOpenAI:
    def __init__(self, payloads):
        self.responses = DummyResponsesAPI(payloads)


def test_openai_client_parsing(monkeypatch):
    payloads = [
        {
            "summary": "builder ok",
            "proposed_changes": ["x"],
            "checks_run": ["pytest -q"],
            "risks": [],
        },
        {
            "verdict": "APPROVE",
            "summary": "review ok",
            "issues": [],
            "next_actions": [],
        },
    ]

    def fake_init(self, api_key: str, model: str) -> None:
        self.client = DummyOpenAI(payloads)
        self.model = model

    monkeypatch.setattr(OpenAIAgentClient, "__init__", fake_init)
    client = OpenAIAgentClient("dummy", "gpt-5")
    builder = client.run_builder("task", "instruction")
    review = client.run_reviewer("task", builder, "TESTS_PASSED=True")
    assert builder.summary == "builder ok"
    assert review.verdict == "APPROVE"
