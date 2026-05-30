import numpy as np
from valuation.models import CheckResult
from valuation.technicals import get_technical_signals
from valuation.helpers import safe_get, format_pct, format_multiple
import valuation.eval_config as cfg


def _get_stmt_row(df, *labels):
    if df is None or (hasattr(df, "empty") and df.empty):
        return None
    for label in labels:
        if label in df.index:
            vals = df.loc[label].dropna()
            if not vals.empty:
                return vals
    return None


def run(data) -> list[CheckResult]:
    info = data.get_info()
    fin = data.get_financials()
    hist = data.get_history("5y")
    analyst = data.get_analyst_targets()
    checks = []

    price = safe_get(info, "currentPrice") or safe_get(info, "regularMarketPrice")
    cf = fin.get("cashflow")

    # ── EARNINGS-BASED ────────────────────────────────────────────────────

    # 1. Forward P/E × Forward EPS Price Target
    forward_pe = safe_get(info, "forwardPE")
    forward_eps = safe_get(info, "forwardEps")
    if forward_pe and forward_eps and price:
        fair_price_pe = forward_eps * forward_pe
        upside = (fair_price_pe / price - 1) if price > 0 else None
        if upside and upside >= 0.20:
            st, sc = "green", 1.0
        elif upside and upside >= 0:
            st, sc = "yellow", 0.5
        else:
            st, sc = "red", 0.0
        checks.append(CheckResult(
            name="Earnings-Based Price Target",
            value=f"{fair_price_pe:.2f}",
            benchmark=f"Forward P/E ({forward_pe:.1f}x) × Forward EPS ({forward_eps:.2f})",
            status=st, score=sc,
            note=f"Earnings-based target: {fair_price_pe:.2f} ({format_pct(upside)} upside)",
        ))
    else:
        checks.append(CheckResult(
            name="Earnings-Based Price Target",
            benchmark="Forward P/E × Forward EPS",
            status="na", note="Forward P/E or EPS not available",
        ))

    # 2. EPS Growth Forecast
    growth_est = safe_get(info, "earningsGrowth")
    if growth_est is not None:
        if growth_est >= 0.15:
            st, sc = "green", 1.0
        elif growth_est >= 0.05:
            st, sc = "yellow", 0.5
        else:
            st, sc = "red", 0.0
        checks.append(CheckResult(
            name="EPS Growth Forecast",
            value=format_pct(growth_est),
            benchmark="Green ≥ 15%, Yellow ≥ 5%",
            status=st, score=sc,
            note=f"Forward EPS growth estimate: {format_pct(growth_est)}",
        ))
    else:
        checks.append(CheckResult(
            name="EPS Growth Forecast",
            benchmark="Green ≥ 15%",
            status="na", note="EPS growth forecast not available",
        ))

    # 3. Fair Value P/E (PEG=1 method: fair P/E = growth %)
    peg = safe_get(info, "pegRatio")
    current_pe = safe_get(info, "trailingPE")
    growth_rate = safe_get(info, "earningsGrowth")
    if growth_rate and growth_rate > 0 and current_pe and price:
        fair_pe_peg = growth_rate * 100  # PEG=1 → P/E = growth%
        fair_price_peg = safe_get(info, "trailingEps", 0) * fair_pe_peg
        if fair_price_peg > 0 and price > 0:
            upside_peg = (fair_price_peg / price - 1)
            if upside_peg >= 0.15:
                st, sc = "green", 1.0
            elif upside_peg >= 0:
                st, sc = "yellow", 0.5
            else:
                st, sc = "red", 0.0
            checks.append(CheckResult(
                name="Fair Value P/E (PEG=1)",
                value=f"{fair_pe_peg:.1f}x",
                benchmark=f"Fair P/E = growth% = {fair_pe_peg:.1f}x (PEG=1)",
                status=st, score=sc,
                note=f"PEG=1 fair price: {fair_price_peg:.2f} ({format_pct(upside_peg)} upside)",
            ))
        else:
            checks.append(CheckResult(
                name="Fair Value P/E (PEG=1)",
                benchmark="Fair P/E = earnings growth %",
                status="na", note="EPS too low for PEG fair value",
            ))
    else:
        checks.append(CheckResult(
            name="Fair Value P/E (PEG=1)",
            benchmark="Fair P/E = earnings growth %",
            status="na", note="Growth rate or P/E not available",
        ))

    # ── CASH FLOW-BASED ───────────────────────────────────────────────────

    # 4. DCF Price Range (from already-computed DCFResult stored in session)
    # We pass the dcf result via info workaround — re-check via price comparison
    dcf_intrinsic = safe_get(info, "_dcf_intrinsic")  # injected by scorer
    if dcf_intrinsic and price and price > 0:
        upside_dcf = (dcf_intrinsic / price - 1)
        if upside_dcf >= 0.20:
            st, sc = "green", 1.0
        elif upside_dcf >= 0:
            st, sc = "yellow", 0.5
        else:
            st, sc = "red", 0.0
        checks.append(CheckResult(
            name="DCF Price Target",
            value=f"{dcf_intrinsic:.2f}",
            benchmark="Intrinsic value > current price",
            status=st, score=sc,
            note=f"DCF intrinsic: {dcf_intrinsic:.2f} ({format_pct(upside_dcf)} upside vs {price:.2f})",
        ))
    else:
        checks.append(CheckResult(
            name="DCF Price Target",
            benchmark="DCF intrinsic > current price",
            status="na", note="DCF intrinsic not available",
        ))

    # 5. FCF 3yr CAGR
    checks.append(_check_fcf_growth(cf))

    # ── MARKET-BASED ──────────────────────────────────────────────────────

    # 6. Analyst Consensus
    rec_mean = analyst.get("recommendationMean")
    n_analysts = analyst.get("numberOfAnalystOpinions", 0) or 0
    if rec_mean is not None and n_analysts > 0:
        # yfinance: 1=Strong Buy, 2=Buy, 3=Hold, 4=Sell, 5=Strong Sell
        if rec_mean <= cfg.ANALYST_CONSENSUS_GREEN:
            st, sc = "green", 1.0
            label = "Strong Buy / Buy"
        elif rec_mean <= cfg.ANALYST_CONSENSUS_YELLOW:
            st, sc = "yellow", 0.5
            label = "Hold"
        else:
            st, sc = "red", 0.0
            label = "Sell / Strong Sell"
        checks.append(CheckResult(
            name="Analyst Consensus",
            value=f"{rec_mean:.1f}/5 ({label})",
            benchmark="≤ 2.5 = Buy, ≤ 3.5 = Hold, > 3.5 = Sell",
            status=st, score=sc,
            note=f"Consensus of {n_analysts} analysts: {label}",
        ))
    else:
        checks.append(CheckResult(
            name="Analyst Consensus",
            benchmark="1=Strong Buy … 5=Strong Sell",
            status="na", note="Analyst consensus not available",
        ))

    # 7. Analyst Price Target vs Current Price
    target = analyst.get("targetMeanPrice")
    if target and price and price > 0:
        upside_analyst = (target / price - 1)
        if upside_analyst >= 0.15:
            st, sc = "green", 1.0
        elif upside_analyst >= 0:
            st, sc = "yellow", 0.5
        else:
            st, sc = "red", 0.0
        checks.append(CheckResult(
            name="Analyst Price Target",
            value=f"{target:.2f}",
            benchmark=f"Current: {price:.2f}",
            status=st, score=sc,
            note=f"Mean analyst target: {target:.2f} ({format_pct(upside_analyst)} upside)",
        ))
    else:
        checks.append(CheckResult(
            name="Analyst Price Target",
            benchmark="Mean analyst target vs current price",
            status="na", note="Analyst price target not available",
        ))

    # ── TECHNICAL ────────────────────────────────────────────────────────

    # 8. Technical Trend Composite (RSI + SMAs)
    tech = get_technical_signals(hist)
    if tech.get("status") == "na":
        checks.append(CheckResult(
            name="Technical Trend (RSI + MA)",
            benchmark="Price above 50/200 MA, RSI 30–70",
            status="na", note="Insufficient price history for technical analysis",
        ))
    else:
        rsi = tech.get("rsi_current")
        vs50 = tech.get("price_vs_50ma_pct")
        vs200 = tech.get("price_vs_200ma_pct")
        gc = tech.get("golden_cross")
        dc = tech.get("death_cross")
        parts = []
        if rsi:
            parts.append(f"RSI={rsi:.0f}")
        if vs50 is not None:
            parts.append(f"vs 50MA={vs50*100:+.1f}%")
        if vs200 is not None:
            parts.append(f"vs 200MA={vs200*100:+.1f}%")
        if gc:
            parts.append("Golden Cross")
        elif dc:
            parts.append("Death Cross")
        st = tech["status"]
        sc = 1.0 if st == "green" else (0.5 if st == "yellow" else 0.0)
        checks.append(CheckResult(
            name="Technical Trend (RSI + MA)",
            value=", ".join(parts),
            benchmark="Price above 50/200 MA, RSI not overbought",
            status=st, score=sc,
            note=", ".join(parts),
        ))

    return checks


