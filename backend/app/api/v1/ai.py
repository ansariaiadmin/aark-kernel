from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from app.agent.brain import AgentBrain
from app.agent.llm import ModelConfig, ModelProvider, model_router
from app.agent.tools import ToolExecutor, get_all_tools
from app.core.config import get_settings

router = APIRouter(tags=["Advanced AI"])
settings = get_settings()

brain = AgentBrain()


class ModelRegisterRequest(BaseModel):
    name: str
    provider: str
    base_url: str
    api_key: str | None = None
    max_tokens: int = 4096
    temperature: float = 0.2
    supports_tools: bool = False
    supports_streaming: bool = True
    priority: int = 0


class ChatRequest(BaseModel):
    message: str
    model: str | None = None
    use_tools: bool = False
    stream: bool = False
    system_prompt: str | None = None


class EvaluateStreamRequest(BaseModel):
    wallet_balance_irt: float
    market_context: str


@router.get("/models")
async def list_models() -> dict[str, Any]:
    return {"models": model_router.list_models()}


@router.post("/models/register")
async def register_model(req: ModelRegisterRequest) -> dict[str, Any]:
    try:
        provider = ModelProvider(req.provider.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {req.provider}")

    config = ModelConfig(
        name=req.name,
        provider=provider,
        base_url=req.base_url,
        api_key=req.api_key,
        max_tokens=req.max_tokens,
        temperature=req.temperature,
        supports_tools=req.supports_tools,
        supports_streaming=req.supports_streaming,
        priority=req.priority,
    )
    model_router.register_model(config)
    return {"status": "registered", "model": req.name}


@router.post("/agent/chat")
async def agent_chat(req: ChatRequest) -> dict[str, Any]:
    if req.use_tools:
        tools = get_all_tools()
        result = await brain.chat_with_tools(req.message, tools, req.system_prompt)
        return {"response": result}
    else:
        # Simple chat without tools
        from app.agent.llm import ChatMessage, MessageRole, llm_client
        messages = [
            ChatMessage(role=MessageRole.SYSTEM, content=req.system_prompt or "You are AARK Kernel, a financial trading assistant."),
            ChatMessage(role=MessageRole.USER, content=req.message),
        ]
        response = await llm_client.chat(messages=messages, model=req.model)
        return {"response": response.choices[0]["message"]["content"]}


@router.post("/agent/evaluate/stream")
async def evaluate_stream(req: EvaluateStreamRequest):
    async def event_generator():
        async for chunk in brain.evaluate_market_stream(req.wallet_balance_irt, req.market_context):
            yield {"data": chunk}

    return EventSourceResponse(event_generator())


@router.post("/agent/memory/clear")
async def clear_memory() -> dict[str, str]:
    brain.clear_memory()
    return {"status": "memory cleared"}


@router.get("/agent/memory/summary")
async def get_memory_summary() -> dict[str, str | None]:
    return {"summary": brain.get_memory_summary()}


@router.get("/tools")
async def list_tools() -> dict[str, list[dict[str, Any]]]:
    tools = get_all_tools()
    return {"tools": [t.model_dump() for t in tools]}


@router.post("/tools/execute")
async def execute_tool(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    executor = ToolExecutor()
    result = await executor.execute(tool_name, arguments)
    return result