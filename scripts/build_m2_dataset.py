#!/usr/bin/env python3
"""Build a long-history M2 dataset using World Bank broad money data and yfinance FX rates.

- M2 proxy: World Bank indicator FM.LBL.BMNY.CN (Broad money, current LCU)
- FX: yfinance annual average close for currency pairs; fallback to World Bank PA.NUS.FCRF

Outputs:
- docs/data/m2_long_history.json
- static/data/m2_long_history.json
"""

from __future__ import annotations

import json
import math
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd
import requests
import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
OUT_DOCS = ROOT / "docs" / "data" / "m2_long_history.json"
OUT_STATIC = ROOT / "static" / "data" / "m2_long_history.json"

WB_API = "https://api.worldbank.org/v2/country/{country}/indicator/{indicator}?format=json&per_page=2000&date={start}:{end}"

M2_IND = "FM.LBL.BMNY.CN"  # Broad money, current LCU
M2_GROWTH_IND = "FM.LBL.BMNY.ZG"  # Broad money growth (annual %)
FX_IND = "PA.NUS.FCRF"  # Official exchange rate (LCU per USD)
INT_RATE_IND = "FR.INR.LEND"  # Lending interest rate (%)

START_YEAR = 1980
END_YEAR = datetime.now(UTC).year - 1

COUNTRIES = {
    "US": {"name": "United States", "wb": "US", "currency": "USD", "gdpRank": 1},
    "CN": {"name": "China", "wb": "CN", "currency": "CNY", "gdpRank": 2},
    "JP": {"name": "Japan", "wb": "JP", "currency": "JPY", "gdpRank": 3},
    "DE": {"name": "Germany", "wb": "DE", "currency": "EUR", "gdpRank": 4},
    "IN": {"name": "India", "wb": "IN", "currency": "INR", "gdpRank": 5},
    "GB": {"name": "United Kingdom", "wb": "GB", "currency": "GBP", "gdpRank": 6},
    "FR": {"name": "France", "wb": "FR", "currency": "EUR", "gdpRank": 7},
    "IT": {"name": "Italy", "wb": "IT", "currency": "EUR", "gdpRank": 8},
    "BR": {"name": "Brazil", "wb": "BR", "currency": "BRL", "gdpRank": 9},
    "CA": {"name": "Canada", "wb": "CA", "currency": "CAD", "gdpRank": 10},
}

CURRENCY_REF_COUNTRY = {
    "USD": "US",
    "EUR": "DE",  # representative euro area country for FX fallback
    "CNY": "CN",
    "JPY": "JP",
    "INR": "IN",
    "GBP": "GB",
    "BRL": "BR",
    "CAD": "CA",
}

BASE_CURRENCIES = ["USD", "EUR", "CNY", "JPY", "GBP", "INR"]

EVENTS = [
    {"year": 1985, "title": "Plaza Accord", "detail": "G5 agreement to depreciate the USD; major FX regime shift."},
    {"year": 1991, "title": "USSR Dissolution", "detail": "Large geopolitical realignment and transition shocks."},
    {"year": 1997, "title": "Asian Financial Crisis", "detail": "Regional FX collapses, reserve loss, and liquidity stress."},
    {"year": 1999, "title": "Euro Launch", "detail": "Introduction of EUR and structural shift in European monetary transmission."},
    {"year": 2001, "title": "China WTO Entry", "detail": "Trade integration accelerates growth and credit deepening."},
    {"year": 2008, "title": "Global Financial Crisis", "detail": "Aggressive monetary easing, liquidity facilities, and balance sheet expansion."},
    {"year": 2010, "title": "Euro Sovereign Debt Crisis", "detail": "Fragmentation risk and unconventional policy in euro area."},
    {"year": 2016, "title": "Brexit Referendum", "detail": "Sterling repricing and UK macro-financial uncertainty spike."},
    {"year": 2020, "title": "COVID-19 Policy Shock", "detail": "Historic fiscal-monetary response and sharp jump in broad money growth."},
    {"year": 2022, "title": "Russia-Ukraine War", "detail": "Energy shock, inflation surge, and synchronized rate hikes."},
]


def wb_series(country: str, indicator: str, start: int, end: int) -> Dict[int, float]:
    url = WB_API.format(country=country, indicator=indicator, start=start, end=end)

    data = None
    for attempt in range(1, 4):
        try:
            r = requests.get(url, timeout=60)
            r.raise_for_status()
            data = r.json()
            break
        except Exception:
            if attempt == 3:
                return {}
            time.sleep(1.5 * attempt)

    out: Dict[int, float] = {}
    if isinstance(data, list) and len(data) > 1 and data[1]:
        for row in data[1]:
            if row.get("value") is None:
                continue
            y = int(row["date"])
            out[y] = float(row["value"])
    return out


def _to_annual_close(df: pd.DataFrame) -> Dict[int, float]:
    if df is None or df.empty:
        return {}
    close = df.get("Close")
    if close is None:
        return {}
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]
    close = close.dropna()
    if close.empty:
        return {}
    annual = close.groupby(close.index.year).mean()
    return {int(y): float(v) for y, v in annual.items() if pd.notna(v) and v > 0}


