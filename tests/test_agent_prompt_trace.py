from __future__ import annotations

from contextlib import contextmanager

from app import agent as agent_module


class ManagedPrompt:
    version = 3

    def compile(self, **variables: str) -> str:
        return (
            f"Feature={variables['feature']}\n"
            f"Docs={variables['docs']}\n"
            f"Question={variables['message']}"
        )


class RecordingLangfuseClient:
    def __init__(self) -> None:
        self.prompt = ManagedPrompt()
        self.span_updates: list[dict] = []
        self.generation_updates: list[dict] = []
        self.observations: list[dict] = []

    def get_prompt(self, name: str, **kwargs):
        return self.prompt

    def update_current_span(self, **kwargs) -> None:
        self.span_updates.append(kwargs)

    def update_current_generation(self, **kwargs) -> None:
        self.generation_updates.append(kwargs)

    @contextmanager
    def start_as_current_observation(self, **kwargs):
        self.observations.append(kwargs)
        yield


def test_agent_records_prompt_version_with_v4_observation_api(monkeypatch) -> None:
    monkeypatch.setenv("LANGFUSE_PROMPT_NAME", "day13-chat")
    monkeypatch.setenv("LANGFUSE_PROMPT_LABEL", "production")
    client = RecordingLangfuseClient()
    monkeypatch.setattr(agent_module, "get_langfuse_client", lambda: client)
    monkeypatch.setattr(agent_module, "tracing_enabled", lambda: True)

    propagated: list[dict] = []

    @contextmanager
    def record_attributes(**kwargs):
        propagated.append(kwargs)
        yield

    monkeypatch.setattr(agent_module, "propagate_attributes", record_attributes)

    agent = agent_module.LabAgent()
    agent_module.LabAgent.run.__wrapped__(
        agent,
        user_id="student-01",
        feature="qa",
        session_id="session-01",
        message="Explain traces for student@vinuni.edu.vn",
        correlation_id="req-12345678",
    )

    span_update = next(
        update
        for update in client.span_updates
        if "prompt_name" in update.get("metadata", {})
    )
    assert span_update["metadata"] == {
        "doc_count": 1,
        "query_preview": "Explain traces for [REDACTED_EMAIL]",
        "prompt_name": "day13-chat",
        "prompt_label": "production",
        "prompt_version": "3",
        "prompt_source": "langfuse",
        "prompt_fetch_error": "",
    }
    assert span_update["version"] == "3"
    assert propagated[0]["metadata"]["correlation_id"] == "req-12345678"
    assert propagated[-1]["prompt"] is client.prompt
    assert [item["as_type"] for item in client.observations] == [
        "retriever",
        "generation",
    ]
    generation = client.observations[-1]
    assert generation["name"] == "generate-response"
    assert generation["model"] == "claude-sonnet-4-5"
    assert generation["prompt"] is client.prompt
    captured = str(client.span_updates + client.observations + client.generation_updates)
    assert "student@vinuni.edu.vn" not in captured
    assert "REDACTED_EMAIL" in captured
    assert client.observations[0]["name"] == "retrieve-context"
    assert client.generation_updates[-1]["usage_details"]["total"] > 0
    assert client.generation_updates[-1]["cost_details"]["total"] > 0
    assert client.generation_updates[-1]["output"]["answer"]
