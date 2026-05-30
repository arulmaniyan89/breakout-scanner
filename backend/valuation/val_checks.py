import numpy as np
from valuation.models import CheckResult
from valuation.dcf import calculate_dcf, DCFResult
from valuation.helpers import safe_get, format_pct, format_multiple
import valuation.eval_config as cfg


def _status(value, green_thresh, yellow_thresh, lower_is_better=True) -> tuple[str, float]:
    """Return (status, score) where lower_is_better=True means lower value = greener."""
    if value is None:
        return "na", 0.0
    if lower_is_better:
        if value <= green_thresh:
            return "green", 1.0
        elif value <= yellow_thresh:
            return "yellow", 0.5
        else:
            return "red", 0.0
    else:
        if value >= green_thresh:
            return "green", 1.0
        elif value >= yellow_thresh:
            return "yellow", 0.5
        else:
            return "red", 0.0


def run(data) -> tuple[list[CheckResult], DCFResult]:
    info = data.get_info()
    fin = data.get_financials()
    hist = data.get_history("5y")

    dcf = calculate_dcf(
        info, fin,
        discount_rate=cfg.DCF_DISCOUNT_RATE,
        terminal_growth=cfg.DCF_TERMINAL_GROWTH,
        growth_min=cfg.DCF_GROWTH_MIN,
        growth_max=cfg.DCF_GROWTH_MAX,
    )

    checks = []

    # --- 1. P/E vs Industry ---
    pe = safe_get(info, "trailingPE")
    sector = safe_get(info, "sector", "Unknown")
    market = "IN" if data.ticker.endswith(".NS") or data.ticker.endswith(".BO") else "US"
    sector_dict = cfg.IN_SECTOR_PE if market == "IN" else cfg.US_SECTOR_PE
    sector_pe = sector_dict.get(sector, sector_dict["Unknown"])

    if pe is not None and pe > 0:
        ratio = pe / sector_pe
        if ratio <= (1 - cfg.PE_BAND):
            st, sc = "green", 1.0
        elif ratio <= (1 + cfg.PE_BAND):
            st, sc = "yellow", 0.5
        else:
            st, sc = "red", 0.0
        checks.append(CheckResult(
            name="P/E vs Industry",
            value=format_multiple(pe),
            benchmark=f"Sector avg: {sector_pe}x",
            status=st, score=sc,
            note=f"P/E is {pe:.1f}x vs sector average {sector_pe}x",
        ))
    else:
        checks.append(CheckResult(
            name="P/E vs Industry",
            benchmark=f"Sector avg: {sector_pe}x",
            status="na", note="P/E not available",
        ))

    # --- 2. PEG Ratio ---
    peg = safe_get(info, "pegRatio")
    if peg is not None and peg > 0:
        if peg < cfg.PEG_GREEN:
            st, sc = "green", 1.0
        elif peg < cfg.PEG_YELLOW:
            st, sc = "yellow", 0.5
        else:
            st, sc = "red", 0.0
        checks.append(CheckResult(
            name="PEG Ratio",
            value=format_multiple(peg),
            benchmark="< 1.0 (undervalued for growth)",
            status=st, score=sc,
            note=f"PEG of {peg:.2f} {'suggests undervaluation' if peg < 1 else 'suggests overvaluation'} relative to growth",
        ))
    else:
        checks.append(CheckResult(
            name="PEG Ratio",
            benchmark="< 1.0 (undervalued for growth)",
            status="na", note="PEG not available",
        ))

    # --- 3. P/B Ratio ---
    pb = safe_get(info, "priceToBook")
    if pb is not None:
        st, sc = _status(pb, cfg.PB_GREEN, cfg.PB_YELLOW)
        checks.append(CheckResult(
            name="P/B Ratio",
            value=format_multiple(pb),
            benchmark=f"Green < {cfg.PB_GREEN}x, Red > {cfg.PB_YELLOW}x",
            status=st, score=sc,
            note=f"Price-to-book of {pb:.2f}x",
        ))
    else:
        checks.append(CheckResult(
            name="P/B Ratio",
            benchmark=f"Green < {cfg.PB_GREEN}x",
            status="na", note="P/B not available",
        ))

    # --- 4. EV/EBITDA ---
    ev_ebitda = safe_get(info, "enterpriseToEbitda")
    if ev_ebitda is not None and ev_ebitda > 0:
        st, sc = _status(ev_ebitda, cfg.EV_EBITDA_GREEN, cfg.EV_EBITDA_YELLOW)
        checks.append(CheckResult(
            name="EV/EBITDA",
            value=format_multiple(ev_ebitda),
            benchmark=f"Green < {cfg.EV_EBITDA_GREEN}x, Red > {cfg.EV_EBITDA_YELLOW}x",
            status=st, score=sc,
            note=f"EV/EBITDA of {ev_ebitda:.1f}x",
        ))
    else:
        checks.append(CheckResult(
            name="EV/EBITDA",
            benchmark=f"Green < {cfg.EV_EBITDA_GREEN}x",
            status="na", note="EV/EBITDA not available",
        ))

    # --- 5. FCF Yield ---
    fcf = safe_get(info, "freeCashflow")
    mktcap = safe_get(info, "marketCap")
    if fcf is not None and mktcap and mktcap > 0:
        fcf_yield = fcf / mktcap
        st, sc = _status(fcf_yield, cfg.FCF_YIELD_GREEN, cfg.FCF_YIELD_YELLOW, lower_is_better=False)
        checks.append(CheckResult(
            name="FCF Yield",
            value=format_pct(fcf_yield),
            benchmark=f"Green > {cfg.FCF_YIELD_GREEN*100:.0f}%, Red < {cfg.FCF_YIELD_YELLOW*100:.0f}%",
            status=st, score=sc,
            note=f"Free cash flow yield: {fcf_yield*100:.1f}%",
        ))
    else:
        checks.append(CheckResult(
            name="FCF Yield",
            benchmark=f"Green > {cfg.FCF_YIELD_GREEN*100:.0f}%",
            status="na", note="FCF or market cap not available",
        ))

    # --- 6. DCF Intrinsic Value ---
    price = safe_get(info, "currentPrice") or safe_get(info, "regularMarketPrice")
    if dcf.intrinsic and price and price > 0:
        ratio = price / dcf.intrinsic
        if ratio <= (1 - cfg.DCF_BAND):
            st, sc = "green", 1.0
            note = f"Price ({price:.2f}) is {(1-ratio)*100:.0f}% below intrinsic ({dcf.intrinsic:.2f}) — margin of safety"
        elif ratio <= (1 + cfg.DCF_BAND):
            st, sc = "yellow", 0.5
            note = f"Price ({price:.2f}) is near intrinsic value ({dcf.intrinsic:.2f})"
        else:
            st, sc = "red", 0.0
            note = f"Price ({price:.2f}) is {(ratio-1)*100:.0f}% above intrinsic ({dcf.intrinsic:.2f})"
        checks.append(CheckResult(
            name="DCF Intrinsic Value",
            value=f"{price:.2f}",
            benchmark=f"Intrinsic: {dcf.intrinsic:.2f} (method: {dcf.method})",
            status=st, score=sc, note=note,
        ))
    else:
        checks.append(CheckResult(
            name="DCF Intrinsic Value",
            benchmark="DCF intrinsic vs current price",
            status="na", note="Insufficient data for DCF" if dcf.method == "N/A" else "Price not available",
        ))

    # --- 7. Historical P/E vs Own Average ---
    hist_pe_status = _check_historical_pe(info, hist, safe_get(info, "trailingPE"))
    checks.append(hist_pe_status)

    return checks, dcf


