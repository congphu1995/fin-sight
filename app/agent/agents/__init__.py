"""Agent registry — importing this package registers every agent via
`register_agent(...)` side-effects in each spec module."""

from app.agent.agents.base import AGENT_REGISTRY, AgentSpec, register_agent
from app.agent.agents.qa import spec as _qa_spec  # noqa: F401  — registers 'qa'

__all__ = ["AGENT_REGISTRY", "AgentSpec", "register_agent"]
