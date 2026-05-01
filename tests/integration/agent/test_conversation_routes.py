"""Route-level tests for the agent conversation API.

Heavy DB-end-to-end tests are skipped (require docker compose). These tests
override `get_conversation_service` with a fake to verify routing,
serialization, agent_key path-param resolution, and error mapping.
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient

from app.agent.agents.base import AgentSpec
from app.agent.dependencies import get_conversation_service
from app.agent.models import Conversation, Message
from app.agent.service import ConversationNotFoundError
from app.core.exceptions import AgentLoopExceededError, LLMError
from app.main import app as fastapi_app

QA = "qa"


def _conv(id_: UUID | None = None, agent_key: str = QA) -> Conversation:
    now = datetime.now(UTC)
    return Conversation(
        id=id_ or uuid4(),
        agent_key=agent_key,
        title=None,
        created_at=now,
        updated_at=now,
    )


def _msg(conv_id: UUID, role: str, **kw: Any) -> Message:
    return Message(
        id=uuid4(),
        conversation_id=conv_id,
        role=role,
        step=kw.pop("step", 0),
        created_at=datetime.now(UTC),
        **kw,
    )


class FakeService:
    def __init__(self) -> None:
        self.created: list[Conversation] = []
        self.posted: list[tuple[str, UUID, str]] = []
        self.next_post_messages: list[Message] = []
        self.next_post_raises: Exception | None = None
        self.conversations: dict[UUID, Conversation] = {}
        self.messages_by_conv: dict[UUID, list[Message]] = {}

    async def create_conversation(self, agent_key: str) -> Conversation:
        c = _conv(agent_key=agent_key)
        self.created.append(c)
        self.conversations[c.id] = c
        self.messages_by_conv[c.id] = []
        return c

    async def get_conversation(self, agent_key: str, conv_id: UUID) -> Conversation:
        conv = self.conversations.get(conv_id)
        if conv is None or conv.agent_key != agent_key:
            raise ConversationNotFoundError(str(conv_id))
        return conv

    async def list_messages(self, agent_key: str, conv_id: UUID) -> list[Message]:
        await self.get_conversation(agent_key, conv_id)
        return self.messages_by_conv.get(conv_id, [])

    async def post_message(
        self, spec: AgentSpec, conv_id: UUID, user_text: str
    ) -> list[Message]:
        await self.get_conversation(spec.key, conv_id)
        if self.next_post_raises is not None:
            raise self.next_post_raises
        self.posted.append((spec.key, conv_id, user_text))
        return self.next_post_messages


@pytest.fixture
def fake_service() -> FakeService:
    return FakeService()


@pytest.fixture
def app_with_service(fake_service: FakeService):
    fastapi_app.dependency_overrides[get_conversation_service] = lambda: fake_service
    try:
        yield fastapi_app
    finally:
        fastapi_app.dependency_overrides.clear()


@pytest.fixture
async def svc_client(app_with_service):
    from httpx import ASGITransport

    async with AsyncClient(
        transport=ASGITransport(app=app_with_service),
        base_url="http://test",
    ) as ac:
        yield ac


async def test_list_agents_includes_qa(svc_client: AsyncClient) -> None:
    resp = await svc_client.get("/api/v1/agent/agents")
    assert resp.status_code == 200
    keys = {a["key"] for a in resp.json()["agents"]}
    assert "qa" in keys


async def test_create_conversation_returns_id_and_agent_key(
    svc_client: AsyncClient, fake_service: FakeService
) -> None:
    resp = await svc_client.post(f"/api/v1/agent/{QA}/conversations")
    assert resp.status_code == 201
    body = resp.json()
    assert UUID(body["id"]) == fake_service.created[0].id
    assert body["agent_key"] == QA


async def test_create_conversation_404_for_unknown_agent(svc_client: AsyncClient) -> None:
    resp = await svc_client.post("/api/v1/agent/nope/conversations")
    assert resp.status_code == 404


async def test_post_message_returns_persisted_messages(
    svc_client: AsyncClient, fake_service: FakeService
) -> None:
    conv = await fake_service.create_conversation(QA)
    fake_service.next_post_messages = [
        _msg(conv.id, "user", content="hi", step=0),
        _msg(conv.id, "assistant", content="hello", step=1),
    ]

    resp = await svc_client.post(
        f"/api/v1/agent/{QA}/conversations/{conv.id}/messages",
        json={"message": "hi"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert [m["role"] for m in body["messages"]] == ["user", "assistant"]
    assert body["messages"][1]["content"] == "hello"
    assert fake_service.posted == [(QA, conv.id, "hi")]


async def test_post_message_404_for_unknown_conversation(svc_client: AsyncClient) -> None:
    resp = await svc_client.post(
        f"/api/v1/agent/{QA}/conversations/{uuid4()}/messages",
        json={"message": "hi"},
    )
    assert resp.status_code == 404


async def test_post_message_502_on_llm_error(
    svc_client: AsyncClient, fake_service: FakeService
) -> None:
    conv = await fake_service.create_conversation(QA)
    fake_service.next_post_raises = LLMError("upstream down")

    resp = await svc_client.post(
        f"/api/v1/agent/{QA}/conversations/{conv.id}/messages",
        json={"message": "hi"},
    )
    assert resp.status_code == 502


async def test_post_message_504_on_loop_exceeded(
    svc_client: AsyncClient, fake_service: FakeService
) -> None:
    conv = await fake_service.create_conversation(QA)
    fake_service.next_post_raises = AgentLoopExceededError("too many steps")

    resp = await svc_client.post(
        f"/api/v1/agent/{QA}/conversations/{conv.id}/messages",
        json={"message": "hi"},
    )
    assert resp.status_code == 504


async def test_post_message_rejects_empty(svc_client: AsyncClient) -> None:
    resp = await svc_client.post(
        f"/api/v1/agent/{QA}/conversations/{uuid4()}/messages",
        json={"message": ""},
    )
    assert resp.status_code == 422


async def test_get_conversation_returns_history(
    svc_client: AsyncClient, fake_service: FakeService
) -> None:
    conv = await fake_service.create_conversation(QA)
    fake_service.messages_by_conv[conv.id] = [
        _msg(conv.id, "user", content="hi", step=0),
        _msg(conv.id, "assistant", content="hello", step=1),
    ]

    resp = await svc_client.get(f"/api/v1/agent/{QA}/conversations/{conv.id}")

    assert resp.status_code == 200
    body = resp.json()
    assert body["conversation"]["id"] == str(conv.id)
    assert body["conversation"]["agent_key"] == QA
    assert len(body["messages"]) == 2


async def test_get_conversation_404(svc_client: AsyncClient) -> None:
    resp = await svc_client.get(f"/api/v1/agent/{QA}/conversations/{uuid4()}")
    assert resp.status_code == 404


async def test_get_conversation_404_when_agent_key_mismatch(
    svc_client: AsyncClient, fake_service: FakeService
) -> None:
    conv = await fake_service.create_conversation(QA)
    # Conversation belongs to qa, but we ask for it via a (validly-registered)
    # different agent. We register a fake spec on the fly so the URL passes
    # the registry check.
    from app.agent.agents.base import AGENT_REGISTRY, AgentSpec

    other = AgentSpec(key="other", description="x", system_prompt="x")
    AGENT_REGISTRY[other.key] = other
    try:
        resp = await svc_client.get(
            f"/api/v1/agent/other/conversations/{conv.id}"
        )
        assert resp.status_code == 404
    finally:
        AGENT_REGISTRY.pop(other.key, None)


async def test_routes_registered_in_openapi(svc_client: AsyncClient) -> None:
    resp = await svc_client.get("/openapi.json")
    paths = resp.json()["paths"]
    assert "/api/v1/agent/agents" in paths
    assert "/api/v1/agent/{agent_key}/conversations" in paths
    assert "/api/v1/agent/{agent_key}/conversations/{conversation_id}" in paths
    assert "/api/v1/agent/{agent_key}/conversations/{conversation_id}/messages" in paths
    # Old single-turn /chat is gone.
    assert "/api/v1/chat" not in paths
    assert "/api/v1/conversations" not in paths
