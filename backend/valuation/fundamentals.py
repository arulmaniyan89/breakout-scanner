import numpy as np
import pandas as pd
from valuation.models import CheckResult
from valuation.helpers import safe_get, format_pct, format_multiple
import valuation.eval_config as cfg


def _status_hi(value, green, yellow) -> tuple[str, float]:
    """Higher = better."""
    if value is None:
        return "na", 0.0
    if value >= green:
        return "green", 1.0
    elif value >= yellow:
        return "yellow", 0.5
    return "red", 0.0


def _status_lo(value, green, yellow) -> tuple[str, float]:
    """Lower = better."""
    if value is None:
        return "na", 0.0
    if value <= green:
        return "green", 1.0
    elif value <= yellow:
        return "yellow", 0.5
    return "red", 0.0


def _get_stmt_row(df, *labels):
    """Try multiple label variants and return the first non-empty Series."""
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
    checks = []

    inc = fin.get("income_stmt")
    bal = fin.get("balance_sheet")
    cf = fin.get("cashflow")

    # ── GROWTH ────────────────────────────────────────────────────────────

    # 1. Revenue Growth (YoY)
    rev_series = _get_stmt_row(inc, "Total Revenue", "Revenue")
    if rev_series is not None and len(rev_series) >= 2:
        rev_new = float(rev_series.iloc[0])
        rev_old = float(rev_series.iloc[1])
        rev_growth = (rev_new / rev_old - 1) if rev_old > 0 else None
    else:
        rev_growth = safe_get(info, "revenueGrowth")

    st, sc = _status_hi(rev_growth, cfg.REVENUE_GROWTH_GREEN, cfg.REVENUE_GROWTH_YELLOW)
    checks.append(CheckResult(
        name="Revenue Growth (YoY)",
        value=format_pct(rev_growth),
        benchmark=f"Green ≥ {cfg.REVENUE_GROWTH_GREEN*100:.0f}%",
        status=st, score=sc,
        note=f"Revenue grew {format_pct(rev_growth)} year-over-year" if rev_growth else "Revenue growth not available",
    ))

    # 2. EPS Growth (YoY)
    eps_series = _get_stmt_row(inc, "Basic EPS", "Diluted EPS", "Normalized EBITDA")
    eps_yf = safe_get(info, "trailingEps")
    eps_growth = None
    if eps_series is not None and len(eps_series) >= 2:
        e_new = float(eps_series.iloc[0])
        e_old = float(eps_series.iloc[1])
        if e_old and abs(e_old) > 0.001:
            eps_growth = (e_new / e_old - 1)
    else:
        eps_growth = safe_get(info, "earningsGrowth")

    st, sc = _status_hi(eps_growth, cfg.EPS_GROWTH_GREEN, cfg.EPS_GROWTH_YELLOW)
    checks.append(CheckResult(
        name="EPS Growth (YoY)",
        value=format_pct(eps_growth),
        benchmark=f"Green ≥ {cfg.EPS_GROWTH_GREEN*100:.0f}%",
        status=st, score=sc,
        note=f"EPS grew {format_pct(eps_growth)} year-over-year" if eps_growth else "EPS growth not available",
    ))

    # 3. Future Growth Estimates (Analyst)
    future_growth = safe_get(info, "earningsGrowth") or safe_get(info, "revenueGrowth")
    if future_growth is not None:
        st, sc = _status_hi(future_growth, 0.15, 0.05)
        checks.append(CheckResult(
            name="Future Growth Estimates",
            value=format_pct(future_growth),
            benchmark="Green ≥ 15%, Yellow ≥ 5%",
            status=st, score=sc,
            note=f"Analyst/trailing growth estimate: {format_pct(future_growth)}",
        ))
    else:
        checks.append(CheckResult(
            name="Future Growth Estimates",
            benchmark="Analyst forward growth",
            status="na", note="Forward growth estimate not available",
        ))

    # ── PROFITABILITY ──────────────────────────────────────────────────────

    # 4. Gross Margin
    gross_margin = safe_get(info, "grossMargins")
    st, sc = _status_hi(gross_margin, cfg.GROSS_MARGIN_GREEN, cfg.GROSS_MARGIN_YELLOW)
    checks.append(CheckResult(
        name="Gross Margin",
        value=format_pct(gross_margin),
        benchmark=f"Green ≥ {cfg.GROSS_MARGIN_GREEN*100:.0f}%",
        status=st, score=sc,
        note=f"Gross margin: {format_pct(gross_margin)}",
    ))

    # 5. Operating Margin
    op_margin = safe_get(info, "operatingMargins")
    st, sc = _status_hi(op_margin, cfg.OP_MARGIN_GREEN, cfg.OP_MARGIN_YELLOW)
    checks.append(CheckResult(
        name="Operating Margin",
        value=format_pct(op_margin),
        benchmark=f"Green ≥ {cfg.OP_MARGIN_GREEN*100:.0f}%",
        status=st, score=sc,
        note=f"Operating margin: {format_pct(op_margin)}",
    ))

    # 6. Net Margin
    net_margin = safe_get(info, "profitMargins")
    st, sc = _status_hi(net_margin, cfg.NET_MARGIN_GREEN, cfg.NET_MARGIN_YELLOW)
    checks.append(CheckResult(
        name="Net Profit Margin",
        value=format_pct(net_margin),
        benchmark=f"Green ≥ {cfg.NET_MARGIN_GREEN*100:.0f}%",
        status=st, score=sc,
        note=f"Net profit margin: {format_pct(net_margin)}",
    ))

    # 7. ROE
    roe = safe_get(info, "returnOnEquity")
    st, sc = _status_hi(roe, cfg.ROE_GREEN, cfg.ROE_YELLOW)
    checks.append(CheckResult(
        name="Return on Equity (ROE)",
        value=format_pct(roe),
        benchmark=f"Green ≥ {cfg.ROE_GREEN*100:.0f}%",
        status=st, score=sc,
        note=f"ROE: {format_pct(roe)}",
    ))

    # 8. ROIC vs WACC proxy
    roic = _compute_roic(info, bal, inc)
    wacc = cfg.ROIC_WACC_PROXY
    if roic is not None:
        spread = roic - wacc
        if spread >= 0.05:
            st, sc = "green", 1.0
        elif spread >= 0:
            st, sc = "yellow", 0.5
        else:
            st, sc = "red", 0.0
        checks.append(CheckResult(
            name="ROIC vs WACC",
            value=format_pct(roic),
            benchmark=f"ROIC > {wacc*100:.0f}% WACC proxy",
            status=st, score=sc,
            note=f"ROIC {format_pct(roic)} vs WACC proxy {format_pct(wacc)} → spread {format_pct(spread)}",
        ))
    else:
        checks.append(CheckResult(
            name="ROIC vs WACC",
            benchmark=f"ROIC > {wacc*100:.0f}% (WACC proxy)",
            status="na", note="ROIC could not be computed",
        ))

    # ── FINANCIAL HEALTH ──────────────────────────────────────────────────

    # 9. Debt-to-Equity
    de = safe_get(info, "debtToEquity")
    if de is not None:
        de_norm = de / 100  # yfinance returns as percentage
        st, sc = _status_lo(de_norm, cfg.DE_GREEN, cfg.DE_YELLOW)
        checks.append(CheckResult(
            name="Debt-to-Equity Ratio",
            value=format_multiple(de_norm),
            benchmark=f"Green ≤ {cfg.DE_GREEN}x, Red > {cfg.DE_YELLOW}x",
            status=st, score=sc,
            note=f"D/E ratio: {de_norm:.2f}x",
        ))
    else:
        checks.append(CheckResult(
            name="Debt-to-Equity Ratio",
            benchmark=f"Green ≤ {cfg.DE_GREEN}x",
            status="na", note="D/E ratio not available",
        ))

    # 10. Interest Coverage
    ebit_series = _get_stmt_row(inc, "EBIT", "Operating Income")
    interest_series = _get_stmt_row(inc, "Interest Expense")
    ic = None
    if ebit_series is not None and interest_series is not None:
        ebit = float(ebit_series.iloc[0])
        interest = abs(float(interest_series.iloc[0]))
        if interest > 0:
            ic = ebit / interest
    if ic is not None:
        st, sc = _status_hi(ic, cfg.INTEREST_COVERAGE_GREEN, cfg.INTEREST_COVERAGE_YELLOW)
        checks.append(CheckResult(
            name="Interest Coverage",
            value=format_multiple(ic),
            benchmark=f"Green ≥ {cfg.INTEREST_COVERAGE_GREEN}x, Red < {cfg.INTEREST_COVERAGE_YELLOW}x",
            status=st, score=sc,
            note=f"EBIT covers interest {ic:.1f}× times",
        ))
    else:
        checks.append(CheckResult(
            name="Interest Coverage",
            benchmark=f"Green ≥ {cfg.INTEREST_COVERAGE_GREEN}x",
            status="na", note="Interest expense data not available",
        ))

    # 11. Free Cash Flow (positive and growing)
    fcf_check = _check_fcf_trend(cf)
    checks.append(fcf_check)

    # 12. Cash Reserves
    cash = safe_get(info, "totalCash")
    debt = safe_get(info, "totalDebt")
    if cash is not None and debt and debt > 0:
        cash_ratio = cash / debt
        st, sc = _status_hi(cash_ratio, cfg.CASH_DEBT_GREEN, cfg.CASH_DEBT_YELLOW)
        checks.append(CheckResult(
            name="Cash Reserves (Cash/Debt)",
            value=format_multiple(cash_ratio),
            benchmark=f"Green ≥ {cfg.CASH_DEBT_GREEN}x",
            status=st, score=sc,
            note=f"Cash-to-debt ratio: {cash_ratio:.2f}x",
        ))
    elif cash is not None:
        checks.append(CheckResult(
            name="Cash Reserves (Cash/Debt)",
            value="No debt",
            benchmark=f"Green ≥ {cfg.CASH_DEBT_GREEN}x",
            status="green", score=1.0,
            note="Company has cash and no reported debt",
        ))
    else:
        checks.append(CheckResult(
            name="Cash Reserves (Cash/Debt)",
            benchmark=f"Green ≥ {cfg.CASH_DEBT_GREEN}x",
            status="na", note="Cash data not available",
        ))

    # 13. Economic Moat Proxy
    moat_check = _check_moat(info)
    checks.append(moat_check)

    return checks


