"""
Notification System v3.0.0 — پشتیبانی صفر — Zero Support
Unified notification: in-app + email + sms + telegram
سقف 10/10
"""
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

class NotificationChannel(str, Enum):
    IN_APP = "in_app"
    EMAIL = "email"
    SMS = "sms"
    TELEGRAM = "telegram"

class NotificationKind(str, Enum):
    TRADE = "trade"
    RISK = "risk"
    SYSTEM = "system"
    ERROR = "error"
    INFO = "info"
    ALERT = "alert"

class NotificationPayload(BaseModel):
    user_id: Optional[str] = None
    kind: NotificationKind
    title: str
    title_fa: str
    body: str
    body_fa: str
    channels: List[NotificationChannel]
    metadata: Optional[Dict[str, Any]] = None
    priority: str = "medium"  # low, medium, high, critical

class NotificationResult(BaseModel):
    channel: NotificationChannel
    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None
    at: str

class NotificationConfig(BaseModel):
    in_app_enabled: bool = True
    email_enabled: bool = False
    email_provider: str = "mock"
    sms_enabled: bool = False
    sms_provider: str = "mock"
    sms_sender: Optional[str] = None
    telegram_enabled: bool = False
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
