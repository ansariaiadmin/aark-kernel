"""Process-wide agent singletons.

``app.main`` and ``app.api.v1.ai`` each used to build their own ``AgentBrain()``.
Because ``AgentBrain.__init__`` registers the default model into the *shared*
``model_router`` and allocates a private ``ConversationMemory``, the process
ended up with two brains and two disjoint memories: the ``/api/v1/agent/...``
routes and the ``/api/v1/ai/agent/...`` routes did not share conversation
state, and ``/ai/agent/memory/clear`` silently cleared the wrong one.

Import ``brain`` from here everywhere so there is exactly one.
"""

from __future__ import annotations

from app.agent.brain import AgentBrain
from app.core.config import get_settings

_settings = get_settings()

#: The single AgentBrain instance for this process.
brain = AgentBrain(
    model_name=_settings.DEFAULT_MODEL,
    base_url=_settings.LOCAL_OLLAMA_HOST,
)

__all__ = ["brain"]
