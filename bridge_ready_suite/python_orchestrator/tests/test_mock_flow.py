from llm_client import MockAgentClient
from orchestrator import Orchestrator


def test_mock_approves_simple_task() -> None:
    orch = Orchestrator(MockAgentClient(), 3, ("app", "tests"))
    state = orch.run("Improve logging in the sample repo and add tests", mode="mock")
    assert state.final_status == "APPROVED"
