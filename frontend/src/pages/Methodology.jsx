import React, { useState } from "react";
import {
  ExternalLink, Database, FlaskConical, BarChart3,
  TrendingUp, Zap, Target, ShieldCheck, BookOpen,
  ChevronDown, ChevronUp,
} from "lucide-react";

// ─── Reusable building blocks ─────────────────────────────────────────────────

function SectionHeader({ icon: Icon, title, subtitle, color = "blue" }) {
  const colors = {
    blue:   "text-blue-400 bg-blue-900/30 border-blue-800",
    emerald:"text-emerald-400 bg-emerald-900/30 border-emerald-800",
    yellow: "text-yellow-400 bg-yellow-900/30 border-yellow-800",
    purple: "text-purple-400 bg-purple-900/30 border-purple-800",
    orange: "text-orange-400 bg-orange-900/30 border-orange-800",
  };
  return (
    <div className="flex items-start gap-3 mb-5">
      <div className={`p-2.5 rounded-lg border ${colors[color]}`}>
        <Icon className="w-5 h-5" />
      </div>
      <div>
        <h2 className="text-lg font-semibold text-white">{title}</h2>
        {subtitle && <p className="text-sm text-gray-400 mt-0.5">{subtitle}</p>}
      </div>
    </div>
  );
}

function Card({ children, className = "" }) {
  return (
    <div className={`bg-gray-900 border border-gray-800 rounded-xl p-5 ${className}`}>
      {children}
    </div>
  );
}

function Formula({ label, value, note }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-xs text-gray-500 uppercase tracking-wide">{label}</span>
      <code className="text-sm text-emerald-300 bg-gray-800 px-2 py-1 rounded font-mono">{value}</code>
      {note && <span className="text-xs text-gray-500 mt-0.5">{note}</span>}
    </div>
  );
}

