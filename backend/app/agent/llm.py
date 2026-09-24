from typing import List, Dict, Any, Optional, AsyncGenerator
from pydantic import BaseModel, Field
from enum import Enum
import json
import httpx
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class ModelProvider(str, Enum):
    OLLAMA = "ollama"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GROQ = "groq"


class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class ModelConfig:
    name: str
    provider: ModelProvider
    base_url: str
    api_key: Optional[str] = None
    max_tokens: int = 4096
    temperature: float = 0.2
    supports_tools: bool = False
    supports_streaming: bool = True
    priority: int = 0  # Higher = preferred


class ChatMessage(BaseModel):
    role: MessageRole
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None


class ToolDefinition(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any]


class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    tools: Optional[List[ToolDefinition]] = None
    tool_choice: Optional[str] = "auto"
    temperature: float = 0.2
    max_tokens: int = 4096
    stream: bool = False
    format: Optional[str] = None


class ChatCompletionResponse(BaseModel):
    id: str
    model: str
    choices: List[Dict[str, Any]]
    usage: Dict[str, int]


class ModelRouter:
    def __init__(self):
        self.models: Dict[str, ModelConfig] = {}
        self.default_model: Optional[str] = None

    def register_model(self, config: ModelConfig) -> None:
        self.models[config.name] = config
        if self.default_model is None or config.priority > self.models[self.default_model].priority:
            self.default_model = config.name
        logger.info(f"Registered model: {config.name} ({config.provider.value})")

    def get_model(self, name: Optional[str] = None) -> ModelConfig:
        if name and name in self.models:
            return self.models[name]
        if self.default_model:
            return self.models[self.default_model]
        raise ValueError("No model available")

    def list_models(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": m.name,
                "provider": m.provider.value,
                "max_tokens": m.max_tokens,
                "supports_tools": m.supports_tools,
                "supports_streaming": m.supports_streaming,
            }
            for m in self.models.values()
        ]


class ConversationMemory:
    def __init__(self, max_messages: int = 50, max_tokens: int = 8000):
        self.messages: List[ChatMessage] = []
        self.max_messages = max_messages
        self.max_tokens = max_tokens
        self.summary: Optional[str] = None

    def add_message(self, message: ChatMessage) -> None:
        self.messages.append(message)
        self._trim()

    def add_messages(self, messages: List[ChatMessage]) -> None:
        self.messages.extend(messages)
        self._trim()

    def get_messages(self, include_summary: bool = True) -> List[ChatMessage]:
        result = []
        if include_summary and self.summary:
            result.append(ChatMessage(role=MessageRole.SYSTEM, content=f"Conversation summary: {self.summary}"))
        result.extend(self.messages)
        return result

    def clear(self) -> None:
        self.messages.clear()
        self.summary = None

    def _trim(self) -> None:
        while len(self.messages) > self.max_messages:
            self.messages.pop(0)

    def estimate_tokens(self) -> int:
        return sum(len(m.content) for m in self.messages) // 4

    async def generate_summary(self, llm_client) -> None:
        if len(self.messages) < 10:
            return
        summary_prompt = "Summarize the key decisions and context from this conversation in 3-4 sentences:"
        messages = [ChatMessage(role=MessageRole.USER, content=summary_prompt)]
        messages.extend(self.messages[-20:])
        try:
            response = await llm_client.chat(messages, temperature=0.1, max_tokens=200)
            self.summary = response.choices[0]["message"]["content"]
            self.messages = self.messages[-10:]
        except Exception as e:
            logger.warning(f"Failed to generate summary: {e}")


