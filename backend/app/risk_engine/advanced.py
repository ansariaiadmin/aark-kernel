from typing import Dict, List, Optional, Tuple, Any
from decimal import Decimal
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import numpy as np
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RiskMetric:
    name: str
    value: float
    threshold: float
    level: RiskLevel
    description: str


@dataclass
class VaRResult:
    var_95: float
    var_99: float
    cvar_95: float  # Conditional VaR (Expected Shortfall)
    cvar_99: float
    confidence_level: float
    method: str
    timestamp: datetime


@dataclass
class StressTestResult:
    scenario_name: str
    portfolio_value_before: float
    portfolio_value_after: float
    pnl_impact: float
    pnl_pct: float
    risk_level: RiskLevel
    details: Dict[str, float]


@dataclass
class CorrelationRisk:
    symbol_pairs: Dict[Tuple[str, str], float]
    max_correlation: float
    avg_correlation: float
    high_correlation_pairs: List[Tuple[str, str, float]]
    concentration_risk: float


class AdvancedRiskEngine:
    """
    Advanced risk management engine with:
    - Historical VaR / Parametric VaR / Monte Carlo VaR
    - Expected Shortfall (CVaR)
    - Stress testing scenarios
    - Correlation analysis
    - Dynamic position sizing
    - Risk budgeting
    """

    def __init__(
        self,
        max_portfolio_value: float = 10_000_000,
        max_single_position_pct: float = 0.20,
        max_daily_loss_pct: float = 0.015,
        max_drawdown_pct: float = 0.10,
        max_leverage: float = 3.0,
        var_confidence: float = 0.95,
        lookback_days: int = 252,
    ):
        self.max_portfolio_value = max_portfolio_value
        self.max_single_position_pct = max_single_position_pct
        self.max_daily_loss_pct = max_daily_loss_pct
        self.max_drawdown_pct = max_drawdown_pct
        self.max_leverage = max_leverage
        self.var_confidence = var_confidence
        self.lookback_days = lookback_days

        # Risk state
        self.daily_pnl_history: List[float] = []
        self.portfolio_value_history: List[float] = []
        self.position_history: List[Dict[str, float]] = []

    def calculate_var_historical(
        self,
        returns: np.ndarray,
        portfolio_value: float,
        confidence: float = 0.95,
    ) -> VaRResult:
        """Calculate Historical VaR and CVaR."""
        if len(returns) < 30:
            return VaRResult(
                var_95=0, var_99=0, cvar_95=0, cvar_99=0,
                confidence_level=confidence, method="historical", timestamp=datetime.utcnow()
            )

        var_95 = np.percentile(returns, (1 - 0.95) * 100) * portfolio_value
        var_99 = np.percentile(returns, (1 - 0.99) * 100) * portfolio_value
        cvar_95 = returns[returns <= np.percentile(returns, (1 - 0.95) * 100)].mean() * portfolio_value
        cvar_99 = returns[returns <= np.percentile(returns, (1 - 0.99) * 100)].mean() * portfolio_value

        return VaRResult(
            var_95=abs(var_95),
            var_99=abs(var_99),
            cvar_95=abs(cvar_95),
            cvar_99=abs(cvar_99),
            confidence_level=confidence,
            method="historical",
            timestamp=datetime.utcnow(),
        )

    def calculate_var_parametric(
        self,
        returns: np.ndarray,
        portfolio_value: float,
        confidence: float = 0.95,
    ) -> VaRResult:
        """Calculate Parametric VaR assuming normal distribution."""
        if len(returns) < 30:
            return VaRResult(
                var_95=0, var_99=0, cvar_95=0, cvar_99=0,
                confidence_level=confidence, method="parametric", timestamp=datetime.utcnow()
            )

        mean = np.mean(returns)
        std = np.std(returns)
        from scipy import stats

        z_95 = stats.norm.ppf(1 - 0.95)
        z_99 = stats.norm.ppf(1 - 0.99)

        var_95 = abs((mean + z_95 * std) * portfolio_value)
        var_99 = abs((mean + z_99 * std) * portfolio_value)

        # CVaR for normal distribution
        cvar_95 = abs((mean - std * stats.norm.pdf(z_95) / 0.05) * portfolio_value)
        cvar_99 = abs((mean - std * stats.norm.pdf(z_99) / 0.01) * portfolio_value)

        return VaRResult(
            var_95=var_95,
            var_99=var_99,
            cvar_95=cvar_95,
            cvar_99=cvar_99,
            confidence_level=confidence,
            method="parametric",
            timestamp=datetime.utcnow(),
        )

    def calculate_var_monte_carlo(
        self,
        returns: np.ndarray,
        portfolio_value: float,
        confidence: float = 0.95,
        simulations: int = 10000,
    ) -> VaRResult:
        """Calculate Monte Carlo VaR."""
        if len(returns) < 30:
            return VaRResult(
                var_95=0, var_99=0, cvar_95=0, cvar_99=0,
                confidence_level=confidence, method="monte_carlo", timestamp=datetime.utcnow()
            )

        mean = np.mean(returns)
        std = np.std(returns)
        simulated_returns = np.random.normal(mean, std, simulations)

        var_95 = np.percentile(simulated_returns, (1 - 0.95) * 100) * portfolio_value
        var_99 = np.percentile(simulated_returns, (1 - 0.99) * 100) * portfolio_value
        cvar_95 = simulated_returns[simulated_returns <= np.percentile(simulated_returns, (1 - 0.95) * 100)].mean() * portfolio_value
        cvar_99 = simulated_returns[simulated_returns <= np.percentile(simulated_returns, (1 - 0.99) * 100)].mean() * portfolio_value

        return VaRResult(
            var_95=abs(var_95),
            var_99=abs(var_99),
            cvar_95=abs(cvar_95),
            cvar_99=abs(cvar_99),
            confidence_level=confidence,
            method="monte_carlo",
            timestamp=datetime.utcnow(),
        )

    def run_stress_tests(
        self,
        positions: Dict[str, float],  # symbol -> quantity
        prices: Dict[str, float],      # symbol -> current price
        scenarios: Optional[Dict[str, Dict[str, float]]] = None,
    ) -> List[StressTestResult]:
        """Run portfolio stress tests against defined scenarios."""
        if scenarios is None:
            scenarios = self._get_default_scenarios()

        portfolio_value = sum(positions.get(s, 0) * prices.get(s, 0) for s in positions)
        results = []

        for scenario_name, shocks in scenarios.items():
            stressed_value = 0
            details = {}

            for symbol, quantity in positions.items():
                current_price = prices.get(symbol, 0)
                shock = shocks.get(symbol, shocks.get("DEFAULT", 0))
                stressed_price = current_price * (1 + shock)
                position_value = quantity * stressed_price
                stressed_value += position_value
                details[symbol] = position_value

            pnl_impact = stressed_value - portfolio_value
            pnl_pct = pnl_impact / portfolio_value if portfolio_value > 0 else 0

            if pnl_pct < -0.20:
                level = RiskLevel.CRITICAL
            elif pnl_pct < -0.10:
                level = RiskLevel.HIGH
            elif pnl_pct < -0.05:
                level = RiskLevel.MEDIUM
            else:
                level = RiskLevel.LOW

            results.append(StressTestResult(
                scenario_name=scenario_name,
                portfolio_value_before=portfolio_value,
                portfolio_value_after=stressed_value,
                pnl_impact=pnl_impact,
                pnl_pct=pnl_pct,
                risk_level=level,
                details=details,
            ))

        return results

    def _get_default_scenarios(self) -> Dict[str, Dict[str, float]]:
        """Define default stress test scenarios."""
        return {
            "market_crash": {"DEFAULT": -0.30, "BTCUSDT": -0.40, "ETHUSDT": -0.45},
            "crypto_winter": {"DEFAULT": -0.50, "BTCUSDT": -0.60, "ETHUSDT": -0.65},
            "flash_crash": {"DEFAULT": -0.15, "BTCUSDT": -0.25, "ETHUSDT": -0.30},
            "regulatory_shock": {"DEFAULT": -0.20, "BTCUSDT": -0.30, "ETHUSDT": -0.35},
            "liquidity_crisis": {"DEFAULT": -0.10, "BTCUSDT": -0.15, "ETHUSDT": -0.20},
            "bull_run": {"DEFAULT": 0.50, "BTCUSDT": 0.80, "ETHUSDT": 1.00},
        }

    def analyze_correlation(
        self,
        returns_data: Dict[str, np.ndarray],  # symbol -> returns array
        threshold: float = 0.7,
    ) -> CorrelationRisk:
        """Analyze correlation risk across positions."""
        symbols = list(returns_data.keys())
        n = len(symbols)

        if n < 2:
            return CorrelationRisk(
                symbol_pairs={},
                max_correlation=0,
                avg_correlation=0,
                high_correlation_pairs=[],
                concentration_risk=0,
            )

        # Build correlation matrix
        returns_matrix = np.array([returns_data[s] for s in symbols])
        min_len = min(len(r) for r in returns_matrix)
        returns_matrix = returns_matrix[:, -min_len:]

        corr_matrix = np.corrcoef(returns_matrix)

        symbol_pairs = {}
        high_corr_pairs = []
        correlations = []

        for i in range(n):
            for j in range(i + 1, n):
                corr = corr_matrix[i, j]
                pair = (symbols[i], symbols[j])
                symbol_pairs[pair] = float(corr)
                correlations.append(abs(corr))
                if abs(corr) >= threshold:
                    high_corr_pairs.append((symbols[i], symbols[j], float(corr)))

        # Concentration risk: Herfindahl-Hirschman Index of position weights
        position_values = np.array([np.abs(np.mean(returns_data[s])) for s in symbols])
        if position_values.sum() > 0:
            weights = position_values / position_values.sum()
            concentration = np.sum(weights ** 2)
        else:
            concentration = 0

        return CorrelationRisk(
            symbol_pairs=symbol_pairs,
            max_correlation=float(np.max(np.abs(corr_matrix - np.eye(n)))) if n > 1 else 0,
            avg_correlation=float(np.mean(correlations)) if correlations else 0,
            high_correlation_pairs=high_corr_pairs,
            concentration_risk=float(concentration),
        )

    def calculate_dynamic_position_size(
        self,
        symbol: str,
        signal_strength: float,  # 0 to 1
        volatility: float,       # Annualized volatility
        portfolio_value: float,
        current_positions: Dict[str, float],
        prices: Dict[str, float],
        max_risk_per_trade: float = 0.02,  # 2% risk per trade
    ) -> float:
        """Calculate position size based on volatility targeting and risk parity."""
        # Volatility targeting: position size inversely proportional to volatility
        target_vol = 0.15  # 15% annual target portfolio vol
        position_vol_target = target_vol / max(volatility, 0.01)

        # Risk-based sizing
        risk_budget = portfolio_value * max_risk_per_trade
        position_size_risk = risk_budget / (volatility * np.sqrt(1/252))  # Daily vol

        # Signal adjustment
        signal_adjusted = position_size_risk * signal_strength

        # Portfolio-level constraints
        current_exposure = sum(
            abs(current_positions.get(s, 0) * prices.get(s, 0))
            for s in current_positions
        )
        remaining_capacity = portfolio_value * self.max_single_position_pct - current_exposure

        # Final size
        final_size = min(signal_adjusted, position_vol_target * portfolio_value, remaining_capacity)
        return max(0, final_size)

    def validate_portfolio_risk(
        self,
        positions: Dict[str, float],
        prices: Dict[str, float],
        daily_pnl: float,
        portfolio_value: float,
        returns_history: Optional[Dict[str, np.ndarray]] = None,
    ) -> List[RiskMetric]:
        """Comprehensive portfolio risk validation."""
        metrics = []

        # 1. Portfolio value check
        current_value = sum(positions.get(s, 0) * prices.get(s, 0) for s in positions)
        value_pct = current_value / self.max_portfolio_value if self.max_portfolio_value > 0 else 0
        metrics.append(RiskMetric(
            name="portfolio_value",
            value=current_value,
            threshold=self.max_portfolio_value,
            level=RiskLevel.CRITICAL if value_pct > 1.0 else RiskLevel.HIGH if value_pct > 0.9 else RiskLevel.LOW,
            description=f"Portfolio value: {current_value:,.0f} / {self.max_portfolio_value:,.0f}",
        ))

        # 2. Single position concentration
        for symbol, qty in positions.items():
            pos_value = abs(qty * prices.get(symbol, 0))
            pos_pct = pos_value / current_value if current_value > 0 else 0
            if pos_pct > self.max_single_position_pct:
                metrics.append(RiskMetric(
                    name=f"concentration_{symbol}",
                    value=pos_pct,
                    threshold=self.max_single_position_pct,
                    level=RiskLevel.CRITICAL,
                    description=f"Position {symbol} exceeds {self.max_single_position_pct*100:.0f}% limit: {pos_pct*100:.1f}%",
                ))

        # 3. Daily loss limit
        daily_loss_pct = abs(daily_pnl) / portfolio_value if portfolio_value > 0 else 0
        metrics.append(RiskMetric(
            name="daily_loss",
            value=daily_loss_pct,
            threshold=self.max_daily_loss_pct,
            level=RiskLevel.CRITICAL if daily_loss_pct > self.max_daily_loss_pct else RiskLevel.HIGH if daily_loss_pct > self.max_daily_loss_pct * 0.8 else RiskLevel.LOW,
            description=f"Daily PnL: {daily_pnl:,.0f} ({daily_loss_pct*100:.2f}%)",
        ))

        # 4. Drawdown check
        if self.portfolio_value_history:
            peak = max(self.portfolio_value_history)
            current = self.portfolio_value_history[-1] if self.portfolio_value_history else portfolio_value
            drawdown = (peak - current) / peak if peak > 0 else 0
            metrics.append(RiskMetric(
                name="max_drawdown",
                value=drawdown,
                threshold=self.max_drawdown_pct,
                level=RiskLevel.CRITICAL if drawdown > self.max_drawdown_pct else RiskLevel.HIGH if drawdown > self.max_drawdown_pct * 0.8 else RiskLevel.LOW,
                description=f"Current drawdown: {drawdown*100:.2f}%",
            ))

        # 5. Leverage check
        total_exposure = sum(abs(qty * prices.get(s, 0)) for s, qty in positions.items())
        leverage = total_exposure / portfolio_value if portfolio_value > 0 else 0
        metrics.append(RiskMetric(
            name="leverage",
            value=leverage,
            threshold=self.max_leverage,
            level=RiskLevel.CRITICAL if leverage > self.max_leverage else RiskLevel.HIGH if leverage > self.max_leverage * 0.8 else RiskLevel.LOW,
            description=f"Portfolio leverage: {leverage:.2f}x",
        ))

        # 6. VaR check (if returns history available)
        if returns_history:
            # Aggregate portfolio returns
            all_returns = []
            for symbol, qty in positions.items():
                if symbol in returns_history:
                    pos_returns = returns_history[symbol] * (qty * prices.get(symbol, 0))
                    all_returns.append(pos_returns)
            if all_returns:
                portfolio_returns = np.sum(all_returns, axis=0) / portfolio_value
                var_result = self.calculate_var_historical(portfolio_returns, portfolio_value)
                var_pct = var_result.var_95 / portfolio_value
                metrics.append(RiskMetric(
                    name="var_95",
                    value=var_pct,
                    threshold=0.05,  # 5% VaR limit
                    level=RiskLevel.HIGH if var_pct > 0.05 else RiskLevel.MEDIUM if var_pct > 0.03 else RiskLevel.LOW,
                    description=f"VaR 95%: {var_result.var_95:,.0f} ({var_pct*100:.2f}%)",
                ))

        return metrics

    def update_history(self, portfolio_value: float, daily_pnl: float, positions: Dict[str, float]) -> None:
        """Update internal history for risk calculations."""
        self.portfolio_value_history.append(portfolio_value)
        self.daily_pnl_history.append(daily_pnl)
        self.position_history.append(positions.copy())

        # Trim history
        max_len = self.lookback_days
        if len(self.portfolio_value_history) > max_len:
            self.portfolio_value_history = self.portfolio_value_history[-max_len:]
        if len(self.daily_pnl_history) > max_len:
            self.daily_pnl_history = self.daily_pnl_history[-max_len:]
        if len(self.position_history) > max_len:
            self.position_history = self.position_history[-max_len:]

    def get_risk_summary(self) -> Dict[str, Any]:
        """Get current risk summary."""
        return {
            "max_portfolio_value": self.max_portfolio_value,
            "max_single_position_pct": self.max_single_position_pct,
            "max_daily_loss_pct": self.max_daily_loss_pct,
            "max_drawdown_pct": self.max_drawdown_pct,
            "max_leverage": self.max_leverage,
            "var_confidence": self.var_confidence,
            "lookback_days": self.lookback_days,
            "history_length": len(self.portfolio_value_history),
        }


