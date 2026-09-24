"""
Nobitex Paper Trader - Real-time paper trading with slippage simulation
Uses Nobitex public API (no key required) with fallback to mock prices for offline testing
"""

import asyncio
import random
import time
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False


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
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass
class PaperOrder:
    order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    filled_price: Optional[float] = None
    filled_quantity: float = 0.0
    slippage: float = 0.0
    commission: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    pnl: float = 0.0


@dataclass
class PaperPosition:
    symbol: str
    quantity: float
    avg_entry_price: float
    current_price: float
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    total_cost: float = 0.0


@dataclass
class PaperBalance:
    asset: str
    free: float
    locked: float = 0.0

    @property
    def total(self) -> float:
        return self.free + self.locked


class NobitexPaperTrader:
    """
    Paper trading simulator with real-time price fetching and slippage
    
    Features:
    - Fetches real prices from Nobitex public API (no auth needed)
    - Falls back to mock prices when offline
    - Slippage simulation 0.1-0.3%
    - Position tracking with PnL (unrealized + realized)
    - Portfolio rebalancing
    - Market/Limit/Stop orders
    """

    # Mock prices for offline testing (realistic as of 2024)
    MOCK_PRICES = {
        "BTCUSDT": 60000.0,
        "ETHUSDT": 3000.0,
        "USDTIRT": 1.0,
        "BTCIRT": 3000000000.0,  # 3B IRT
        "ETHIRT": 150000000.0,
    }

    def __init__(self, initial_balance: float = 100000.0, base_currency: str = "USDT"):
        self.base_currency = base_currency
        self.initial_balance = initial_balance
        self.balances: Dict[str, PaperBalance] = {
            base_currency: PaperBalance(asset=base_currency, free=initial_balance)
        }
        self.positions: Dict[str, PaperPosition] = {}
        self.orders: Dict[str, PaperOrder] = {}
        self.trade_history: List[PaperOrder] = []
        self.price_cache: Dict[str, float] = self.MOCK_PRICES.copy()
        self.price_cache_time: Dict[str, float] = {}
        self.commission_rate = 0.001  # 0.1% commission
        self.slippage_range = (0.001, 0.003)  # 0.1% to 0.3%

    async def get_market_price(self, symbol: str) -> float:
        """Fetch real-time price from Nobitex public API with fallback to mock"""
        # Check cache (5 sec TTL)
        now = time.time()
        if symbol in self.price_cache_time and now - self.price_cache_time[symbol] < 5:
            return self.price_cache[symbol]

        # Try real API if httpx available
        if HAS_HTTPX:
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    # Nobitex uses srcCurrency and dstCurrency
                    # Symbol like BTCUSDT -> src=btc, dst=usdt
                    if len(symbol) >= 6:
                        src = symbol[:-4].lower()
                        dst = symbol[-4:].lower()
                        # Try stats endpoint
                        resp = await client.get(
                            "https://api.nobitex.ir/market/stats",
                            params={"srcCurrency": src, "dstCurrency": dst},
                        )
                        if resp.status_code == 200:
                            data = resp.json()
                            # Parse price from stats
                            # Data structure: {"stats": {"btc-usdt": {"latest": "60000", ...}}}
                            stats = data.get("stats", {})
                            for key, val in stats.items():
                                if src in key.lower() and dst in key.lower():
                                    latest = val.get("latest") or val.get("last") or val.get("markPrice")
                                    if latest:
                                        price = float(latest)
                                        self.price_cache[symbol] = price
                                        self.price_cache_time[symbol] = now
                                        return price
            except Exception as e:
                logger.debug(f"Failed to fetch real price for {symbol}: {e}, using mock")

        # Fallback to mock price with small random walk to simulate real-time
        base_price = self.MOCK_PRICES.get(symbol, 100.0)
        # Add random walk ±0.5% to simulate real-time movement
        random_factor = random.uniform(-0.005, 0.005)
        price = base_price * (1 + random_factor)
        self.price_cache[symbol] = price
        self.price_cache_time[symbol] = now
        return price

    def _calculate_slippage(self) -> float:
        """Random slippage between 0.1% and 0.3%"""
        return random.uniform(*self.slippage_range)

    def _calculate_commission(self, quantity: float, price: float) -> float:
        """Calculate commission"""
        return quantity * price * self.commission_rate

    async def place_market_order(self, symbol: str, side: OrderSide, quantity: float) -> PaperOrder:
        """Place market order with slippage simulation"""
        current_price = await self.get_market_price(symbol)
        slippage = self._calculate_slippage()

        # Apply slippage: buy at higher price, sell at lower price
        if side == OrderSide.BUY:
            filled_price = current_price * (1 + slippage)
        else:
            filled_price = current_price * (1 - slippage)

        commission = self._calculate_commission(quantity, filled_price)

        order_id = f"paper_{int(time.time()*1000)}_{random.randint(1000,9999)}"
        order = PaperOrder(
            order_id=order_id,
            symbol=symbol,
            side=side,
            order_type=OrderType.MARKET,
            quantity=quantity,
            price=current_price,
            status=OrderStatus.FILLED,
            filled_price=filled_price,
            filled_quantity=quantity,
            slippage=slippage,
            commission=commission,
        )

        # Update balances and positions
        self._update_position(order)
        self.orders[order_id] = order
        self.trade_history.append(order)

        logger.info(f"Market order filled: {side} {quantity} {symbol} @ {filled_price:.2f} (slippage {slippage*100:.3f}%)")
        return order

    async def place_limit_order(self, symbol: str, side: OrderSide, quantity: float, price: float) -> PaperOrder:
        """Place limit order - will be filled when market reaches target"""
        order_id = f"paper_{int(time.time()*1000)}_{random.randint(1000,9999)}"
        order = PaperOrder(
            order_id=order_id,
            symbol=symbol,
            side=side,
            order_type=OrderType.LIMIT,
            quantity=quantity,
            price=price,
            status=OrderStatus.PENDING,
        )
        self.orders[order_id] = order
        logger.info(f"Limit order placed: {side} {quantity} {symbol} @ {price:.2f}")
        return order

    async def place_stop_order(self, symbol: str, side: OrderSide, quantity: float, stop_price: float) -> PaperOrder:
        """Place stop order - triggers when price crosses stop_price"""
        order_id = f"paper_{int(time.time()*1000)}_{random.randint(1000,9999)}"
        order = PaperOrder(
            order_id=order_id,
            symbol=symbol,
            side=side,
            order_type=OrderType.STOP,
            quantity=quantity,
            stop_price=stop_price,
            status=OrderStatus.PENDING,
        )
        self.orders[order_id] = order
        logger.info(f"Stop order placed: {side} {quantity} {symbol} stop @ {stop_price:.2f}")
        return order

    async def check_pending_orders(self) -> List[PaperOrder]:
        """Check and fill pending limit/stop orders based on current market price"""
        filled = []
        for order_id, order in list(self.orders.items()):
            if order.status != OrderStatus.PENDING:
                continue

            current_price = await self.get_market_price(order.symbol)

            should_fill = False
            if order.order_type == OrderType.LIMIT:
                if order.side == OrderSide.BUY and current_price <= order.price:
                    should_fill = True
                elif order.side == OrderSide.SELL and current_price >= order.price:
                    should_fill = True
            elif order.order_type == OrderType.STOP:
                if order.side == OrderSide.BUY and current_price >= order.stop_price:
                    should_fill = True
                elif order.side == OrderSide.SELL and current_price <= order.stop_price:
                    should_fill = True

            if should_fill:
                slippage = self._calculate_slippage()
                # For limit/stop, filled price is close to target with slippage
                if order.side == OrderSide.BUY:
                    filled_price = (order.price or order.stop_price or current_price) * (1 + slippage)
                else:
                    filled_price = (order.price or order.stop_price or current_price) * (1 - slippage)

                order.filled_price = filled_price
                order.filled_quantity = order.quantity
                order.slippage = slippage
                order.commission = self._calculate_commission(order.quantity, filled_price)
                order.status = OrderStatus.FILLED

                self._update_position(order)
                self.trade_history.append(order)
                filled.append(order)
                logger.info(f"Pending order filled: {order.side} {order.quantity} {order.symbol} @ {filled_price:.2f}")

        return filled

    def _update_position(self, order: PaperOrder):
        """Update position and PnL tracking"""
        symbol = order.symbol
        quantity = order.quantity if order.side == OrderSide.BUY else -order.quantity
        price = order.filled_price or order.price or 0

        if symbol not in self.positions:
            if quantity > 0:
                # New long position
                self.positions[symbol] = PaperPosition(
                    symbol=symbol,
                    quantity=quantity,
                    avg_entry_price=price,
                    current_price=price,
                    total_cost=quantity * price + order.commission,
                )
            # If selling without position, create short (simplified)
            else:
                self.positions[symbol] = PaperPosition(
                    symbol=symbol,
                    quantity=quantity,
                    avg_entry_price=price,
                    current_price=price,
                    total_cost=quantity * price,
                )
        else:
            pos = self.positions[symbol]
            old_qty = pos.quantity
            new_qty = old_qty + quantity

            if old_qty == 0:
                pos.quantity = new_qty
                pos.avg_entry_price = price
                pos.total_cost = new_qty * price
            elif (old_qty > 0 and quantity > 0) or (old_qty < 0 and quantity < 0):
                # Adding to existing position
                total_cost = pos.total_cost + quantity * price
                pos.quantity = new_qty
                pos.avg_entry_price = total_cost / new_qty if new_qty != 0 else 0
                pos.total_cost = total_cost
            else:
                # Reducing or closing position - calculate realized PnL
                closing_qty = min(abs(quantity), abs(old_qty))
                if old_qty > 0:
                    # Closing long
                    pnl = closing_qty * (price - pos.avg_entry_price) - order.commission
                else:
                    # Closing short
                    pnl = closing_qty * (pos.avg_entry_price - price) - order.commission

                pos.realized_pnl += pnl
                pos.quantity = new_qty
                if new_qty == 0:
                    pos.total_cost = 0
                    pos.avg_entry_price = 0
                else:
                    # Partial close, keep avg entry for remaining
                    pos.total_cost = new_qty * pos.avg_entry_price

            # Update current price and unrealized PnL
            pos.current_price = price
            if pos.quantity != 0:
                pos.unrealized_pnl = pos.quantity * (pos.current_price - pos.avg_entry_price)
            else:
                pos.unrealized_pnl = 0

        # Update balances
        base_asset = self.base_currency
        cost = order.filled_quantity * (order.filled_price or 0) + order.commission
        if order.side == OrderSide.BUY:
            # Deduct base currency
            if base_asset in self.balances:
                self.balances[base_asset].free -= cost
        else:
            # Add base currency from sale
            if base_asset in self.balances:
                self.balances[base_asset].free += (order.filled_quantity * (order.filled_price or 0) - order.commission)

    async def update_positions_pnl(self):
        """Update unrealized PnL for all positions with current market prices"""
        for symbol, pos in self.positions.items():
            if pos.quantity != 0:
                current_price = await self.get_market_price(symbol)
                pos.current_price = current_price
                pos.unrealized_pnl = pos.quantity * (current_price - pos.avg_entry_price)

    def get_portfolio_value(self) -> float:
        """Calculate total portfolio value"""
        total = 0.0
        # Base currency balance
        for bal in self.balances.values():
            total += bal.total

        # Positions value
        for pos in self.positions.values():
            total += pos.quantity * pos.current_price + pos.realized_pnl + pos.unrealized_pnl

        return total

    def get_total_pnl(self) -> Dict[str, float]:
        """Get total PnL breakdown"""
        realized = sum(p.realized_pnl for p in self.positions.values())
        unrealized = sum(p.unrealized_pnl for p in self.positions.values())
        return {
            "realized": realized,
            "unrealized": unrealized,
            "total": realized + unrealized,
        }

    async def rebalance_portfolio(self, target_allocations: Dict[str, float]) -> List[PaperOrder]:
        """
        Rebalance portfolio to target allocations
        Example: {"BTCUSDT": 0.6, "ETHUSDT": 0.3, "USDTIRT": 0.1}
        """
        portfolio_value = self.get_portfolio_value()
        orders = []

        for symbol, target_pct in target_allocations.items():
            if symbol == self.base_currency:
                continue

            current_price = await self.get_market_price(symbol)
            target_value = portfolio_value * target_pct
            current_pos = self.positions.get(symbol)
            current_value = (current_pos.quantity * current_pos.current_price) if current_pos else 0

            diff_value = target_value - current_value
            if abs(diff_value) < portfolio_value * 0.01:  # Less than 1% diff, skip
                continue

            diff_quantity = diff_value / current_price

            if diff_quantity > 0:
                # Need to buy
                order = await self.place_market_order(symbol, OrderSide.BUY, abs(diff_quantity))
                orders.append(order)
            else:
                # Need to sell
                order = await self.place_market_order(symbol, OrderSide.SELL, abs(diff_quantity))
                orders.append(order)

        return orders

    def get_positions_summary(self) -> Dict[str, Any]:
        """Get summary of all positions"""
        return {
            symbol: {
                "quantity": pos.quantity,
                "avg_entry": pos.avg_entry_price,
                "current": pos.current_price,
                "unrealized_pnl": pos.unrealized_pnl,
                "realized_pnl": pos.realized_pnl,
                "total_pnl": pos.realized_pnl + pos.unrealized_pnl,
            }
            for symbol, pos in self.positions.items()
        }