class LLMClient:
    def __init__(self, router: ModelRouter):
        self.router = router

    async def chat(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        tools: Optional[List[ToolDefinition]] = None,
        tool_choice: Optional[str] = "auto",
        temperature: float = 0.2,
        max_tokens: int = 4096,
        stream: bool = False,
        format: Optional[str] = None,
    ) -> ChatCompletionResponse:
        model_config = self.router.get_model(model)
        return await self._call_provider(model_config, messages, tools, tool_choice, temperature, max_tokens, stream, format)

    async def stream_chat(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        tools: Optional[List[ToolDefinition]] = None,
        tool_choice: Optional[str] = "auto",
        temperature: float = 0.2,
        max_tokens: int = 4096,
        format: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        model_config = self.router.get_model(model)
        async for chunk in self._stream_provider(model_config, messages, tools, tool_choice, temperature, max_tokens, format):
            yield chunk

    async def _call_provider(
        self,
        config: ModelConfig,
        messages: List[ChatMessage],
        tools: Optional[List[ToolDefinition]],
        tool_choice: Optional[str],
        temperature: float,
        max_tokens: int,
        stream: bool,
        format: Optional[str],
    ) -> ChatCompletionResponse:
        if config.provider == ModelProvider.OLLAMA:
            return await self._call_ollama(config, messages, tools, tool_choice, temperature, max_tokens, stream, format)
        elif config.provider == ModelProvider.OPENAI:
            return await self._call_openai(config, messages, tools, tool_choice, temperature, max_tokens, stream, format)
        else:
            raise ValueError(f"Provider {config.provider} not implemented")

    async def _stream_provider(
        self,
        config: ModelConfig,
        messages: List[ChatMessage],
        tools: Optional[List[ToolDefinition]],
        tool_choice: Optional[str],
        temperature: float,
        max_tokens: int,
        format: Optional[str],
    ) -> AsyncGenerator[str, None]:
        if config.provider == ModelProvider.OLLAMA:
            async for chunk in self._stream_ollama(config, messages, tools, tool_choice, temperature, max_tokens, format):
                yield chunk
        else:
            raise ValueError(f"Streaming not implemented for {config.provider}")

    async def _call_ollama(
        self,
        config: ModelConfig,
        messages: List[ChatMessage],
        tools: Optional[List[ToolDefinition]],
        tool_choice: Optional[str],
        temperature: float,
        max_tokens: int,
        stream: bool,
        format: Optional[str],
    ) -> ChatCompletionResponse:
        payload = {
            "model": config.name,
            "messages": [{"role": m.role.value, "content": m.content} for m in messages],
            "stream": stream,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        if format:
            payload["format"] = format
        if tools and config.supports_tools:
            payload["tools"] = [{"type": "function", "function": t.model_dump()} for t in tools]
            payload["tool_choice"] = tool_choice

        async with httpx.AsyncClient(base_url=config.base_url, timeout=config.max_tokens) as client:
            response = await client.post("/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()
            return ChatCompletionResponse(
                id=data.get("id", "ollama"),
                model=config.name,
                choices=[{"message": data.get("message", {}), "index": 0, "finish_reason": "stop"}],
                usage=data.get("usage", {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}),
            )

    async def _stream_ollama(
        self,
        config: ModelConfig,
        messages: List[ChatMessage],
        tools: Optional[List[ToolDefinition]],
        tool_choice: Optional[str],
        temperature: float,
        max_tokens: int,
        format: Optional[str],
    ) -> AsyncGenerator[str, None]:
        payload = {
            "model": config.name,
            "messages": [{"role": m.role.value, "content": m.content} for m in messages],
            "stream": True,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        if format:
            payload["format"] = format
        if tools and config.supports_tools:
            payload["tools"] = [{"type": "function", "function": t.model_dump()} for t in tools]
            payload["tool_choice"] = tool_choice

        async with httpx.AsyncClient(base_url=config.base_url, timeout=config.max_tokens) as client:
            async with client.stream("POST", "/api/chat", json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.strip():
                        try:
                            data = json.loads(line)
                            content = data.get("message", {}).get("content", "")
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            continue

    async def _call_openai(
        self,
        config: ModelConfig,
        messages: List[ChatMessage],
        tools: Optional[List[ToolDefinition]],
        tool_choice: Optional[str],
        temperature: float,
        max_tokens: int,
        stream: bool,
        format: Optional[str],
    ) -> ChatCompletionResponse:
        headers = {"Authorization": f"Bearer {config.api_key}", "Content-Type": "application/json"}
        payload = {
            "model": config.name,
            "messages": [{"role": m.role.value, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
        }
        if tools:
            payload["tools"] = [{"type": "function", "function": t.model_dump()} for t in tools]
            payload["tool_choice"] = tool_choice
        if format == "json":
            payload["response_format"] = {"type": "json_object"}

        async with httpx.AsyncClient(base_url=config.base_url, timeout=60.0) as client:
            response = await client.post("/v1/chat/completions", headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return ChatCompletionResponse(
                id=data.get("id", ""),
                model=data.get("model", config.name),
                choices=data.get("choices", []),
                usage=data.get("usage", {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}),
            )


model_router = ModelRouter()
llm_client = LLMClient(model_router)