function Badge({ children, color }) {
  const colors = {
    emerald: "bg-emerald-900/40 text-emerald-300 border-emerald-800",
    blue:    "bg-blue-900/40 text-blue-300 border-blue-800",
    yellow:  "bg-yellow-900/40 text-yellow-300 border-yellow-800",
    purple:  "bg-purple-900/40 text-purple-300 border-purple-800",
    gray:    "bg-gray-800 text-gray-300 border-gray-700",
  };
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${colors[color]}`}>
      {children}
    </span>
  );
}

function VerifyLink({ href, label, icon }) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="flex items-center gap-2 px-3 py-2 rounded-lg bg-gray-800 border border-gray-700
                 text-sm text-gray-300 hover:text-white hover:border-gray-500 transition group"
    >
      <span className="text-base">{icon}</span>
      <span>{label}</span>
      <ExternalLink className="w-3.5 h-3.5 ml-auto opacity-0 group-hover:opacity-100 transition" />
    </a>
  );
}

// ─── Collapsible criterion card ───────────────────────────────────────────────

function CriterionCard({ index, icon, label, color, badge, formulas, rationale, children }) {
  const [open, setOpen] = useState(true);
  const borderColors = {
    emerald: "border-emerald-800",
    blue:    "border-blue-800",
    yellow:  "border-yellow-800",
    purple:  "border-purple-800",
  };
  const headerColors = {
    emerald: "text-emerald-400",
    blue:    "text-blue-400",
    yellow:  "text-yellow-400",
    purple:  "text-purple-400",
  };
  return (
    <div className={`bg-gray-900 border ${borderColors[color]} rounded-xl overflow-hidden`}>
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-3 px-5 py-4 hover:bg-gray-800/50 transition text-left"
      >
        <span className="text-xl">{icon}</span>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className={`text-xs font-bold uppercase tracking-widest ${headerColors[color]}`}>
              Criterion {index}
            </span>
            <Badge color={color}>{badge}</Badge>
          </div>
          <div className="text-base font-semibold text-white mt-0.5">{label}</div>
        </div>
        {open
          ? <ChevronUp className="w-4 h-4 text-gray-500" />
          : <ChevronDown className="w-4 h-4 text-gray-500" />}
      </button>

      {open && (
        <div className="px-5 pb-5 space-y-4 border-t border-gray-800">
          <p className="text-sm text-gray-400 pt-4">{rationale}</p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {formulas.map((f, i) => <Formula key={i} {...f} />)}
          </div>

          {children && (
            <div className="bg-gray-800/50 rounded-lg p-3 text-sm text-gray-400">
              {children}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function Methodology() {
  const [symbol, setSymbol] = useState("RELIANCE");

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-8 space-y-10">

      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          <BookOpen className="w-6 h-6 text-blue-400" />
          How Results Are Determined
        </h1>
        <p className="text-gray-400 text-sm mt-2 max-w-2xl">
          Every pre-breakout setup shown on the Dashboard is derived from a transparent,
          rule-based formula applied to official NSE data. This page explains exactly what
          data is used, how each criterion is calculated, and how you can independently
          verify any result.
        </p>
      </div>

      {/* ── 1. Data Source ─────────────────────────────────────────────────── */}
      <section className="space-y-4">
        <SectionHeader
          icon={Database}
          color="blue"
          title="Data Source — NSE Official Bhavcopy"
          subtitle="Where the OHLCV numbers come from"
        />

        <Card>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-5">
            <div className="bg-gray-800/60 rounded-lg p-3">
              <div className="text-xs text-gray-500 mb-1">Provider</div>
              <div className="text-sm font-semibold text-white">National Stock Exchange of India</div>
            </div>
            <div className="bg-gray-800/60 rounded-lg p-3">
              <div className="text-xs text-gray-500 mb-1">File format</div>
              <div className="text-sm font-semibold text-white">CSV · published daily after 6 PM IST</div>
            </div>
            <div className="bg-gray-800/60 rounded-lg p-3">
              <div className="text-xs text-gray-500 mb-1">Coverage</div>
              <div className="text-sm font-semibold text-white">~2,400 NSE-listed equity stocks (EQ series)</div>
            </div>
          </div>

          <div className="mb-4">
            <div className="text-xs text-gray-500 mb-1.5 uppercase tracking-wide">Official archive URL pattern</div>
            <code className="block text-xs text-emerald-300 bg-gray-800 px-3 py-2 rounded-lg font-mono break-all">
              https://nsearchives.nseindia.com/products/content/sec_bhavdata_full_DDMMYYYY.csv
            </code>
            <p className="text-xs text-gray-500 mt-1.5">
              Each file contains one row per traded stock: SYMBOL, SERIES, OPEN_PRICE, HIGH_PRICE,
              LOW_PRICE, CLOSE_PRICE, TTL_TRD_QNTY (volume). We download and cache ~255 trading days
              (~375 calendar days) on first run, then only fetch the latest missing day on each restart.
            </p>
          </div>

          <div className="flex flex-wrap gap-2 mt-3">
            <VerifyLink
              href="https://nsearchives.nseindia.com/products/content/sec_bhavdata_full_28052026.csv"
              icon="📥"
              label="Download today's Bhavcopy (CSV)"
            />
            <VerifyLink
              href="https://www.nseindia.com/market-data/live-equity-market"
              icon="🏛"
              label="NSE Live Equity Market"
            />
          </div>

          <div className="mt-4 p-3 bg-yellow-900/20 border border-yellow-800/50 rounded-lg text-xs text-yellow-300">
            ⚠ Prices are <strong>unadjusted for splits/bonuses</strong> — the same values shown on nseindia.com.
            This is standard practice for Indian technical analysis. For stocks that had a split in the past
            year, the 52-week high comparison may show a higher pre-split price.
          </div>
        </Card>
      </section>

      {/* ── 2. Four Criteria ──────────────────────────────────────────────── */}
      <section className="space-y-4">
        <SectionHeader
          icon={FlaskConical}
          color="emerald"
          title="The 4-Criteria Breakout Model"
          subtitle="A stock must satisfy ≥ 2 of these 4 criteria to appear in results"
        />

        <div className="grid grid-cols-3 gap-3 mb-2">
          {[
            { label: "Strong",    count: "4 / 4", color: "emerald" },
            { label: "Moderate",  count: "3 / 4", color: "yellow"  },
            { label: "Watchlist", count: "2 / 4", color: "blue"    },
          ].map(({ label, count, color }) => (
            <div key={label} className="bg-gray-900 border border-gray-800 rounded-lg p-3 text-center">
              <Badge color={color}>{label}</Badge>
              <div className="text-2xl font-bold text-white mt-2">{count}</div>
              <div className="text-xs text-gray-500">criteria met</div>
            </div>
          ))}
        </div>

        <CriterionCard
          index="A"
          icon="📈"
          label="Near Resistance — Price Breakout Zone"
          color="emerald"
          badge="price_breakout"
          rationale="The stock is within 3% below a key resistance level (52-week high, 20-day high, or 200 DMA), or has already broken just above it. This identifies stocks 'coiling' for a move rather than ones that already ran."
          formulas={[
            { label: "Near 52-week high",  value: "h52w × 0.97 ≤ CMP < h52w",         note: "Within 3% below 52W high" },
            { label: "Near 20-day high",   value: "h20d × 0.97 ≤ CMP",                 note: "Within 3% below recent high" },
            { label: "Near 200 DMA",       value: "SMA200 × 0.97 ≤ CMP < SMA200 × 1.02", note: "Hugging the long-term MA" },
            { label: "Fresh breakout",     value: "CMP ≥ h52w  OR  CMP ≥ h20d",        note: "Already above resistance" },
          ]}
        >
          Result is <strong>TRUE</strong> if the stock satisfies any one of the above conditions.
          The label (NEAR_52W_HIGH, NEAR_20D_HIGH, NEAR_200DMA) shown in the table is the first
          matching condition in priority order.
        </CriterionCard>

        <CriterionCard
          index="B"
          icon="📊"
          label="Volume Building — Accumulation Underway"
          color="blue"
          badge="volume_confirmed"
          rationale="Smart money accumulates quietly before a breakout. We look for volume rising over the recent 3 days versus the prior 10 days, or a significant single-day volume spike — both signal institutional participation."
          formulas={[
            { label: "3-day avg > 10-day avg", value: "avgVol3d ≥ avgVol10d × 1.15",  note: "Recent volume 15%+ above prior 10-day avg" },
            { label: "Volume spike",           value: "todayVolume / avgVol20d ≥ 1.5x", note: "Today's volume 1.5× the 20-day average" },
          ]}
        >
          Result is <strong>TRUE</strong> if either condition is met (OR logic).
          Volume ratio shown in the table is <code>today ÷ 20-day avg</code>.
        </CriterionCard>

        <CriterionCard
          index="C"
          icon="⚡"
          label="Momentum Building — RSI + MACD Improving"
          color="yellow"
          badge="momentum_ok"
          rationale="Momentum indicators confirm the stock has internal strength. RSI in the 45–72 'sweet spot' means not overbought but building strength. A rising RSI plus improving MACD histogram confirms the move has legs."
          formulas={[
            { label: "RSI range",       value: "45 ≤ RSI(14) ≤ 72",                 note: "Healthy momentum zone — not overbought" },
            { label: "RSI rising",      value: "RSI(today) > RSI(5 sessions ago)",   note: "Momentum trending upward" },
            { label: "MACD positive",   value: "MACD histogram > 0",                 note: "Fast EMA above slow EMA" },
            { label: "MACD improving",  value: "histogram(today) > histogram(3d ago)", note: "Momentum accelerating" },
          ]}
        >
          Result is <strong>TRUE</strong> if: RSI in range AND RSI rising AND (MACD positive OR MACD improving).
          MACD uses standard settings: fast=12, slow=26, signal=9.
        </CriterionCard>

        <CriterionCard
          index="D"
          icon="🔺"
          label="Trend Intact + Consolidating"
          color="purple"
          badge="trend_ok"
          rationale="A breakout only works when the underlying trend is up and the stock has been 'coiling' in a tight range. Consolidation after a run-up (flag/pennant pattern) is the highest-probability breakout setup."
          formulas={[
            { label: "Above 50 DMA",    value: "CMP > SMA(50)",                      note: "Medium-term uptrend intact" },
            { label: "Tight range",     value: "(10d high − 10d low) / CMP < 8%",    note: "Price compressed in a narrow channel" },
          ]}
        >
          Result is <strong>TRUE</strong> if both conditions are met (AND logic).
          The 10-day range % is shown in the scan logs. A range below 5% is especially strong (very tight coil).
        </CriterionCard>
      </section>

      {/* ── 3. Scoring & Entry Levels ─────────────────────────────────────── */}
      <section className="space-y-4">
        <SectionHeader
          icon={BarChart3}
          color="orange"
          title="Strength Score & Suggested Levels"
          subtitle="How the 0–100 score is calculated and where entry/stop/target come from"
        />

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <Card>
            <div className="text-xs text-gray-500 uppercase tracking-wide mb-2">Strong (4/4)</div>
            <code className="text-emerald-300 text-sm font-mono">90 + min(10, (volRatio − 2) × 2)</code>
            <p className="text-xs text-gray-500 mt-2">Base score 90. Bonus up to +10 for very high volume.</p>
          </Card>
          <Card>
            <div className="text-xs text-gray-500 uppercase tracking-wide mb-2">Moderate (3/4)</div>
            <code className="text-yellow-300 text-sm font-mono">60 + min(25, (volRatio − 1) × 5)</code>
            <p className="text-xs text-gray-500 mt-2">Base score 60. Bonus up to +25 for elevated volume.</p>
          </Card>
          <Card>
            <div className="text-xs text-gray-500 uppercase tracking-wide mb-2">Watchlist (2/4)</div>
            <code className="text-blue-300 text-sm font-mono">30 + min(25, (volRatio − 1) × 5)</code>
            <p className="text-xs text-gray-500 mt-2">Base score 30. Monitor — needs more confirmation.</p>
          </Card>
        </div>

        <Card>
          <div className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
            <Target className="w-4 h-4 text-orange-400" /> Suggested Trade Levels
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <Formula
              label="Entry Price"
              value="resistance × 1.005"
              note="0.5% above the resistance (buy the breakout confirmation, not in anticipation)"
            />
            <Formula
              label="Stop Loss"
              value="CMP × 0.96"
              note="4% below current price — below the consolidation low"
            />
            <Formula
              label="Target Price"
              value="entry + 2 × (entry − stop)"
              note="1:2 Risk-Reward ratio — minimum acceptable trade setup"
            />
          </div>
          <p className="text-xs text-gray-500 mt-4 p-3 bg-gray-800/50 rounded-lg">
            <strong className="text-gray-300">Resistance used:</strong> 52W high if breakout type is NEAR_52W_HIGH,
            otherwise the 20-day high. Entry and stop are <em>suggestions only</em> — adjust based on
            your own risk tolerance, ATR, and the specific chart pattern.
          </p>
        </Card>
      </section>

      {/* ── 4. Nifty Trend Filter ─────────────────────────────────────────── */}
      <section className="space-y-4">
        <SectionHeader
          icon={TrendingUp}
          color="blue"
          title="Nifty Trend Filter"
          subtitle="Market-level context applied to every scan"
        />
        <Card>
          <p className="text-sm text-gray-400 mb-4">
            The <Badge color="emerald">Nifty Uptrend</Badge> / <Badge color="gray">Nifty Downtrend</Badge> badge
            in the header reflects whether the Nifty 50 index is currently above its 50-day SMA.
            When Nifty is in a downtrend, individual stock breakouts have a lower success rate — the badge
            is a reminder to size positions smaller or wait for market confirmation.
          </p>
          <Formula
            label="Nifty trend formula"
            value="Nifty50 close > SMA(Nifty50, 50)"
            note="Fetched from Yahoo Finance (^NSEI). TRUE = uptrend, FALSE = downtrend."
          />
        </Card>
      </section>

      {/* ── 5. Verify Results ─────────────────────────────────────────────── */}
      <section className="space-y-4">
        <SectionHeader
          icon={ShieldCheck}
          color="emerald"
          title="Verify Any Result Independently"
          subtitle="Cross-check a signal on external platforms in under 60 seconds"
        />

        <Card>
          <p className="text-sm text-gray-400 mb-4">
            Enter a symbol to generate direct verification links for that stock:
          </p>
          <div className="flex gap-2 mb-5">
            <input
              type="text"
              value={symbol}
              onChange={e => setSymbol(e.target.value.toUpperCase().trim())}
              placeholder="e.g. RELIANCE"
              className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm
                         text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 transition"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            <VerifyLink
              href={`https://www.nseindia.com/get-quotes/equity?symbol=${symbol}`}
              icon="🏛"
              label={`NSE India — ${symbol} Quote`}
            />
            <VerifyLink
              href={`https://www.tradingview.com/chart/?symbol=NSE%3A${symbol}`}
              icon="📊"
              label={`TradingView — NSE:${symbol} Chart`}
            />
            <VerifyLink
              href={`https://www.screener.in/company/${symbol}/`}
              icon="🔍"
              label={`Screener.in — ${symbol} Fundamentals`}
            />
            <VerifyLink
              href={`https://chartink.com/stocks/${symbol.toLowerCase()}.html`}
              icon="📈"
              label={`Chartink — ${symbol} Technical`}
            />
            <VerifyLink
              href={`https://ticker.finology.in/company/${symbol}`}
              icon="💡"
              label={`Finology Ticker — ${symbol}`}
            />
            <VerifyLink
              href={`https://finance.yahoo.com/quote/${symbol}.NS`}
              icon="🌐"
              label={`Yahoo Finance — ${symbol}.NS`}
            />
          </div>
        </Card>

        <Card>
          <div className="text-sm font-semibold text-white mb-3">What to check on each platform</div>
          <div className="space-y-3">
            {[
              {
                platform: "NSEIndia",
                icon: "🏛",
                checks: ["Confirm CMP and 52-week high/low match our values", "Check delivery % — high delivery = institutional buying"],
              },
              {
                platform: "TradingView",
                icon: "📊",
                checks: ["Visually confirm consolidation / flag pattern", "Check RSI and MACD match our displayed values", "Draw the resistance level — is it clean or messy?"],
              },
              {
                platform: "Screener.in",
                icon: "🔍",
                checks: ["Check promoter holding (>50% is positive)", "Verify quarterly sales and profit are growing", "Confirm no red flags in pledging or debt"],
              },
            ].map(({ platform, icon, checks }) => (
              <div key={platform} className="flex gap-3 p-3 bg-gray-800/50 rounded-lg">
                <span className="text-lg mt-0.5">{icon}</span>
                <div>
                  <div className="text-sm font-medium text-white">{platform}</div>
                  <ul className="mt-1 space-y-1">
                    {checks.map((c, i) => (
                      <li key={i} className="text-xs text-gray-400 flex items-start gap-1.5">
                        <span className="text-emerald-500 mt-0.5">✓</span>{c}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            ))}
          </div>
        </Card>
      </section>

      {/* ── 6. Source code ────────────────────────────────────────────────── */}
      <section className="space-y-4">
        <SectionHeader
          icon={Zap}
          color="purple"
          title="Formula Source Code"
          subtitle="Exact implementation — no black box"
        />
        <Card>
          <p className="text-sm text-gray-400 mb-3">
            The complete scanner logic is in a single readable file. Every threshold and condition
            described above maps 1:1 to a line of code you can read and audit:
          </p>
          <div className="space-y-2">
            <VerifyLink
              href="https://github.com"
              icon="📄"
              label="backend/scanner.py — analyse_stock() function"
            />
            <VerifyLink
              href="https://github.com"
              icon="📄"
              label="backend/nse_bhavcopy.py — NSE data downloader"
            />
          </div>
          <p className="text-xs text-gray-600 mt-3">
            File locations on your machine: <code className="text-gray-500">C:\Users\arulm\Breakout\backend\scanner.py</code>
          </p>
        </Card>
      </section>

      {/* ── 7. Disclaimer ─────────────────────────────────────────────────── */}
      <div className="p-4 bg-gray-900 border border-gray-800 rounded-xl text-xs text-gray-500 leading-relaxed">
        <strong className="text-gray-400">Disclaimer:</strong> This scanner is an educational tool based on publicly
        available data from NSE India. It does not constitute investment advice. All technical signals are
        probabilistic — no setup has a 100% success rate. Always do your own research, consult a SEBI-registered
        advisor if needed, and never risk more than you can afford to lose. Past performance of technical patterns
        does not guarantee future results.
      </div>

    </div>
  );
}
