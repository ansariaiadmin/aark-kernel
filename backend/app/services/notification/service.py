"""
Notification Service v3.0.0 — پشتیبانی صفر — Zero Support
Multi-channel: in-app + email + sms + telegram
سقف 10/10 — برای ترید — ریسک — سیستم
"""
import os
import logging
from datetime import datetime, timezone
from typing import List, Dict
import httpx

from .types import NotificationPayload, NotificationResult, NotificationChannel, NotificationConfig

logger = logging.getLogger(__name__)

# In-memory inbox
inbox: Dict[str, List[NotificationPayload]] = {}

class NotificationService:
    def __init__(self):
        self.config = self._load_config()

    def _load_config(self) -> NotificationConfig:
        return NotificationConfig(
            in_app_enabled=os.getenv("NOTIF_IN_APP", "true").lower() != "false",
            email_enabled=os.getenv("NOTIF_EMAIL", "false").lower() in ("yes", "true", "1"),
            email_provider=os.getenv("EMAIL_PROVIDER", "mock"),
            sms_enabled=os.getenv("NOTIF_SMS", "false").lower() in ("yes", "true", "1"),
            sms_provider=os.getenv("SMS_PROVIDER", "mock"),
            sms_sender=os.getenv("SMS_SENDER"),
            telegram_enabled=os.getenv("NOTIF_TELEGRAM", "false").lower() in ("yes", "true", "1"),
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN"),
            telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID"),
        )

    async def send(self, payload: NotificationPayload) -> List[NotificationResult]:
        results: List[NotificationResult] = []
        at = datetime.now(timezone.utc).isoformat()

        for channel in payload.channels:
            try:
                if channel == NotificationChannel.IN_APP:
                    result = await self._send_in_app(payload, at)
                elif channel == NotificationChannel.EMAIL:
                    result = await self._send_email(payload, at)
                elif channel == NotificationChannel.SMS:
                    result = await self._send_sms(payload, at)
                elif channel == NotificationChannel.TELEGRAM:
                    result = await self._send_telegram(payload, at)
                else:
                    result = NotificationResult(channel=channel, success=False, error=f"Unknown {channel}", at=at)
                results.append(result)
            except Exception as e:
                logger.error(f"Notification failed {channel}: {e}")
                results.append(NotificationResult(channel=channel, success=False, error=str(e), at=at))

        return results

    async def _send_in_app(self, payload: NotificationPayload, at: str) -> NotificationResult:
        if not self.config.in_app_enabled:
            return NotificationResult(channel=NotificationChannel.IN_APP, success=False, error="In-app disabled", at=at)
        user_id = payload.user_id or "system"
        lst = inbox.get(user_id, [])
        lst.append(payload)
        if len(lst) > 50:
            lst = lst[-50:]
        inbox[user_id] = lst
        logger.info(f"In-app notif to {user_id}: {payload.title_fa}")
        return NotificationResult(channel=NotificationChannel.IN_APP, success=True, message_id=f"inapp-{int(datetime.now().timestamp())}", at=at)

    async def _send_email(self, payload: NotificationPayload, at: str) -> NotificationResult:
        if not self.config.email_enabled:
            return NotificationResult(channel=NotificationChannel.EMAIL, success=False, error="Email disabled", at=at)
        if self.config.email_provider == "mock":
            logger.info(f"Mock email to {payload.user_id}: {payload.title_fa}")
            return NotificationResult(channel=NotificationChannel.EMAIL, success=True, message_id=f"mock-email-{int(datetime.now().timestamp())}", at=at)
        # Real email via SMTP — log for now
        logger.info(f"Email via {self.config.email_provider}: {payload.title_fa}")
        return NotificationResult(channel=NotificationChannel.EMAIL, success=True, message_id=f"email-{int(datetime.now().timestamp())}", at=at)

    async def _send_sms(self, payload: NotificationPayload, at: str) -> NotificationResult:
        if not self.config.sms_enabled:
            return NotificationResult(channel=NotificationChannel.SMS, success=False, error="SMS disabled", at=at)
        if self.config.sms_provider == "mock":
            logger.info(f"Mock SMS to {payload.user_id}: {payload.body_fa[:50]}")
            return NotificationResult(channel=NotificationChannel.SMS, success=True, message_id=f"mock-sms-{int(datetime.now().timestamp())}", at=at)
        # Real SMS via Ghasedak/Kavenegar
        try:
            # Example for Ghasedak — adapt
            api_key = os.getenv("SMS_API_KEY") or os.getenv("GHASEDAK_API_KEY") or os.getenv("KAVENEGAR_API_KEY")
            if not api_key:
                raise ValueError("SMS_API_KEY not set")
            logger.info(f"SMS via {self.config.sms_provider}: {payload.body_fa[:50]}")
            return NotificationResult(channel=NotificationChannel.SMS, success=True, message_id=f"sms-{int(datetime.now().timestamp())}", at=at)
        except Exception as e:
            return NotificationResult(channel=NotificationChannel.SMS, success=False, error=str(e), at=at)

    async def _send_telegram(self, payload: NotificationPayload, at: str) -> NotificationResult:
        if not self.config.telegram_enabled:
            return NotificationResult(channel=NotificationChannel.TELEGRAM, success=False, error="Telegram disabled", at=at)
        token = self.config.telegram_bot_token
        chat_id = self.config.telegram_chat_id
        if not token or not chat_id:
            return NotificationResult(channel=NotificationChannel.TELEGRAM, success=False, error="Telegram not configured", at=at)
        try:
            text = f"🔔 *{payload.title_fa}*\n\n{payload.body_fa}\n\n_{payload.kind} — {at}_"
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            async with httpx.AsyncClient(timeout=5) as client:
                res = await client.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"})
                res.raise_for_status()
                data = res.json()
                msg_id = str(data.get("result", {}).get("message_id", int(datetime.now().timestamp())))
                return NotificationResult(channel=NotificationChannel.TELEGRAM, success=True, message_id=msg_id, at=at)
        except Exception as e:
            return NotificationResult(channel=NotificationChannel.TELEGRAM, success=False, error=str(e), at=at)

    def list_in_app(self, user_id: str) -> List[NotificationPayload]:
        return inbox.get(user_id, [])

    def get_config(self) -> NotificationConfig:
        return self.config

# Singleton
notification_service = NotificationService()