def _check_historical_pe(info: dict, hist, current_pe) -> CheckResult:
    if hist is None or hist.empty or current_pe is None or current_pe <= 0:
        return CheckResult(
            name="Historical P/E",
            benchmark="vs own 5-year average",
            status="na", note="Historical data not available",
        )

    # Compute 5yr average P/E using annual EPS from info fields
    eps_ttm = safe_get(info, "trailingEps")
    if eps_ttm is None or eps_ttm <= 0:
        return CheckResult(
            name="Historical P/E",
            benchmark="vs own 5-year average",
            status="na", note="EPS not available for historical P/E",
        )

    try:
        close = hist["Close"].resample("ME").last().dropna()
        # Approximate 5yr avg P/E using current EPS (rough proxy — EPS is relatively stable)
        avg_pe = (close / eps_ttm).mean()
        if avg_pe <= 0:
            raise ValueError

        band = cfg.HIST_PE_BAND
        if current_pe <= avg_pe * (1 - band):
            st, sc = "green", 1.0
        elif current_pe <= avg_pe * (1 + band):
            st, sc = "yellow", 0.5
        else:
            st, sc = "red", 0.0

        return CheckResult(
            name="Historical P/E",
            value=format_multiple(current_pe),
            benchmark=f"5yr avg ≈ {avg_pe:.1f}x",
            status=st, score=sc,
            note=f"Current P/E {current_pe:.1f}x vs approx 5yr avg {avg_pe:.1f}x",
        )
    except Exception:
        return CheckResult(
            name="Historical P/E",
            benchmark="vs own 5-year average",
            status="na", note="Could not compute historical P/E",
        )
