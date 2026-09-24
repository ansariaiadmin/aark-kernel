from typing import Any

import numpy as np
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.logging import get_logger
from app.risk_engine.advanced import (
    AdvancedRiskEngine,
    DeterministicRiskEngine,
    RiskLevel,
    RiskProfile,
)

router = APIRouter(tags=["Advanced Risk Management"])
settings = get_settings()
logger = get_logger(__name__)

# Global risk engine instance
_risk_engine: AdvancedRiskEngine | None = None


def get_risk_engine() -> AdvancedRiskEngine:
    global _risk_engine
    if _risk_engine is None:
        _risk_engine = AdvancedRiskEngine(
            max_portfolio_value=settings.MAX_PORTFOLIO_ALLOCATION_IRT,
            max_single_position_pct=settings.MAX_SINGLE_TRADE_PCT,
            max_daily_loss_pct=settings.MAX_DAILY_LOSS_PCT,
        )
    return _risk_engine


class VaRResponse(BaseModel):
    var_95: float
    var_99: float
    cvar_95: float
    cvar_99: float
    confidence_level: float
    method: str
    timestamp: str


class StressTestResponse(BaseModel):
    scenario_name: str
    portfolio_value_before: float
    portfolio_value_after: float
    pnl_impact: float
    pnl_pct: float
    risk_level: str
    details: dict[str, float]


class CorrelationResponse(BaseModel):
    symbol_pairs: dict[str, float]
    max_correlation: float
    avg_correlation: float
    high_correlation_pairs: list[dict[str, Any]]
    concentration_risk: float


class RiskMetricsResponse(BaseModel):
    metrics: list[dict[str, Any]]
    overall_level: str
    timestamp: str


class PositionSizeRequest(BaseModel):
    symbol: str
    signal_strength: float = Field(..., ge=0, le=1)
    volatility: float = Field(..., gt=0)
    portfolio_value: float = Field(..., gt=0)
    current_positions: dict[str, float] = Field(default_factory=dict)
    prices: dict[str, float] = Field(default_factory=dict)
    max_risk_per_trade: float = Field(0.02, gt=0, le=0.1)


class PositionSizeResponse(BaseModel):
    recommended_size: float
    risk_budget_used: float
    volatility_adjusted_size: float
    signal_adjusted_size: float


@router.get("/var", response_model=VaRResponse)
async def get_var(
    method: str = Query("historical", enum=["historical", "parametric", "monte_carlo"]),
    confidence: float = Query(0.95, ge=0.9, le=0.999),
    portfolio_value: float = Query(..., gt=0),
    engine: AdvancedRiskEngine = Depends(get_risk_engine),
) -> VaRResponse:
    """Calculate Value at Risk using specified method."""
    # In production, fetch actual returns from database
    # For now, generate sample returns
    import numpy as np
    returns = np.random.normal(0.0005, 0.02, 252)  # Sample daily returns

    if method == "historical":
        result = engine.calculate_var_historical(returns, portfolio_value, confidence)
    elif method == "parametric":
        result = engine.calculate_var_parametric(returns, portfolio_value, confidence)
    else:
        result = engine.calculate_var_monte_carlo(returns, portfolio_value, confidence)

    return VaRResponse(
        var_95=result.var_95,
        var_99=result.var_99,
        cvar_95=result.cvar_95,
        cvar_99=result.cvar_99,
        confidence_level=result.confidence_level,
        method=result.method,
        timestamp=result.timestamp.isoformat(),
    )


@router.post("/stress-test", response_model=list[StressTestResponse])
async def run_stress_test(
    positions: dict[str, float],
    prices: dict[str, float],
    scenarios: dict[str, dict[str, float]] | None = None,
    engine: AdvancedRiskEngine = Depends(get_risk_engine),
) -> list[StressTestResponse]:
    """Run portfolio stress tests against defined scenarios."""
    results = engine.run_stress_tests(positions, prices, scenarios)
    return [
        StressTestResponse(
            scenario_name=r.scenario_name,
            portfolio_value_before=r.portfolio_value_before,
            portfolio_value_after=r.portfolio_value_after,
            pnl_impact=r.pnl_impact,
            pnl_pct=r.pnl_pct,
            risk_level=r.risk_level.value,
            details=r.details,
        )
        for r in results
    ]


