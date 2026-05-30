from dataclasses import dataclass, field
from typing import Any


@dataclass
class CheckResult:
    name: str
    value: Any = None           # raw value for display
    benchmark: str = ""         # human-readable benchmark description
    status: str = "na"          # "green" | "yellow" | "red" | "na"
    note: str = ""              # short explanatory note
    score: float = 0.0          # 1.0=green, 0.5=yellow, 0.0=red; N/A excluded

    def as_dict(self) -> dict:
        return {
            "Check": self.name,
            "Value": self.value,
            "Benchmark": self.benchmark,
            "Status": self.status,
            "Note": self.note,
        }


@dataclass
class DCFResult:
    intrinsic: float | None = None
    bull: float | None = None
    bear: float | None = None
    margin_of_safety: float | None = None
    growth_rate_used: float | None = None
    method: str = "FCF"         # "FCF" | "EPS-proxy" | "N/A"


@dataclass
class StockVerdict:
    ticker: str = ""
    company_name: str = ""
    current_price: float | None = None
    currency: str = "$"
    sector: str = "Unknown"
    industry: str = "Unknown"

    category_scores: dict = field(default_factory=dict)   # {cat: 0–100}
    overall_score: float = 0.0

    verdict: str = "N/A"        # "BUY" | "HOLD" | "AVOID" | "N/A"
    verdict_color: str = "gray"  # "green" | "yellow" | "red" | "gray"

    price_target_low: float | None = None
    price_target_mid: float | None = None
    price_target_high: float | None = None
    upside_pct: float | None = None

    dcf: DCFResult = field(default_factory=DCFResult)

    checks: dict = field(default_factory=dict)
    # keys: "valuation", "fundamentals", "risk", "future"
    # values: list[CheckResult]

    error: str | None = None    # set if fetch/evaluation failed entirely


VERDICT_COLORS = {
    "BUY": "green",
    "HOLD": "orange",
    "AVOID": "red",
    "N/A": "gray",
}
