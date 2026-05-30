import numpy as np
import pandas as pd
from valuation.models import CheckResult
from valuation.helpers import safe_get, format_pct
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
    checks = []

    inc = fin.get("income_stmt")
    bal = fin.get("balance_sheet")

    # 1. Earnings Stability (CV of 5yr EPS)
    checks.append(_check_earnings_stability(info, inc))

    # 2. Customer Concentration — always N/A (no free data)
    checks.append(CheckResult(
        name="Customer Concentration",
        benchmark="Single customer < 20% revenue",
        status="na",
        note="Customer concentration data not available from public sources",
    ))

    # 3. Regulatory Risk
    sector = safe_get(info, "sector", "Unknown")
    if sector in cfg.HIGH_REGULATORY_SECTORS:
        checks.append(CheckResult(
            name="Regulatory Risk",
            value=sector,
            benchmark="Sectors with high regulatory scrutiny",
            status="red", score=0.0,
            note=f"{sector} operates in a highly regulated environment",
        ))
    else:
        checks.append(CheckResult(
            name="Regulatory Risk",
            value=sector,
            benchmark="Low-to-moderate regulatory environment",
            status="green", score=1.0,
            note=f"{sector} faces moderate regulatory risk",
        ))

    # 4. Debt Risk (debt CAGR vs revenue CAGR)
    checks.append(_check_debt_risk(info, bal, inc))

    # 5. Cyclicality
    cyclical = cfg.SECTOR_CYCLICALITY.get(sector, False)
    if cyclical:
        checks.append(CheckResult(
            name="Business Cyclicality",
            value=sector,
            benchmark="Non-cyclical preferred",
            status="yellow", score=0.5,
            note=f"{sector} is cyclical — sensitive to economic downturns",
        ))
    else:
        checks.append(CheckResult(
            name="Business Cyclicality",
            value=sector,
            benchmark="Non-cyclical preferred",
            status="green", score=1.0,
            note=f"{sector} is generally non-cyclical",
        ))

    # 6. Insider Selling
    checks.append(_check_insider_selling(data))

    return checks


def _check_earnings_stability(info: dict, inc) -> CheckResult:
    # Try to get EPS series from income statement
    eps_series = _get_stmt_row(inc, "Basic EPS", "Diluted EPS")
    eps_vals = None
    if eps_series is not None and len(eps_series) >= 3:
        eps_vals = [float(v) for v in eps_series.iloc[:5]]

    if not eps_vals:
        # Fallback to single-point data
        eps = safe_get(info, "trailingEps")
        if eps is None:
            return CheckResult(
                name="Earnings Stability",
                benchmark="Low earnings volatility (CV < 25%)",
                status="na", note="EPS data not available",
            )
        return CheckResult(
            name="Earnings Stability",
            benchmark="Low earnings volatility",
            status="na", note="Only single EPS data point available",
        )

    arr = np.array(eps_vals)
    mean = arr.mean()
    if mean == 0:
        return CheckResult(
            name="Earnings Stability",
            benchmark="Low earnings volatility (CV < 25%)",
            status="red", score=0.0,
            note="Mean EPS is zero — highly unstable earnings",
        )
    cv = arr.std() / abs(mean)
    if cv <= cfg.EARNINGS_CV_GREEN:
        st, sc = "green", 1.0
        note = f"Earnings are very stable (CV={cv:.2f})"
    elif cv <= cfg.EARNINGS_CV_YELLOW:
        st, sc = "yellow", 0.5
        note = f"Earnings are moderately stable (CV={cv:.2f})"
    else:
        st, sc = "red", 0.0
        note = f"Earnings are volatile (CV={cv:.2f})"

    return CheckResult(
        name="Earnings Stability",
        value=f"CV={cv:.2f}",
        benchmark=f"Green CV < {cfg.EARNINGS_CV_GREEN}, Red CV > {cfg.EARNINGS_CV_YELLOW}",
        status=st, score=sc, note=note,
    )