# Backward compatibility with existing DeterministicRiskEngine
class DeterministicRiskEngine:
    @staticmethod
    def validate_order(profile, current_balance_irt: float, requested_amount_irt: float) -> Tuple[bool, str]:
        if requested_amount_irt < 0:
            return False, "REJECTED: Amount cannot be negative."

        if current_balance_irt > profile.max_portfolio_allocation_irt:
            return False, f"REJECTED: Wallet balance ({current_balance_irt:,.0f} IRT) exceeds hard ceiling limit of {profile.max_portfolio_allocation_irt:,.0f} IRT."

        if requested_amount_irt > current_balance_irt:
            return False, f"REJECTED: Requested amount ({requested_amount_irt:,.0f} IRT) exceeds available balance ({current_balance_irt:,.0f} IRT)."

        max_allowed_single_order = current_balance_irt * profile.max_single_trade_pct
        if requested_amount_irt > max_allowed_single_order:
            return False, f"REJECTED: Requested amount ({requested_amount_irt:,.0f} IRT) exceeds single-order risk boundary of 20% ({max_allowed_single_order:,.0f} IRT)."

        return True, f"APPROVED: Order of {requested_amount_irt:,.0f} IRT is fully compliant with dynamic risk boundaries."


@dataclass(frozen=True)
class RiskProfile:
    max_portfolio_allocation_irt: float = 10_000_000.0
    max_single_trade_pct: float = 0.20
    max_daily_loss_pct: float = 0.015