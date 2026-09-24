from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class AgentConfig(BaseModel):
    id: str = Field(default_factory=lambda: "agent_" + datetime.now().strftime("%Y%m%d-%H%M%S"))
    name: str
    role: str
    system_prompt: str
    allowed_tools: List[str] = Field(default_factory=list)
    is_active: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)

class AgentMessage(BaseModel):
    sender_id: str
    target_id: str
    action: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class AgentRegistry:
    def __init__(self) -> None:
        self._agents: Dict[str, AgentConfig] = {}
        self.register(AgentConfig(
            id="core_orchestrator",
            name="Core Orchestrator",
            role="Orchestrator",
            system_prompt="You orchestrate multi-agent actions and system decisions."
        ))
        self.register(AgentConfig(
            id="accounting_bridge",
            name="Accounting Bridge",
            role="Accounting Integration",
            system_prompt="You handle fiscal sync and accounting integration."
        ))

    def register(self, config: AgentConfig) -> AgentConfig:
        self._agents[config.id] = config
        return config

    def get(self, agent_id: str) -> Optional[AgentConfig]:
        return self._agents.get(agent_id)

    def list_all(self) -> List[AgentConfig]:
        return list(self._agents.values())

    def remove(self, agent_id: str) -> bool:
        return self._agents.pop(agent_id, None) is not None

agent_registry = AgentRegistry()