def yfinance_usd_per_currency(currency: str, start: int, end: int) -> Tuple[Dict[int, float], str]:
    """Return annual USD per 1 unit of currency using yfinance, or empty dict on failure.

    - Preferred pair: CURRENCYUSD=X (e.g., EURUSD=X) => USD per 1 currency
    - Fallback pair: USDCURRENCY=X (e.g., USDJPY=X) => currency per 1 USD; invert
    """
    if currency == "USD":
        return {y: 1.0 for y in range(start, end + 1)}, "fixed"

    tickers = [
        (f"{currency}USD=X", False),
        (f"USD{currency}=X", True),
    ]

    for ticker, invert in tickers:
        try:
            df = yf.download(
                ticker,
                start=f"{start}-01-01",
                end=f"{end + 1}-01-01",
                interval="1mo",
                auto_adjust=False,
                progress=False,
                threads=False,
            )
            annual = _to_annual_close(df)
            if not annual:
                continue
            if invert:
                annual = {y: (1.0 / v) for y, v in annual.items() if v and v > 0}
            return annual, f"yfinance:{ticker}"
        except Exception:
            continue

    return {}, ""


def wb_usd_per_currency(currency: str, start: int, end: int) -> Tuple[Dict[int, float], str]:
    """Fallback: derive USD per currency from World Bank official FX (LCU per USD)."""
    if currency == "USD":
        return {y: 1.0 for y in range(start, end + 1)}, "fixed"

    ref = CURRENCY_REF_COUNTRY[currency]
    lcu_per_usd = wb_series(ref, FX_IND, start, end)  # local currency per 1 USD
    usd_per_lcu = {y: (1.0 / v) for y, v in lcu_per_usd.items() if v and v > 0}
    return usd_per_lcu, f"worldbank:{FX_IND}:{ref}"


def fill_years(s: Dict[int, float], start: int, end: int) -> Dict[int, float]:
    years = list(range(start, end + 1))
    if not s:
        return {y: math.nan for y in years}
    ser = pd.Series(s).sort_index()
    ser = ser.reindex(years)
    ser = ser.interpolate(limit_direction="both").ffill().bfill()
    return {int(y): float(v) for y, v in ser.items()}


def build() -> dict:
    currencies = sorted({cfg["currency"] for cfg in COUNTRIES.values()})

    # FX table: USD per 1 local currency
    fx_usd_per_ccy: Dict[str, Dict[int, float]] = {}
    fx_sources: Dict[str, str] = {}

    for ccy in currencies:
        yf_vals, yf_src = yfinance_usd_per_currency(ccy, START_YEAR, END_YEAR)
        if yf_vals:
            fx_usd_per_ccy[ccy] = fill_years(yf_vals, START_YEAR, END_YEAR)
            fx_sources[ccy] = yf_src
        else:
            wb_vals, wb_src = wb_usd_per_currency(ccy, START_YEAR, END_YEAR)
            fx_usd_per_ccy[ccy] = fill_years(wb_vals, START_YEAR, END_YEAR)
            fx_sources[ccy] = wb_src

    country_payload = {}
    for code, cfg in COUNTRIES.items():
        m2 = wb_series(cfg["wb"], M2_IND, START_YEAR, END_YEAR)
        m2_growth = wb_series(cfg["wb"], M2_GROWTH_IND, START_YEAR, END_YEAR)
        interest = wb_series(cfg["wb"], INT_RATE_IND, START_YEAR, END_YEAR)

        annual = []
        for y in range(START_YEAR, END_YEAR + 1):
            if y not in m2:
                continue
            annual.append(
                {
                    "year": y,
                    "m2_local": m2[y],
                    "m2_growth_pct": m2_growth.get(y),
                    "lending_rate_pct": interest.get(y),
                }
            )

        country_payload[code] = {
            "name": cfg["name"],
            "wb": cfg["wb"],
            "currency": cfg["currency"],
            "gdpRank": cfg["gdpRank"],
            "annual": annual,
        }

    out = {
        "meta": {
            "generatedAt": datetime.now(UTC).isoformat(),
            "startYear": START_YEAR,
            "endYear": END_YEAR,
            "unitPolicy": "All comparisons rendered as billions of selected base currency.",
            "notes": [
                "M2 proxy uses World Bank broad money (FM.LBL.BMNY.CN).",
                "FX conversion uses yfinance annual average close where available; World Bank PA.NUS.FCRF fallback otherwise.",
                "Cross-country comparability is indicative because national aggregate definitions differ.",
            ],
        },
        "countries": country_payload,
        "fx": {
            "usdPerCurrency": fx_usd_per_ccy,
            "sources": fx_sources,
            "baseCurrencies": BASE_CURRENCIES,
        },
        "events": EVENTS,
        "sources": [
            {
                "name": "World Bank - Broad Money (Current LCU)",
                "url": "https://data.worldbank.org/indicator/FM.LBL.BMNY.CN",
            },
            {
                "name": "World Bank - Broad Money Growth (Annual %)",
                "url": "https://data.worldbank.org/indicator/FM.LBL.BMNY.ZG",
            },
            {
                "name": "World Bank - Official Exchange Rate (LCU per USD)",
                "url": "https://data.worldbank.org/indicator/PA.NUS.FCRF",
            },
            {
                "name": "World Bank - Lending Interest Rate (%)",
                "url": "https://data.worldbank.org/indicator/FR.INR.LEND",
            },
            {
                "name": "Yahoo Finance (yfinance)",
                "url": "https://finance.yahoo.com/",
            },
        ],
    }
    return out


def main() -> None:
    payload = build()
    OUT_DOCS.parent.mkdir(parents=True, exist_ok=True)
    OUT_STATIC.parent.mkdir(parents=True, exist_ok=True)

    txt = json.dumps(payload, indent=2)
    OUT_DOCS.write_text(txt)
    OUT_STATIC.write_text(txt)

    print(f"Wrote: {OUT_DOCS}")
    print(f"Wrote: {OUT_STATIC}")
    print("FX sources:")
    for k, v in payload["fx"]["sources"].items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
