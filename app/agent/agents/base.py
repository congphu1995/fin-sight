"""AgentSpec + process-global registry.

An `AgentSpec` is **data, not behavior** — it tells the runtime which tools
to expose, which system prompt to use, which limits to enforce, and which
model knobs to flip. The loop itself is shared across every agent.

To add a new agent:
1. `mkdir app/agent/agents/<key>/`
2. Write `prompt.md` (the system instruction).
3. Write `spec.py` that builds an `AgentSpec` and calls `register_agent(...)`.
4. Add `from app.agent.agents.<key> import spec as _<key>_spec  # noqa: F401`
   to `app/agent/agents/__init__.py` so the registration runs at import time.
"""

from dataclasses import dataclass, field

from app.agent.runtime.loop import (
    DEFAULT_MAX_STEPS,
    DEFAULT_PER_TOOL_TIMEOUT_S,
    DEFAULT_PER_TURN_TIMEOUT_S,
)


@dataclass(frozen=True)
class AgentSpec:
    """Configuration for a single agent. The runtime reads this to construct
    an `AgentLoop` for each turn — same loop, different parameters."""

    key: str
    """URL slug. Also stored on `Conversation.agent_key`."""

    description: str
    """Human-readable label, surfaced via the discovery endpoint."""

    system_prompt: str
    """The full system instruction. Loaded from the agent's `prompt.md`."""

    tool_names: tuple[str, ...] = field(default_factory=tuple)
    """Allowlist of tool names from `app.agent.tools.TOOL_REGISTRY`. An empty
    tuple means the agent runs without tools (text-only)."""

    max_steps: int = DEFAULT_MAX_STEPS
    per_tool_timeout_s: float = DEFAULT_PER_TOOL_TIMEOUT_S
    per_turn_timeout_s: float = DEFAULT_PER_TURN_TIMEOUT_S
    enable_google_search: bool = False


AGENT_REGISTRY: dict[str, AgentSpec] = {}


def register_agent(spec: AgentSpec) -> AgentSpec:
    if spec.key in AGENT_REGISTRY:
        raise RuntimeError(f"duplicate agent key {spec.key!r}")
    AGENT_REGISTRY[spec.key] = spec
    return spec
