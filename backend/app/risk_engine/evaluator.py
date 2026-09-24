from dataclasses import dataclass


@dataclass(frozen=True)
class RiskProfile:
    max_portfolio_allocation_irt: float = 10_000_000.0  # سقف کل موجودی مجاز: ۱۰ میلیون تومان
    max_single_trade_pct: float = 0.20  # حداکثر ۲۰٪ کل موجودی در هر تصمیم (۲ میلیون تومان)
    max_daily_loss_pct: float = 0.015   # ۱.۵٪ حد ضرر روزانه

class DeterministicRiskEngine:
    @staticmethod
    def validate_order(profile: RiskProfile, current_balance_irt: float, requested_amount_irt: float) -> tuple[bool, str]:
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