def _check_fcf_growth(cf) -> CheckResult:
    if cf is None or (hasattr(cf, "empty") and cf.empty):
        return CheckResult(
            name="FCF Growth (3yr CAGR)",
            benchmark="Positive and growing",
            status="na", note="Cash flow data not available",
        )
    fcf_row = None
    for label in ["Free Cash Flow", "FreeCashFlow"]:
        if label in cf.index:
            fcf_row = cf.loc[label].dropna()
            break
    if fcf_row is None:
        try:
            op = cf.loc["Operating Cash Flow"].dropna()
            cap = cf.loc["Capital Expenditure"].dropna()
            fcf_row = (op + cap).dropna()
        except (KeyError, Exception):
            pass
    if fcf_row is None or len(fcf_row) < 3:
        return CheckResult(
            name="FCF Growth (3yr CAGR)",
            benchmark="Positive FCF CAGR",
            status="na", note="Insufficient years of FCF data",
        )
    recent = float(fcf_row.iloc[0])
    oldest = float(fcf_row.iloc[min(2, len(fcf_row)-1)])
    if oldest <= 0 or recent <= 0:
        return CheckResult(
            name="FCF Growth (3yr CAGR)",
            value="Negative FCF period",
            benchmark="Positive FCF CAGR",
            status="red", score=0.0,
            note="FCF was zero or negative in the period",
        )
    cagr_3yr = (recent / oldest) ** (1 / 2) - 1  # 2 gaps for 3 points
    if cagr_3yr >= 0.10:
        st, sc = "green", 1.0
    elif cagr_3yr >= 0:
        st, sc = "yellow", 0.5
    else:
        st, sc = "red", 0.0
    return CheckResult(
        name="FCF Growth (3yr CAGR)",
        value=format_pct(cagr_3yr),
        benchmark="Green ≥ 10% CAGR",
        status=st, score=sc,
        note=f"FCF 3yr CAGR: {format_pct(cagr_3yr)}",
    )
