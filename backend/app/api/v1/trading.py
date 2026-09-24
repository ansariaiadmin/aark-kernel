from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from decimal import Decimal
from datetime import datetime

from app.services.trading import (
    NobitexClient,
    OrderManager,
    PortfolioManager,
    OrderRequest,
    OrderResponse,
    OrderSide,
    OrderType,
    OrderStatus,
    Position,
    Balance,
    Exchange,
)
from app.core.config import get_settings
from app.core.logging import get_logger

router = APIRouter(tags=["Trading Engine"])
settings = get_settings()
logger = get_logger(__name__)

# Global instances (in production, use dependency injection)
_nobitex_client: Optional[NobitexClient] = None
_order_manager: Optional[OrderManager] = None
_portfolio_manager: Optional[PortfolioManager] = None


async def get_nobitex_client() -> NobitexClient:
    global _nobitex_client
    if _nobitex_client is None:
        # Get API key from vault
        import os
        import json
        CONFIG_FILE = os.path.expanduser("~/.aark/nobitex.vault")
        api_key = ""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE) as f:
                    api_key = json.load(f).get("api_key", "")
            except Exception:
                pass
        if not api_key:
            raise HTTPException(status_code=400, detail="Nobitex API key not configured")
        _nobitex_client = NobitexClient(api_key=api_key, base_url=settings.NOBITEX_API_BASE)
    return _nobitex_client


async def get_order_manager(client: NobitexClient = Depends(get_nobitex_client)) -> OrderManager:
    global _order_manager
    if _order_manager is None:
        _order_manager = OrderManager(client)
    return _order_manager


async def get_portfolio_manager(client: NobitexClient = Depends(get_nobitex_client)) -> PortfolioManager:
    global _portfolio_manager
    if _portfolio_manager is None:
        _portfolio_manager = PortfolioManager(client)
    return _portfolio_manager


class PlaceOrderRequest(BaseModel):
    symbol: str = Field(..., description="Trading symbol (e.g., BTCUSDT)")
    side: str = Field(..., description="buy or sell")
    order_type: str = Field(..., description="market, limit, stop, stop_limit")
    quantity: float = Field(..., gt=0, description="Order quantity")
    price: Optional[float] = Field(None, description="Limit price (required for limit orders)")
    stop_price: Optional[float] = Field(None, description="Stop price (required for stop orders)")
    client_order_id: Optional[str] = Field(None, description="Client-defined order ID")


class PlaceOrderResponse(BaseModel):
    order_id: str
    client_order_id: Optional[str]
    symbol: str
    side: str
    order_type: str
    quantity: float
    price: Optional[float]
    status: str
    filled_quantity: float
    avg_fill_price: Optional[float]
    error: Optional[str] = None


class OrderResponseModel(BaseModel):
    order_id: str
    client_order_id: Optional[str]
    symbol: str
    side: str
    order_type: str
    quantity: float
    price: Optional[float]
    status: str
    filled_quantity: float
    avg_fill_price: Optional[float]
    commission: float
    timestamp: datetime


@router.post("/orders", response_model=PlaceOrderResponse)
async def place_order(
    request: PlaceOrderRequest,
    manager: OrderManager = Depends(get_order_manager),
) -> PlaceOrderResponse:
    try:
        side = OrderSide(request.side.lower())
        order_type = OrderType(request.order_type.lower())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid order parameter: {e}")

    order_request = OrderRequest(
        symbol=request.symbol,
        side=side,
        order_type=order_type,
        quantity=Decimal(str(request.quantity)),
        price=Decimal(str(request.price)) if request.price else None,
        stop_price=Decimal(str(request.stop_price)) if request.stop_price else None,
        client_order_id=request.client_order_id,
    )

    response = await manager.submit_order(order_request)

    return PlaceOrderResponse(
        order_id=response.order_id,
        client_order_id=response.client_order_id,
        symbol=response.symbol,
        side=response.side.value,
        order_type=response.order_type.value,
        quantity=float(response.quantity),
        price=float(response.price) if response.price else None,
        status=response.status.value,
        filled_quantity=float(response.filled_quantity),
        avg_fill_price=float(response.avg_fill_price) if response.avg_fill_price else None,
        error=response.error,
    )


@router.delete("/orders/{order_id}")
async def cancel_order(
    order_id: str,
    manager: OrderManager = Depends(get_order_manager),
) -> Dict[str, Any]:
    success = await manager.cancel_order(order_id)
    if not success:
        raise HTTPException(status_code=404, detail="Order not found or cannot be cancelled")
    return {"status": "cancelled", "order_id": order_id}


