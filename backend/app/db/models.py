from enum import Enum as PyEnum

from app.db.session import Base
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func


class UserRole(str, PyEnum):
    ADMIN = "admin"
    TRADER = "trader"
    VIEWER = "viewer"


class OrderStatus(str, PyEnum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    FILLED = "filled"
    PARTIAL = "partial"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    FAILED = "failed"


class OrderSide(str, PyEnum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, PyEnum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class PositionSide(str, PyEnum):
    LONG = "long"
    SHORT = "short"
    FLAT = "flat"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    role = Column(SQLEnum(UserRole), default=UserRole.TRADER, nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True))

    # Relationships
    trades = relationship("Trade", back_populates="user")
    positions = relationship("Position", back_populates="user")
    api_keys = relationship("APIKey", back_populates="user")
    audit_logs = relationship("AuditLog", back_populates="user")


class APIKey(Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    exchange = Column(String(50), nullable=False)  # nobitex, binance, etc.
    key_name = Column(String(100))
    encrypted_key = Column(Text, nullable=False)
    encrypted_secret = Column(Text)
    is_active = Column(Boolean, default=True)
    permissions = Column(Text)  # JSON string of permissions
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_used = Column(DateTime(timezone=True))

    user = relationship("User", back_populates="api_keys")

    __table_args__ = (
        UniqueConstraint("user_id", "exchange", "key_name", name="uq_user_exchange_keyname"),
    )


class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    exchange = Column(String(50), nullable=False)
    symbol = Column(String(20), nullable=False, index=True)
    side = Column(SQLEnum(OrderSide), nullable=False)
    order_type = Column(SQLEnum(OrderType), nullable=False)
    quantity = Column(Float, nullable=False)
    price = Column(Float)  # None for market orders
    stop_price = Column(Float)  # For stop orders
    status = Column(SQLEnum(OrderStatus), default=OrderStatus.PENDING, nullable=False, index=True)
    filled_quantity = Column(Float, default=0.0)
    avg_fill_price = Column(Float)
    commission = Column(Float, default=0.0)
    commission_asset = Column(String(10), default="IRT")
    exchange_order_id = Column(String(100), index=True)
    client_order_id = Column(String(100), unique=True, index=True)
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    filled_at = Column(DateTime(timezone=True))

    user = relationship("User", back_populates="trades")

    __table_args__ = (
        Index("ix_trades_user_symbol_created", "user_id", "symbol", "created_at"),
    )


class Position(Base):
    __tablename__ = "positions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    exchange = Column(String(50), nullable=False)
    symbol = Column(String(20), nullable=False, index=True)
    side = Column(SQLEnum(PositionSide), default=PositionSide.FLAT, nullable=False)
    quantity = Column(Float, default=0.0)
    entry_price = Column(Float, default=0.0)
    mark_price = Column(Float, default=0.0)
    unrealized_pnl = Column(Float, default=0.0)
    realized_pnl = Column(Float, default=0.0)
    leverage = Column(Float, default=1.0)
    liquidation_price = Column(Float)
    margin_used = Column(Float, default=0.0)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_sync = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="positions")

    __table_args__ = (
        UniqueConstraint("user_id", "exchange", "symbol", name="uq_user_exchange_symbol_position"),
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(50))
    resource_id = Column(String(100))
    details = Column(Text)  # JSON string
    ip_address = Column(String(45))
    user_agent = Column(Text)
    status = Column(String(20), default="success")  # success, failure
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    user = relationship("User", back_populates="audit_logs")

    __table_args__ = (
        Index("ix_audit_user_action_created", "user_id", "action", "created_at"),
    )


class MarketData(Base):
    __tablename__ = "market_data"

    id = Column(Integer, primary_key=True, index=True)
    exchange = Column(String(50), nullable=False)
    symbol = Column(String(20), nullable=False, index=True)
    interval = Column(String(10), nullable=False)  # 1m, 5m, 15m, 1h, 4h, 1d
    open_price = Column(Float, nullable=False)
    high_price = Column(Float, nullable=False)
    low_price = Column(Float, nullable=False)
    close_price = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("exchange", "symbol", "interval", "timestamp", name="uq_market_data"),
        Index("ix_market_data_exchange_symbol_time", "exchange", "symbol", "timestamp"),
    )


class RiskMetrics(Base):
    __tablename__ = "risk_metrics"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    total_portfolio_value = Column(Float, default=0.0)
    daily_pnl = Column(Float, default=0.0)
    daily_pnl_pct = Column(Float, default=0.0)
    max_drawdown = Column(Float, default=0.0)
    var_95 = Column(Float, default=0.0)  # Value at Risk 95%
    var_99 = Column(Float, default=0.0)
    sharpe_ratio = Column(Float)
    sortino_ratio = Column(Float)
    correlation_risk = Column(Float, default=0.0)
    concentration_risk = Column(Float, default=0.0)
    leverage_ratio = Column(Float, default=1.0)
    margin_ratio = Column(Float, default=0.0)
    calculated_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    __table_args__ = (
        Index("ix_risk_user_calculated", "user_id", "calculated_at"),
    )