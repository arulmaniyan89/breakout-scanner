import numpy as np
from valuation.models import DCFResult
from valuation.helpers import safe_get


def _get_fcf(fin: dict) -> float | None:
    cf = fin.get("cashflow")
    if cf is None or cf.empty:
        return None
    for label in ["Free Cash Flow", "FreeCashFlow"]:
        if label in cf.index:
            vals = cf.loc[label].dropna()
            if not vals.empty:
                return float(vals.iloc[0])
    # Fallback: Operating CF - CapEx
    try:
        op = cf.loc["Operating Cash Flow"].dropna()
        cap = cf.loc["Capital Expenditure"].dropna()
        if not op.empty and not cap.empty:
            return float(op.iloc[0]) + float(cap.iloc[0])  # capex is negative
    except (KeyError, Exception):
        pass
    return None


def _get_eps_proxy(info: dict, fin: dict) -> float | None:
    """Fallback intrinsic value using EPS × historical average P/E."""
    eps = safe_get(info, "trailingEps")
    pe = safe_get(info, "trailingPE")
    forward_pe = safe_get(info, "forwardPE")
    if eps is None or eps <= 0:
        return None
    avg_pe = None
    if pe and forward_pe and pe > 0 and forward_pe > 0:
        avg_pe = (pe + forward_pe) / 2
    elif pe and pe > 0:
        avg_pe = pe
    if avg_pe is None or avg_pe <= 0:
        avg_pe = 15.0  # conservative default
    # cap at 40× to avoid runaway
    avg_pe = min(avg_pe, 40.0)
    return eps * avg_pe


def calculate_dcf(
    info: dict,
    fin: dict,
    discount_rate: float = 0.10,
    terminal_growth: float = 0.03,
    growth_min: float = 0.03,
    growth_max: float = 0.30,
) -> DCFResult:
    shares = safe_get(info, "sharesOutstanding")
    if not shares or shares <= 0:
        return DCFResult(method="N/A")

    total_debt = safe_get(info, "totalDebt", 0) or 0
    cash = safe_get(info, "totalCash", 0) or 0
    net_debt = total_debt - cash

    base_fcf = _get_fcf(fin)
    method = "FCF"

    if base_fcf is None or base_fcf <= 0:
        # EPS-proxy path
        intrinsic = _get_eps_proxy(info, fin)
        if intrinsic is None:
            return DCFResult(method="N/A")
        growth_rate = safe_get(info, "earningsGrowth") or 0.10
        growth_rate = float(np.clip(growth_rate, growth_min, growth_max))
        return DCFResult(
            intrinsic=intrinsic,
            bull=intrinsic * (1 + growth_rate * 0.3),
            bear=intrinsic * (1 - growth_rate * 0.3),
            margin_of_safety=intrinsic * 0.80,
            growth_rate_used=growth_rate,
            method="EPS-proxy",
        )

    growth_rate = safe_get(info, "earningsGrowth") or safe_get(info, "revenueGrowth") or 0.10
    growth_rate = float(np.clip(growth_rate, growth_min, growth_max))

    def _intrinsic(g: float) -> float | None:
        try:
            pv_sum = 0.0
            for t in range(1, 11):
                fcf_t = base_fcf * (1 + g) ** t
                pv_sum += fcf_t / (1 + discount_rate) ** t
            tv = base_fcf * (1 + g) ** 10 * (1 + terminal_growth) / (discount_rate - terminal_growth)
            pv_tv = tv / (1 + discount_rate) ** 10
            ev = pv_sum + pv_tv
            equity_value = ev - net_debt
            if equity_value <= 0:
                return None
            return equity_value / shares
        except Exception:
            return None

    base = _intrinsic(growth_rate)
    bull = _intrinsic(min(growth_rate * 1.3, growth_max))
    bear = _intrinsic(max(growth_rate * 0.7, growth_min))

    if base is None:
        return DCFResult(method="N/A")

    return DCFResult(
        intrinsic=base,
        bull=bull,
        bear=bear,
        margin_of_safety=base * 0.80,
        growth_rate_used=growth_rate,
        method=method,
    )
