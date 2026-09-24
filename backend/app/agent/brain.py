import json
import logging
import os
from typing import Dict, Any, List, Optional, AsyncGenerator
from pydantic import BaseModel, Field, ValidationError

from app.agent.llm import (
    model_router,
    llm_client,
    ConversationMemory,
    ModelProvider,
    ModelConfig,
    ChatMessage,
    MessageRole,
    ToolDefinition,
)

logger = logging.getLogger(__name__)


class DecisionSchema(BaseModel):
    action: str = Field(default="HOLD", description="One of: BUY, SELL, HOLD")
    confidence: float = Field(default=0.0, ge=0.0, le=100.0, description="Confidence percentage 0-100")
    allocated_irt: float = Field(default=0.0, ge=0.0, description="Amount in IRT to allocate")
    reason: str = Field(default="عدم اطمینان", description="تحلیل و استدلال استراتژیک و اقتصادی دقیق به زبان فارسی")
    reply_message: str = Field(default="دستور پردازش شد.", description="پاسخ مستقیم و محترمانه به کاربر")


class AgentBrain:
    def __init__(
        self,
        model_name: str = "qwen2.5:7b",
        base_url: str = "",
        enable_memory: bool = True,
        max_memory_messages: int = 30,
    ):
        # Honor the container env (compose sets LOCAL_OLLAMA_HOST to the
        # docker host); fall back to loopback for bare-metal dev.
        if not base_url:
            base_url = os.getenv(
                "LOCAL_OLLAMA_HOST", "http://127.0.0.1:11434"
            )
        self.enable_memory = enable_memory
        self.memory = ConversationMemory(max_messages=max_memory_messages) if enable_memory else None

        # Register default Ollama model
        model_router.register_model(ModelConfig(
            name=model_name,
            provider=ModelProvider.OLLAMA,
            base_url=base_url,
            max_tokens=4096,
            temperature=0.2,
            supports_tools=False,
            supports_streaming=True,
            priority=10,
        ))

    def register_cloud_model(self, name: str, api_key: str, base_url: str = "https://api.openai.com/v1") -> None:
        model_router.register_model(ModelConfig(
            name=name,
            provider=ModelProvider.OPENAI,
            base_url=base_url,
            api_key=api_key,
            max_tokens=4096,
            temperature=0.2,
            supports_tools=True,
            supports_streaming=True,
            priority=20,
        ))

    async def evaluate_market(self, wallet_balance_irt: float, market_context: str) -> Dict[str, Any]:
        max_order_cap = wallet_balance_irt * 0.20

        system_prompt = f"""شما هسته تصمیم‌گیری هوشمند سیستم مالی AARK هستید.
وظیفه شما تحلیل داده‌ها، مدیریت ریسک و پاسخ‌دهی به اپراتور (ممد) است.

قوانین قطعی سیستم:
۱. موجودی کل فعلی: {wallet_balance_irt:,.0f} تومان.
۲. سقف قطعی مجاز برای هر سفارش خرید (۲۰٪ موجودی): {max_order_cap:,.0f} تومان است. مقدار allocated_irt هرگز نباید بیشتر از این سقف باشد.
۳. در شرایط ابهام یا پیام‌های عمومی/احوالپرسی: action=HOLD، تخصیص=0 و پاسخ دوستانه و حرفه‌ای.
۴. زبان خروجی: تمام بخش‌های 'reason' و 'reply_message' حتماً و بدون استثنا باید به زبان فارسی دقیق و روان باشند.
۵. قالب پاسخ: فقط و فقط یک آبجکت معتبر JSON با کلیدهای زیر:
{{
  "action": "BUY" | "SELL" | "HOLD",
  "confidence": عدد بین 0 تا 100,
  "allocated_irt": عدد بر حسب تومان,
  "reason": "استدلال کوتاه و دقیق به فارسی",
  "reply_message": "پیام فارسی برای نمایش در چت"
}}"""

        user_content = f"سناریو / پیام اپراتور: {market_context}"

        messages = [
            ChatMessage(role=MessageRole.SYSTEM, content=system_prompt),
            ChatMessage(role=MessageRole.USER, content=user_content),
        ]

        # Add conversation history if memory enabled
        if self.memory:
            history = self.memory.get_messages()
            messages = [messages[0]] + history + [messages[1]]

        try:
            response = await llm_client.chat(
                messages=messages,
                format="json",
                temperature=0.2,
                max_tokens=1024,
            )

            raw_content = response.choices[0]["message"].get("content", "{}")
            parsed = json.loads(raw_content)

            decision = DecisionSchema(**parsed)
            action_clean = decision.action.upper()
            if action_clean not in ["BUY", "SELL", "HOLD"]:
                action_clean = "HOLD"

            result = decision.model_dump()
            result["action"] = action_clean

            # Store in memory
            if self.memory:
                self.memory.add_message(ChatMessage(role=MessageRole.USER, content=user_content))
                self.memory.add_message(ChatMessage(role=MessageRole.ASSISTANT, content=raw_content))

            return result

        except (json.JSONDecodeError, ValidationError, Exception) as e:
            logger.error(f"Brain evaluation error: {e}")
            return {
                "action": "HOLD",
                "confidence": 0.0,
                "allocated_irt": 0.0,
                "reason": f"خطا در پردازش هوش مصنوعی: {str(e)}",
                "reply_message": "در پردازش سناریو خطایی رخ داد. وضعیت جهت حفظ سرمایه روی HOLD تنظیم شد.",
            }

    async def evaluate_market_stream(
        self, wallet_balance_irt: float, market_context: str
    ) -> AsyncGenerator[str, None]:
        """Stream the evaluation response token by token."""
        max_order_cap = wallet_balance_irt * 0.20

        system_prompt = f"""شما هسته تصمیم‌گیری هوشمند سیستم مالی AARK هستید.
وظیفه شما تحلیل داده‌ها، مدیریت ریسک و پاسخ‌دهی به اپراتور (ممد) است.

قوانین قطعی سیستم:
۱. موجودی کل فعلی: {wallet_balance_irt:,.0f} تومان.
۲. سقف قطعی مجاز برای هر سفارش خرید (۲۰٪ موجودی): {max_order_cap:,.0f} تومان است.
۳. در شرایط ابهام: action=HOLD، تخصیص=0.
۴. زبان خروجی: فارسی.
۵. قالب پاسخ: JSON با action, confidence, allocated_irt, reason, reply_message"""

        user_content = f"سناریو / پیام اپراتور: {market_context}"

        messages = [
            ChatMessage(role=MessageRole.SYSTEM, content=system_prompt),
            ChatMessage(role=MessageRole.USER, content=user_content),
        ]

        if self.memory:
            history = self.memory.get_messages()
            messages = [messages[0]] + history + [messages[1]]

        try:
            full_response = ""
            async for chunk in llm_client.stream_chat(
                messages=messages,
                format="json",
                temperature=0.2,
                max_tokens=1024,
            ):
                full_response += chunk
                yield chunk

            # Parse and store complete response
            try:
                parsed = json.loads(full_response)
                decision = DecisionSchema(**parsed)
                action_clean = decision.action.upper()
                if action_clean not in ["BUY", "SELL", "HOLD"]:
                    action_clean = "HOLD"
                result = decision.model_dump()
                result["action"] = action_clean

                if self.memory:
                    self.memory.add_message(ChatMessage(role=MessageRole.USER, content=user_content))
                    self.memory.add_message(ChatMessage(role=MessageRole.ASSISTANT, content=full_response))

            except Exception:
                pass

        except Exception as e:
            logger.error(f"Stream evaluation error: {e}")
            yield json.dumps({
                "action": "HOLD",
                "confidence": 0.0,
                "allocated_irt": 0.0,
                "reason": f"خطا در پردازش: {str(e)}",
                "reply_message": "خطا در پردازش جریان.",
            })

    async def chat_with_tools(
        self,
        user_message: str,
        tools: List[ToolDefinition],
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Chat with tool calling support."""
        default_system = "You are AARK Kernel, a financial trading assistant with access to tools."
        messages = [
            ChatMessage(role=MessageRole.SYSTEM, content=system_prompt or default_system),
            ChatMessage(role=MessageRole.USER, content=user_message),
        ]

        if self.memory:
            history = self.memory.get_messages()
            messages = [messages[0]] + history + [messages[1]]

        response = await llm_client.chat(
            messages=messages,
            tools=tools,
            tool_choice="auto",
            temperature=0.1,
        )

        return response.model_dump()

    def clear_memory(self) -> None:
        if self.memory:
            self.memory.clear()

    def get_memory_summary(self) -> Optional[str]:
        return self.memory.summary if self.memory else None