@router.get("/correlation", response_model=CorrelationResponse)
async def get_correlation_risk(
    symbols: list[str] = Query(..., min_length=2),
    lookback_days: int = Query(252, ge=30, le=756),
    engine: AdvancedRiskEngine = Depends(get_risk_engine),
) -> CorrelationResponse:
    """Analyze correlation risk across positions."""
    # In production, fetch actual returns from market data service
    import numpy as np
    returns_data = {s: np.random.normal(0, 0.02, lookback_days) for s in symbols}

    result = engine.analyze_correlation(returns_data)

    return CorrelationResponse(
        symbol_pairs={f"{a}-{b}": v for (a, b), v in result.symbol_pairs.items()},
        max_correlation=result.max_correlation,
        avg_correlation=result.avg_correlation,
        high_correlation_pairs=[
            {"symbol_a": a, "symbol_b": b, "correlation": c}
            for a, b, c in result.high_correlation_pairs
        ],
        concentration_risk=result.concentration_risk,
    )


@router.post("/validate", response_model=RiskMetricsResponse)
async def validate_portfolio_risk(
    positions: dict[str, float],
    prices: dict[str, float],
    daily_pnl: float,
    portfolio_value: float,
    returns_history: dict[str, list[float]] | None = None,
    engine: AdvancedRiskEngine = Depends(get_risk_engine),
) -> RiskMetricsResponse:
    """Comprehensive portfolio risk validation."""
    # Convert returns history to numpy arrays
    np_returns = {}
    if returns_history:
        import numpy as np
        np_returns = {k: np.array(v) for k, v in returns_history.items()}

    metrics = engine.validate_portfolio_risk(
        positions=positions,
        prices=prices,
        daily_pnl=daily_pnl,
        portfolio_value=portfolio_value,
        returns_history=np_returns if np_returns else None,
    )

    # Determine overall risk level
    levels = [m.level for m in metrics]
    if RiskLevel.CRITICAL in levels:
        overall = RiskLevel.CRITICAL
    elif RiskLevel.HIGH in levels:
        overall = RiskLevel.HIGH
    elif RiskLevel.MEDIUM in levels:
        overall = RiskLevel.MEDIUM
    else:
        overall = RiskLevel.LOW

    return RiskMetricsResponse(
        metrics=[
            {
                "name": m.name,
                "value": m.value,
                "threshold": m.threshold,
                "level": m.level.value,
                "description": m.description,
            }
            for m in metrics
        ],
        overall_level=overall.value,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.post("/position-size", response_model=PositionSizeResponse)
async def calculate_position_size(
    request: PositionSizeRequest,
    engine: AdvancedRiskEngine = Depends(get_risk_engine),
) -> PositionSizeResponse:
    """Calculate dynamic position size based on risk parameters."""
    size = engine.calculate_dynamic_position_size(
        symbol=request.symbol,
        signal_strength=request.signal_strength,
        volatility=request.volatility,
        portfolio_value=request.portfolio_value,
        current_positions=request.current_positions,
        prices=request.prices,
        max_risk_per_trade=request.max_risk_per_trade,
    )

    # Calculate components for transparency
    risk_budget = request.portfolio_value * request.max_risk_per_trade
    daily_vol = request.volatility * np.sqrt(1/252) if 'np' in globals() else request.volatility * 0.063
    vol_adjusted = risk_budget / max(daily_vol, 0.001)
    signal_adjusted = vol_adjusted * request.signal_strength

    return PositionSizeResponse(
        recommended_size=size,
        risk_budget_used=size / request.portfolio_value if request.portfolio_value > 0 else 0,
        volatility_adjusted_size=vol_adjusted,
        signal_adjusted_size=signal_adjusted,
    )


@router.get("/summary")
async def get_risk_summary(
    engine: AdvancedRiskEngine = Depends(get_risk_engine),
) -> dict[str, Any]:
    """Get current risk engine configuration and state."""
    return engine.get_risk_summary()


@router.post("/legacy/validate")
async def legacy_validate_order(
    current_balance_irt: float,
    requested_amount_irt: float,
) -> dict[str, Any]:
    """Backward compatible risk validation endpoint."""
    profile = RiskProfile(
        max_portfolio_allocation_irt=settings.MAX_PORTFOLIO_ALLOCATION_IRT,
        max_single_trade_pct=settings.MAX_SINGLE_TRADE_PCT,
        max_daily_loss_pct=settings.MAX_DAILY_LOSS_PCT,
    )
    approved, message = DeterministicRiskEngine.validate_order(profile, current_balance_irt, requested_amount_irt)
    return {"approved": approved, "message": message}


from datetime import datetime, timezone