def _check_debt_risk(info: dict, bal, inc) -> CheckResult:
    debt_series = _get_stmt_row(bal, "Total Debt", "Long Term Debt And Capital Lease Obligation")
    rev_series = _get_stmt_row(inc, "Total Revenue", "Revenue")

    def _cagr(series, years=3):
        if series is None or len(series) < years + 1:
            return None
        start = float(series.iloc[years])
        end = float(series.iloc[0])
        if start <= 0:
            return None
        return (end / start) ** (1 / years) - 1

    debt_cagr = _cagr(debt_series)
    rev_cagr = _cagr(rev_series)

    if debt_cagr is None or rev_cagr is None:
        # Fallback: single-point D/E
        de = safe_get(info, "debtToEquity")
        if de is None:
            return CheckResult(
                name="Debt Risk",
                benchmark="Debt not growing faster than revenue",
                status="na", note="Debt trend data not available",
            )
        de_norm = de / 100
        if de_norm < 0.5:
            st, sc = "green", 1.0
            note = f"D/E ratio is low ({de_norm:.2f}x) — minimal debt risk"
        elif de_norm < 1.5:
            st, sc = "yellow", 0.5
            note = f"D/E ratio is moderate ({de_norm:.2f}x)"
        else:
            st, sc = "red", 0.0
            note = f"D/E ratio is high ({de_norm:.2f}x)"
        return CheckResult(
            name="Debt Risk",
            value=f"D/E={de_norm:.2f}x",
            benchmark="Debt not outpacing revenue growth",
            status=st, score=sc, note=note,
        )

    ratio = debt_cagr / rev_cagr if rev_cagr > 0 else 99
    if ratio <= cfg.DEBT_CAGR_RATIO_GREEN:
        st, sc = "green", 1.0
        note = f"Debt growing ({debt_cagr*100:.1f}%) in line with revenue ({rev_cagr*100:.1f}%)"
    elif ratio <= cfg.DEBT_CAGR_RATIO_YELLOW:
        st, sc = "yellow", 0.5
        note = f"Debt growing ({debt_cagr*100:.1f}%) faster than revenue ({rev_cagr*100:.1f}%)"
    else:
        st, sc = "red", 0.0
        note = f"Debt growing ({debt_cagr*100:.1f}%) significantly faster than revenue ({rev_cagr*100:.1f}%)"

    return CheckResult(
        name="Debt Risk",
        value=f"Debt CAGR {debt_cagr*100:.1f}% vs Rev CAGR {rev_cagr*100:.1f}%",
        benchmark=f"Debt CAGR / Rev CAGR < {cfg.DEBT_CAGR_RATIO_YELLOW}",
        status=st, score=sc, note=note,
    )


def _check_insider_selling(data) -> CheckResult:
    try:
        ticker_obj = data._yf
        transactions = ticker_obj.insider_transactions
        if transactions is None or transactions.empty:
            return CheckResult(
                name="Insider Selling",
                benchmark="Net insider buying preferred",
                status="na", note="Insider transaction data not available",
            )
        # Filter last 90 days
        cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=90)
        if "startDate" in transactions.columns:
            recent = transactions[pd.to_datetime(transactions["startDate"], utc=True) >= cutoff]
        else:
            recent = transactions.head(20)

        if recent.empty:
            return CheckResult(
                name="Insider Selling",
                benchmark="Net insider buying preferred",
                status="na", note="No insider transactions in last 90 days",
            )

        if "shares" in recent.columns and "transactionType" in recent.columns:
            buys = recent[recent["transactionType"].str.contains("Purchase|Buy", case=False, na=False)]["shares"].sum()
            sells = recent[recent["transactionType"].str.contains("Sale|Sell", case=False, na=False)]["shares"].sum()
        elif "Value" in recent.columns:
            # Alternative column structure
            buys = recent[recent.get("Transaction", pd.Series()).str.contains("Buy|Purchase", case=False, na=False)]["Value"].sum()
            sells = recent[recent.get("Transaction", pd.Series()).str.contains("Sell|Sale", case=False, na=False)]["Value"].sum()
        else:
            return CheckResult(
                name="Insider Selling",
                benchmark="Net insider buying preferred",
                status="na", note="Could not parse insider transaction format",
            )

        total = buys + sells
        if total == 0:
            return CheckResult(
                name="Insider Selling",
                benchmark="Net insider buying preferred",
                status="na", note="No insider buy/sell activity found",
            )

        buy_ratio = buys / total
        if buy_ratio >= 0.5:
            st, sc = "green", 1.0
            note = f"Insiders are net buyers ({buy_ratio*100:.0f}% buys)"
        elif buy_ratio >= 0.2:
            st, sc = "yellow", 0.5
            note = f"Mixed insider activity ({buy_ratio*100:.0f}% buys)"
        else:
            st, sc = "red", 0.0
            note = f"Heavy insider selling ({(1-buy_ratio)*100:.0f}% sells)"

        return CheckResult(
            name="Insider Selling",
            value=f"{buy_ratio*100:.0f}% buys",
            benchmark="≥ 50% buys preferred",
            status=st, score=sc, note=note,
        )
    except Exception:
        return CheckResult(
            name="Insider Selling",
            benchmark="Net insider buying preferred",
            status="na", note="Could not retrieve insider data",
        )