def _compute_roic(info: dict, bal, inc) -> float | None:
    try:
        net_income = safe_get(info, "netIncomeToCommon")
        if net_income is None and inc is not None:
            ni_s = _get_stmt_row(inc, "Net Income", "Net Income Common Stockholders")
            net_income = float(ni_s.iloc[0]) if ni_s is not None else None
        if net_income is None:
            return None

        total_assets = safe_get(info, "totalAssets")
        current_liab = safe_get(info, "totalCurrentLiabilities")
        if total_assets is None and bal is not None:
            ta_s = _get_stmt_row(bal, "Total Assets")
            total_assets = float(ta_s.iloc[0]) if ta_s is not None else None
        if current_liab is None and bal is not None:
            cl_s = _get_stmt_row(bal, "Current Liabilities", "Total Current Liabilities")
            current_liab = float(cl_s.iloc[0]) if cl_s is not None else None

        if total_assets is None:
            return None
        current_liab = current_liab or 0
        invested_capital = total_assets - current_liab
        if invested_capital <= 0:
            return None
        return net_income / invested_capital
    except Exception:
        return None


def _check_fcf_trend(cf) -> CheckResult:
    if cf is None or (hasattr(cf, "empty") and cf.empty):
        return CheckResult(
            name="Free Cash Flow",
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
    if fcf_row is None or len(fcf_row) < 1:
        return CheckResult(
            name="Free Cash Flow",
            benchmark="Positive and growing",
            status="na", note="Could not extract FCF",
        )
    vals = [float(v) for v in fcf_row.iloc[:3]]
    latest = vals[0]
    all_positive = all(v > 0 for v in vals)
    growing = len(vals) >= 2 and vals[0] > vals[-1]

    if all_positive and growing:
        st, sc = "green", 1.0
        note = "FCF is positive and growing"
    elif all_positive:
        st, sc = "yellow", 0.5
        note = "FCF is positive but not clearly growing"
    elif latest > 0:
        st, sc = "yellow", 0.5
        note = "FCF is currently positive but was negative in prior years"
    else:
        st, sc = "red", 0.0
        note = "FCF is currently negative"

    return CheckResult(
        name="Free Cash Flow",
        value=f"{latest/1e6:.0f}M" if abs(latest) >= 1e6 else f"{latest:,.0f}",
        benchmark="Positive and growing",
        status=st, score=sc, note=note,
    )


def _check_moat(info: dict) -> CheckResult:
    """Proxy moat via net margin, ROE, and revenue growth."""
    signals = 0
    total = 0

    net_margin = safe_get(info, "profitMargins")
    if net_margin is not None:
        total += 1
        if net_margin > 0.20:
            signals += 1

    roe = safe_get(info, "returnOnEquity")
    if roe is not None:
        total += 1
        if roe > 0.15:
            signals += 1

    rev_growth = safe_get(info, "revenueGrowth")
    if rev_growth is not None:
        total += 1
        if rev_growth > 0.10:
            signals += 1

    if total == 0:
        return CheckResult(
            name="Economic Moat (Proxy)",
            benchmark="Margin > 20% + ROE > 15% + Revenue growth > 10%",
            status="na", note="Insufficient data for moat proxy",
        )

    ratio = signals / total
    if ratio >= 0.67:
        st, sc = "green", 1.0
        note = f"Strong moat signals: {signals}/{total} criteria met"
    elif ratio >= 0.34:
        st, sc = "yellow", 0.5
        note = f"Moderate moat signals: {signals}/{total} criteria met"
    else:
        st, sc = "red", 0.0
        note = f"Weak moat signals: {signals}/{total} criteria met"

    return CheckResult(
        name="Economic Moat (Proxy)",
        value=f"{signals}/{total} signals",
        benchmark="Net margin >20%, ROE >15%, Rev growth >10%",
        status=st, score=sc, note=note,
    )