@router.get("/orders/{order_id}", response_model=OrderResponseModel)
async def get_order(
    order_id: str,
    manager: OrderManager = Depends(get_order_manager),
) -> OrderResponseModel:
    order = await manager.refresh_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return OrderResponseModel(
        order_id=order.order_id,
        client_order_id=order.client_order_id,
        symbol=order.symbol,
        side=order.side.value,
        order_type=order.order_type.value,
        quantity=float(order.quantity),
        price=float(order.price) if order.price else None,
        status=order.status.value,
        filled_quantity=float(order.filled_quantity),
        avg_fill_price=float(order.avg_fill_price) if order.avg_fill_price else None,
        commission=float(order.commission),
        timestamp=order.timestamp,
    )


@router.get("/orders", response_model=List[OrderResponseModel])
async def list_orders(
    symbol: Optional[str] = None,
    manager: OrderManager = Depends(get_order_manager),
) -> List[OrderResponseModel]:
    orders = await manager.refresh_all()
    if symbol:
        orders = [o for o in orders if o.symbol == symbol]
    return [
        OrderResponseModel(
            order_id=o.order_id,
            client_order_id=o.client_order_id,
            symbol=o.symbol,
            side=o.side.value,
            order_type=o.order_type.value,
            quantity=float(o.quantity),
            price=float(o.price) if o.price else None,
            status=o.status.value,
            filled_quantity=float(o.filled_quantity),
            avg_fill_price=float(o.avg_fill_price) if o.avg_fill_price else None,
            commission=float(o.commission),
            timestamp=o.timestamp,
        )
        for o in orders
    ]


@router.get("/portfolio/balances", response_model=List[Dict[str, Any]])
async def get_balances(
    manager: PortfolioManager = Depends(get_portfolio_manager),
) -> List[Dict[str, Any]]:
    await manager.refresh_balances()
    return [
        {
            "asset": b.asset,
            "free": float(b.free),
            "locked": float(b.locked),
            "total": float(b.total),
        }
        for b in manager.balances.values()
    ]


@router.get("/portfolio/positions", response_model=List[Dict[str, Any]])
async def get_positions(
    manager: PortfolioManager = Depends(get_portfolio_manager),
) -> List[Dict[str, Any]]:
    await manager.refresh_positions()
    return [
        {
            "symbol": p.symbol,
            "side": p.side,
            "quantity": float(p.quantity),
            "entry_price": float(p.entry_price),
            "mark_price": float(p.mark_price),
            "unrealized_pnl": float(p.unrealized_pnl),
            "realized_pnl": float(p.realized_pnl),
            "leverage": float(p.leverage),
            "liquidation_price": float(p.liquidation_price) if p.liquidation_price else None,
            "margin_used": float(p.margin_used),
        }
        for p in manager.positions.values()
    ]


@router.get("/portfolio/pnl")
async def get_pnl(
    manager: PortfolioManager = Depends(get_portfolio_manager),
) -> Dict[str, Any]:
    pnl = manager.get_pnl_summary()
    return {
        "unrealized_pnl": float(pnl["unrealized_pnl"]),
        "realized_pnl": float(pnl["realized_pnl"]),
        "total_pnl": float(pnl["total_pnl"]),
    }


@router.get("/portfolio/value")
async def get_portfolio_value(
    manager: PortfolioManager = Depends(get_portfolio_manager),
) -> Dict[str, Any]:
    await manager.refresh_balances()
    # Get prices for all non-IRT assets
    prices = {}
    client = manager.client
    for asset in manager.balances:
        if asset != "IRT":
            try:
                ticker = await client.get_ticker(f"{asset}USDT")
                # Extract price from ticker
                prices[f"{asset}IRT"] = Decimal("0")  # Placeholder
            except Exception:
                pass

    total = await manager.get_total_portfolio_value(prices)
    return {"total_value_irt": float(total), "breakdown": {}}


@router.post("/orders/batch")
async def place_batch_orders(
    orders: List[PlaceOrderRequest],
    background_tasks: BackgroundTasks,
    manager: OrderManager = Depends(get_order_manager),
) -> Dict[str, Any]:
    results = []
    for req in orders:
        try:
            side = OrderSide(req.side.lower())
            order_type = OrderType(req.order_type.lower())
            order_request = OrderRequest(
                symbol=req.symbol,
                side=side,
                order_type=order_type,
                quantity=Decimal(str(req.quantity)),
                price=Decimal(str(req.price)) if req.price else None,
                stop_price=Decimal(str(req.stop_price)) if req.stop_price else None,
                client_order_id=req.client_order_id,
            )
            response = await manager.submit_order(order_request)
            results.append({
                "client_order_id": req.client_order_id,
                "order_id": response.order_id,
                "status": response.status.value,
                "error": response.error,
            })
        except Exception as e:
            results.append({
                "client_order_id": req.client_order_id,
                "order_id": None,
                "status": "failed",
                "error": str(e),
            })
    return {"results": results}