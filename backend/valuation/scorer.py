from valuation.models import CheckResult, StockVerdict, DCFResult, VERDICT_COLORS
from valuation.dcf import calculate_dcf
from valuation.helpers import safe_get, is_indian_stock
import valuation.val_checks as val_module
import valuation.fundamentals as fund_module
import valuation.risk as risk_module
import valuation.future_potential as future_module
import valuation.eval_config as cfg


def _score_category(checks: list[CheckResult]) -> float:
    """Average score of non-N/A checks, 0–100."""
    valid = [c for c in checks if c.status != "na"]
    if not valid:
        return 0.0
    return (sum(c.score for c in valid) / len(valid)) * 100


def evaluate(ticker: str, data, discount_rate: float = None, terminal_growth: float = None) -> StockVerdict:
    discount_rate = discount_rate or cfg.DCF_DISCOUNT_RATE
    terminal_growth = terminal_growth or cfg.DCF_TERMINAL_GROWTH

    info = data.get_info()
    if not info:
        return StockVerdict(
            ticker=ticker,
            error=f"Could not fetch data for {ticker}",
            verdict="N/A",
            verdict_color="gray",
        )

    price = safe_get(info, "currentPrice") or safe_get(info, "regularMarketPrice")
    name = safe_get(info, "longName") or safe_get(info, "shortName") or ticker
    sector = safe_get(info, "sector", "Unknown")
    industry = safe_get(info, "industry", "Unknown")
    currency = "INR" if is_indian_stock(ticker) else "USD"
    currency_symbol = "₹" if currency == "INR" else "$"

    # Run evaluation modules
    try:
        val_checks, dcf = val_module.run(data)
    except Exception as e:
        val_checks = []
        dcf = DCFResult(method="N/A")

    # Inject DCF intrinsic into future_potential so it can compare
    if dcf.intrinsic:
        info["_dcf_intrinsic"] = dcf.intrinsic

    try:
        fund_checks = fund_module.run(data)
    except Exception:
        fund_checks = []

    try:
        risk_checks = risk_module.run(data)
    except Exception:
        risk_checks = []

    try:
        fut_checks = future_module.run(data)
    except Exception:
        fut_checks = []

    checks = {
        "valuation": val_checks,
        "fundamentals": fund_checks,
        "risk": risk_checks,
        "future": fut_checks,
    }

    # Category scores
    cat_scores = {cat: _score_category(chks) for cat, chks in checks.items()}

    # Weighted overall score
    w = cfg.SCORING_WEIGHTS
    overall = (
        w["valuation"] * cat_scores["valuation"]
        + w["fundamentals"] * cat_scores["fundamentals"]
        + w["risk"] * cat_scores["risk"]
        + w["future"] * cat_scores["future"]
    )

    # Verdict
    verdict = _determine_verdict(overall, cat_scores, risk_checks)
    verdict_color = VERDICT_COLORS.get(verdict, "gray")

    # Price targets
    analyst = data.get_analyst_targets()
    target_mean = analyst.get("targetMeanPrice")
    target_low = analyst.get("targetLowPrice")
    target_high = analyst.get("targetHighPrice")

    pt_low, pt_mid, pt_high = _compute_price_targets(dcf, target_mean, target_low, target_high, price)
    upside = ((pt_mid / price) - 1) if (pt_mid and price and price > 0) else None

    return StockVerdict(
        ticker=ticker,
        company_name=name,
        current_price=price,
        currency=currency_symbol,
        sector=sector,
        industry=industry,
        category_scores=cat_scores,
        overall_score=round(overall, 1),
        verdict=verdict,
        verdict_color=verdict_color,
        price_target_low=pt_low,
        price_target_mid=pt_mid,
        price_target_high=pt_high,
        upside_pct=upside,
        dcf=dcf,
        checks=checks,
    )


def _determine_verdict(overall: float, cat_scores: dict, risk_checks: list) -> str:
    risk_score_norm = cat_scores.get("risk", 0) / 100

    # Check override rules
    debt_risk_red = any(
        c.name == "Debt Risk" and c.status == "red" for c in risk_checks
    )
    earnings_unstable = any(
        c.name == "Earnings Stability" and c.status == "red" for c in risk_checks
    )
    red_risk_count = sum(1 for c in risk_checks if c.status == "red")

    if red_risk_count >= 3:
        return "AVOID"

    if overall >= cfg.VERDICT_BUY_SCORE and risk_score_norm >= cfg.VERDICT_BUY_MIN_RISK:
        if debt_risk_red or earnings_unstable:
            return "HOLD"
        return "BUY"
    elif overall >= cfg.VERDICT_HOLD_SCORE:
        return "HOLD"
    else:
        return "AVOID"


def _compute_price_targets(
    dcf: DCFResult,
    target_mean, target_low, target_high,
    price: float | None,
) -> tuple[float | None, float | None, float | None]:
    candidates_low = []
    candidates_high = []

    if dcf.bear:
        candidates_low.append(dcf.bear)
    if target_low:
        candidates_low.append(target_low * 0.90)

    if dcf.bull:
        candidates_high.append(dcf.bull)
    if target_high:
        candidates_high.append(target_high * 1.10)

    pt_low = min(candidates_low) if candidates_low else None
    pt_high = max(candidates_high) if candidates_high else None

    # Mid from DCF base + analyst mean
    mids = []
    if dcf.intrinsic:
        mids.append(dcf.intrinsic)
    if target_mean:
        mids.append(target_mean)
    pt_mid = sum(mids) / len(mids) if mids else None

    # Fallback: if only one side available
    if pt_low is None and pt_mid:
        pt_low = pt_mid * 0.80
    if pt_high is None and pt_mid:
        pt_high = pt_mid * 1.20

    return pt_low, pt_mid, pt_high
