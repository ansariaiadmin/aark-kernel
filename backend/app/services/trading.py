import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class Exchange(str, Enum):
    NOBITEX = "nobitex"
    BINANCE = "binance"
    BYBIT = "bybit"


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderStatus(str, Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    FILLED = "filled"
    PARTIAL = "partial"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    FAILED = "failed"


@dataclass
class OrderRequest:
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: Decimal
    price: Decimal | None = None
    stop_price: Decimal | None = None
    client_order_id: str | None = None


@dataclass
class OrderResponse:
    order_id: str
    client_order_id: str | None
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: Decimal
    price: Decimal | None
    status: OrderStatus
    filled_quantity: Decimal = Decimal(0)
    avg_fill_price: Decimal | None = None
    commission: Decimal = Decimal(0)
    commission_asset: str = "IRT"
    timestamp: datetime = datetime.now(timezone.utc)
    error: str | None = None


@dataclass
class Position:
    symbol: str
    side: str  # long, short, flat
    quantity: Decimal
    entry_price: Decimal
    mark_price: Decimal
    unrealized_pnl: Decimal
    realized_pnl: Decimal
    leverage: Decimal = Decimal(1)
    liquidation_price: Decimal | None = None
    margin_used: Decimal = Decimal(0)


@dataclass
class Balance:
    asset: str
    free: Decimal
    locked: Decimal
    total: Decimal


class NobitexClient:
    def __init__(self, api_key: str, base_url: str = "https://api.nobitex.ir"):
        self.api_key = api_key
        self.base_url = base_url
        self.session = httpx.AsyncClient(timeout=30.0, trust_env=False)

    async def close(self):
        await self.session.aclose()

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Token {self.api_key}", "Content-Type": "application/json"}

    async def get_balance(self) -> list[Balance]:
        response = await self.session.get(f"{self.base_url}/users/wallets/list", headers=self._headers())
        response.raise_for_status()
        data = response.json()
        balances = []
        for currency, info in data.get("wallets", {}).items():
            balances.append(Balance(
                asset=currency.upper(),
                free=Decimal(str(info.get("balance", "0"))),
                locked=Decimal(str(info.get("blocked", "0"))),
                total=Decimal(str(info.get("balance", "0"))) + Decimal(str(info.get("blocked", "0"))),
            ))
        return balances

    async def get_ticker(self, symbol: str) -> dict[str, Any]:
        # Nobitex uses symbols like BTCUSDT
        response = await self.session.get(f"{self.base_url}/market/stats", params={"srcCurrency": symbol[:-4], "dstCurrency": symbol[-4:]})
        response.raise_for_status()
        return response.json()

    async def get_orderbook(self, symbol: str, depth: int = 20) -> dict[str, Any]:
        src = symbol[:-4]
        dst = symbol[-4:]
        response = await self.session.get(f"{self.base_url}/market/orderbook", params={"symbol": f"{src}{dst}", "depth": depth})
        response.raise_for_status()
        return response.json()

    async def place_order(self, request: OrderRequest) -> OrderResponse:
        src = request.symbol[:-4].lower()
        dst = request.symbol[-4:].lower()
        side = "buy" if request.side == OrderSide.BUY else "sell"
        order_type = request.order_type.value

        payload = {
            "type": side,
            "srcCurrency": src,
            "dstCurrency": dst,
            "amount": str(request.quantity),
            "execution": order_type,
        }

        if request.order_type in [OrderType.LIMIT, OrderType.STOP_LIMIT] and request.price:
            payload["price"] = str(request.price)

        if request.order_type in [OrderType.STOP, OrderType.STOP_LIMIT] and request.stop_price:
            payload["stopPrice"] = str(request.stop_price)

        if request.client_order_id:
            payload["clientOrderId"] = request.client_order_id

        response = await self.session.post(f"{self.base_url}/market/orders/add", headers=self._headers(), json=payload)
        data = response.json()

        if response.status_code != 200 or data.get("status") != "ok":
            return OrderResponse(
                order_id="",
                client_order_id=request.client_order_id,
                symbol=request.symbol,
                side=request.side,
                order_type=request.order_type,
                quantity=request.quantity,
                price=request.price,
                status=OrderStatus.REJECTED,
                error=data.get("message", "Unknown error"),
            )

        order_data = data.get("order", {})
        return OrderResponse(
            order_id=str(order_data.get("id", "")),
            client_order_id=request.client_order_id,
            symbol=request.symbol,
            side=request.side,
            order_type=request.order_type,
            quantity=request.quantity,
            price=request.price,
            status=OrderStatus.SUBMITTED,
        )

    async def cancel_order(self, order_id: str) -> bool:
        response = await self.session.post(f"{self.base_url}/market/orders/cancel", headers=self._headers(), json={"id": order_id})
        response.raise_for_status()
        data = response.json()
        return data.get("status") == "ok"

    async def get_order_status(self, order_id: str) -> OrderResponse:
        response = await self.session.post(f"{self.base_url}/market/orders/status", headers=self._headers(), json={"id": order_id})
        response.raise_for_status()
        data = response.json()
        order_data = data.get("order", {})
        return OrderResponse(
            order_id=str(order_data.get("id", "")),
            client_order_id=order_data.get("clientOrderId"),
            symbol=order_data.get("symbol", ""),
            side=OrderSide(order_data.get("type", "buy")),
            order_type=OrderType(order_data.get("execution", "market")),
            quantity=Decimal(str(order_data.get("amount", "0"))),
            price=Decimal(str(order_data.get("price", "0"))) if order_data.get("price") else None,
            status=OrderStatus(order_data.get("status", "pending")),
            filled_quantity=Decimal(str(order_data.get("matchedAmount", "0"))),
            avg_fill_price=Decimal(str(order_data.get("matchedPrice", "0"))) if order_data.get("matchedPrice") else None,
            commission=Decimal(str(order_data.get("fee", "0"))),
        )

    async def get_open_orders(self, symbol: str | None = None) -> list[OrderResponse]:
        payload = {}
        if symbol:
            payload["srcCurrency"] = symbol[:-4].lower()
            payload["dstCurrency"] = symbol[-4:].lower()
        response = await self.session.post(f"{self.base_url}/market/orders/list", headers=self._headers(), json=payload)
        response.raise_for_status()
        data = response.json()
        orders = []
        for o in data.get("orders", []):
            orders.append(OrderResponse(
                order_id=str(o.get("id", "")),
                client_order_id=o.get("clientOrderId"),
                symbol=o.get("symbol", ""),
                side=OrderSide(o.get("type", "buy")),
                order_type=OrderType(o.get("execution", "market")),
                quantity=Decimal(str(o.get("amount", "0"))),
                price=Decimal(str(o.get("price", "0"))) if o.get("price") else None,
                status=OrderStatus(o.get("status", "pending")),
                filled_quantity=Decimal(str(o.get("matchedAmount", "0"))),
                avg_fill_price=Decimal(str(o.get("matchedPrice", "0"))) if o.get("matchedPrice") else None,
                commission=Decimal(str(o.get("fee", "0"))),
            ))
        return orders

    async def get_positions(self) -> list[Position]:
        # Nobitex doesn't have traditional positions, compute from balances
        balances = await self.get_balance()
        positions = []
        for bal in balances:
            if bal.total > 0 and bal.asset != "IRT":
                # This is a simplification - real positions need entry price tracking
                positions.append(Position(
                    symbol=f"{bal.asset}IRT",
                    side="long",
                    quantity=bal.total,
                    entry_price=Decimal(0),
                    mark_price=Decimal(0),
                    unrealized_pnl=Decimal(0),
                    realized_pnl=Decimal(0),
                ))
        return positions


class OrderManager:
    def __init__(self, client: NobitexClient):
        self.client = client
        self.pending_orders: dict[str, OrderResponse] = {}

    async def submit_order(self, request: OrderRequest) -> OrderResponse:
        response = await self.client.place_order(request)
        if response.status == OrderStatus.SUBMITTED:
            self.pending_orders[response.order_id] = response
        return response

    async def cancel_order(self, order_id: str) -> bool:
        success = await self.client.cancel_order(order_id)
        if success and order_id in self.pending_orders:
            self.pending_orders[order_id].status = OrderStatus.CANCELLED
        return success

    async def refresh_order(self, order_id: str) -> OrderResponse | None:
        if order_id not in self.pending_orders:
            return None
        updated = await self.client.get_order_status(order_id)
        self.pending_orders[order_id] = updated
        if updated.status in [OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED]:
            del self.pending_orders[order_id]
        return updated

    async def refresh_all(self) -> list[OrderResponse]:
        updated = []
        to_remove = []
        for order_id in self.pending_orders:
            refreshed = await self.client.get_order_status(order_id)
            self.pending_orders[order_id] = refreshed
            updated.append(refreshed)
            if refreshed.status in [OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED]:
                to_remove.append(order_id)
        for oid in to_remove:
            del self.pending_orders[oid]
        return updated


class PortfolioManager:
    def __init__(self, client: NobitexClient):
        self.client = client
        self.positions: dict[str, Position] = {}
        self.balances: dict[str, Balance] = {}

    async def refresh_balances(self) -> dict[str, Balance]:
        balances = await self.client.get_balance()
        self.balances = {b.asset: b for b in balances}
        return self.balances

    async def refresh_positions(self) -> dict[str, Position]:
        positions = await self.client.get_positions()
        self.positions = {p.symbol: p for p in positions}
        return self.positions

    async def get_total_portfolio_value(self, prices: dict[str, Decimal]) -> Decimal:
        total = Decimal(0)
        for asset, balance in self.balances.items():
            if asset == "IRT":
                total += balance.total
            else:
                symbol = f"{asset}IRT"
                price = prices.get(symbol, Decimal(0))
                total += balance.total * price
        return total

    def get_pnl_summary(self) -> dict[str, Decimal]:
        total_unrealized = sum(p.unrealized_pnl for p in self.positions.values())
        total_realized = sum(p.realized_pnl for p in self.positions.values())
        return {
            "unrealized_pnl": total_unrealized,
            "realized_pnl": total_realized,
            "total_pnl": total_unrealized + total_realized,
        }