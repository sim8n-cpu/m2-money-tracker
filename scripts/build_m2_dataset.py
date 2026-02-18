#!/usr/bin/env python3
"""Build long-history M2 dataset with multi-source gap filling.

Primary objective: reduce missing values in M2 level series across major economies.

Data hierarchy:
1) World Bank broad money level (FM.LBL.BMNY.CN)
2) OECD monetary aggregates (M3=MABM, fallback M1=MANM), annual XDC
3) Euro-area aggregate allocation for DE/FR/IT (EA19 * country GDP share in EMU)
4) World Bank growth-chain fill (FM.LBL.BMNY.ZG)
5) Time interpolation / edge carry for residual gaps

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
from statistics import median
from typing import Dict, Tuple
import xml.etree.ElementTree as ET

import pandas as pd
import requests
import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
OUT_DOCS = ROOT / "docs" / "data" / "m2_long_history.json"
OUT_STATIC = ROOT / "static" / "data" / "m2_long_history.json"

WB_API = "https://api.worldbank.org/v2/country/{country}/indicator/{indicator}?format=json&per_page=2000&date={start}:{end}"
OECD_MONAGG_API = "https://sdmx.oecd.org/public/rest/data/DSD_STES@DF_MONAGG/{key}?startPeriod={start}&endPeriod={end}"

M2_IND = "FM.LBL.BMNY.CN"  # Broad money, current LCU
M2_GROWTH_IND = "FM.LBL.BMNY.ZG"  # Broad money growth (annual %)
FX_IND = "PA.NUS.FCRF"  # Official exchange rate (LCU per USD)
INT_RATE_IND = "FR.INR.LEND"  # Lending interest rate (%)
GDP_USD_IND = "NY.GDP.MKTP.CD"  # GDP current US$

START_YEAR = 1980
PROVISIONAL_END_YEAR = datetime.now(UTC).year - 1

COUNTRIES = {
    "US": {"name": "United States", "wb": "US", "currency": "USD", "gdpRank": 1, "oecdArea": "USA"},
    "CN": {"name": "China", "wb": "CN", "currency": "CNY", "gdpRank": 2, "oecdArea": "CHN"},
    "JP": {"name": "Japan", "wb": "JP", "currency": "JPY", "gdpRank": 3, "oecdArea": "JPN"},
    "DE": {"name": "Germany", "wb": "DE", "currency": "EUR", "gdpRank": 4, "oecdArea": None},
    "IN": {"name": "India", "wb": "IN", "currency": "INR", "gdpRank": 5, "oecdArea": "IND"},
    "GB": {"name": "United Kingdom", "wb": "GB", "currency": "GBP", "gdpRank": 6, "oecdArea": "GBR"},
    "FR": {"name": "France", "wb": "FR", "currency": "EUR", "gdpRank": 7, "oecdArea": None},
    "IT": {"name": "Italy", "wb": "IT", "currency": "EUR", "gdpRank": 8, "oecdArea": None},
    "BR": {"name": "Brazil", "wb": "BR", "currency": "BRL", "gdpRank": 9, "oecdArea": "BRA"},
    "CA": {"name": "Canada", "wb": "CA", "currency": "CAD", "gdpRank": 10, "oecdArea": "CAN"},
}

EURO_PROXY_CODES = {"DE", "FR", "IT"}
EA_AREA_CODE = "EA19"
EMU_WB_CODE = "EMU"

CURRENCY_REF_COUNTRY = {
    "USD": "US",
    "EUR": "DE",  # representative euro country for FX fallback
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


def _parse_year(period: str) -> int | None:
    if not period:
        return None
    try:
        return int(period[:4])
    except Exception:
        return None


def fetch_oecd_monetary_annual(measure: str, start: int, end: int) -> Tuple[Dict[str, Dict[int, float]], Dict[str, str]]:
    """Fetch OECD annual monetary aggregate (MABM or MANM) in XDC.

    Query uses wildcard key to avoid per-country rate-limit pressure:
      .A.<MEASURE>.XDC._Z.._Z._Z.N

    Returns:
      area -> {year: value_in_local_currency_units}
      area -> source-tag (includes adjustment preference)
    """

    key = f".A.{measure}.XDC._Z.._Z._Z.N"
    url = OECD_MONAGG_API.format(key=key, start=start, end=end)

    xml_txt = None
    for attempt in range(1, 6):
        try:
            r = requests.get(url, timeout=120)
            if r.status_code == 429:
                # OECD rate limit: gentle backoff
                time.sleep(2.0 * attempt)
                continue
            r.raise_for_status()
            xml_txt = r.text
            break
        except Exception:
            if attempt == 5:
                return {}, {}
            time.sleep(2.0 * attempt)

    ns = {"generic": "http://www.sdmx.org/resources/sdmxml/schemas/v2_1/data/generic"}
    root = ET.fromstring(xml_txt)

    # area -> adj -> year -> value
    raw: Dict[str, Dict[str, Dict[int, float]]] = {}
    for series in root.findall('.//generic:Series', ns):
        sk = series.find('generic:SeriesKey', ns)
        if sk is None:
            continue
        kv = {v.attrib["id"]: v.attrib["value"] for v in sk.findall('generic:Value', ns)}
        area = kv.get("REF_AREA")
        adj = kv.get("ADJUSTMENT", "")
        if not area:
            continue

        attrs = series.find('generic:Attributes', ns)
        unit_mult = 0
        if attrs is not None:
            for a in attrs.findall('generic:Value', ns):
                if a.attrib.get("id") == "UNIT_MULT":
                    try:
                        unit_mult = int(a.attrib.get("value", "0"))
                    except Exception:
                        unit_mult = 0

        s = raw.setdefault(area, {}).setdefault(adj, {})
        for obs in series.findall('generic:Obs', ns):
            d = obs.find('generic:ObsDimension', ns)
            v = obs.find('generic:ObsValue', ns)
            if d is None or v is None:
                continue
            year = _parse_year(d.attrib.get("value", ""))
            if year is None:
                continue
            try:
                val = float(v.attrib.get("value", "nan"))
            except Exception:
                continue
            if not math.isfinite(val):
                continue
            s[year] = val * (10 ** unit_mult)

    collapsed: Dict[str, Dict[int, float]] = {}
    source: Dict[str, str] = {}
    for area, adjs in raw.items():
        years = sorted({y for vals in adjs.values() for y in vals.keys()})
        out = {}
        src = ""
        for y in years:
            if y in adjs.get("N", {}):
                out[y] = adjs["N"][y]
                src = f"oecd:{measure}:adj=N"
            elif y in adjs.get("Y", {}):
                out[y] = adjs["Y"][y]
                src = f"oecd:{measure}:adj=Y"
        if out:
            collapsed[area] = out
            source[area] = src or f"oecd:{measure}"

    return collapsed, source


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
    """Return annual USD per 1 unit of currency using yfinance, or empty dict on failure."""
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
    lcu_per_usd = wb_series(ref, FX_IND, start, end)
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


def fit_scale_factor(wb_level: Dict[int, float], oecd_level: Dict[int, float]) -> float:
    ratios = []
    for y, w in wb_level.items():
        o = oecd_level.get(y)
        if o and o > 0 and w > 0:
            ratios.append(w / o)
    if len(ratios) >= 5:
        return float(median(ratios))
    return 1.0


def fill_from_growth(level: Dict[int, float], growth_pct: Dict[int, float], start: int, end: int, source_map: Dict[int, str]) -> Dict[int, float]:
    out = dict(level)
    changed = True
    while changed:
        changed = False

        # forward chain: y = y-1 * (1+g_y)
        for y in range(start + 1, end + 1):
            if y in out:
                continue
            if (y - 1) in out and y in growth_pct:
                g = growth_pct[y]
                out[y] = out[y - 1] * (1.0 + g / 100.0)
                source_map[y] = source_map.get(y, "growth_chained")
                changed = True

        # backward chain: y = y+1 / (1+g_{y+1})
        for y in range(end - 1, start - 1, -1):
            if y in out:
                continue
            if (y + 1) in out and (y + 1) in growth_pct:
                g_next = growth_pct[y + 1]
                denom = 1.0 + g_next / 100.0
                if denom != 0:
                    out[y] = out[y + 1] / denom
                    source_map[y] = source_map.get(y, "growth_chained")
                    changed = True

    return out


def compute_growth_from_level(level: Dict[int, float], start: int, end: int) -> Dict[int, float]:
    out = {}
    for y in range(start + 1, end + 1):
        if y in level and (y - 1) in level and level[y - 1] != 0:
            out[y] = 100.0 * (level[y] / level[y - 1] - 1.0)
    return out


def choose_final_end_year(country_payload: Dict[str, dict], start: int, provisional_end: int) -> int:
    # Prefer latest year with broad direct-source coverage (non-interpolated).
    direct = {"worldbank", "oecd_m3", "oecd_m1", "oecd_ea19_alloc"}
    n_countries = len(country_payload)

    best = start
    for y in range(start, provisional_end + 1):
        covered = 0
        for _, c in country_payload.items():
            row = next((r for r in c["annual"] if r["year"] == y), None)
            if row and row.get("m2_source") in direct:
                covered += 1
        if covered >= max(5, int(0.6 * n_countries)):
            best = y
    return best


def build() -> dict:
    currencies = sorted({cfg["currency"] for cfg in COUNTRIES.values()})

    # FX table: USD per 1 local currency
    fx_usd_per_ccy: Dict[str, Dict[int, float]] = {}
    fx_sources: Dict[str, str] = {}

    for ccy in currencies:
        yf_vals, yf_src = yfinance_usd_per_currency(ccy, START_YEAR, PROVISIONAL_END_YEAR)
        if yf_vals:
            fx_usd_per_ccy[ccy] = fill_years(yf_vals, START_YEAR, PROVISIONAL_END_YEAR)
            fx_sources[ccy] = yf_src
        else:
            wb_vals, wb_src = wb_usd_per_currency(ccy, START_YEAR, PROVISIONAL_END_YEAR)
            fx_usd_per_ccy[ccy] = fill_years(wb_vals, START_YEAR, PROVISIONAL_END_YEAR)
            fx_sources[ccy] = wb_src

    # OECD monetary aggregates (annual)
    oecd_m3, oecd_m3_src = fetch_oecd_monetary_annual("MABM", START_YEAR, PROVISIONAL_END_YEAR)
    oecd_m1, oecd_m1_src = fetch_oecd_monetary_annual("MANM", START_YEAR, PROVISIONAL_END_YEAR)

    # WB GDP for EMU aggregate (used to split EA19 monetary aggregate across DE/FR/IT)
    gdp_emu_usd = wb_series(EMU_WB_CODE, GDP_USD_IND, START_YEAR, PROVISIONAL_END_YEAR)

    # First pass: gather WB and OECD scales for countries with both
    wb_data = {}
    scale_factors = {}
    for code, cfg in COUNTRIES.items():
        wb_m2 = wb_series(cfg["wb"], M2_IND, START_YEAR, PROVISIONAL_END_YEAR)
        wb_growth = wb_series(cfg["wb"], M2_GROWTH_IND, START_YEAR, PROVISIONAL_END_YEAR)
        wb_interest = wb_series(cfg["wb"], INT_RATE_IND, START_YEAR, PROVISIONAL_END_YEAR)
        wb_gdp_usd = wb_series(cfg["wb"], GDP_USD_IND, START_YEAR, PROVISIONAL_END_YEAR)

        wb_data[code] = {
            "m2": wb_m2,
            "growth": wb_growth,
            "interest": wb_interest,
            "gdp_usd": wb_gdp_usd,
        }

        area = cfg.get("oecdArea")
        if area:
            oecd_base = oecd_m3.get(area) or oecd_m1.get(area) or {}
            scale_factors[code] = fit_scale_factor(wb_m2, oecd_base)

    # Global scale for countries without WB overlap (used for DE/FR/IT synthetic allocation)
    nontrivial_scales = [v for v in scale_factors.values() if v and math.isfinite(v) and v > 0]
    global_scale = float(median(nontrivial_scales)) if nontrivial_scales else 1.0

    country_payload = {}
    for code, cfg in COUNTRIES.items():
        wb_m2 = dict(wb_data[code]["m2"])
        wb_growth = dict(wb_data[code]["growth"])
        wb_interest = dict(wb_data[code]["interest"])
        wb_gdp_usd = dict(wb_data[code]["gdp_usd"])

        source_map: Dict[int, str] = {}
        level = {}

        # 1) WB direct level
        for y, v in wb_m2.items():
            level[y] = v
            source_map[y] = "worldbank"

        # 2) OECD direct level (country-specific)
        area = cfg.get("oecdArea")
        if area:
            base = oecd_m3.get(area)
            src_tag = "oecd_m3"
            if not base:
                base = oecd_m1.get(area)
                src_tag = "oecd_m1"
            if base:
                scale = scale_factors.get(code, 1.0)
                for y, v in base.items():
                    if y not in level:
                        level[y] = v * scale
                        source_map[y] = src_tag

        # 3) DE/FR/IT synthetic from EA19 allocation by GDP share in EMU
        if code in EURO_PROXY_CODES:
            ea = oecd_m3.get(EA_AREA_CODE) or oecd_m1.get(EA_AREA_CODE) or {}
            for y, ea_val in ea.items():
                gc = wb_gdp_usd.get(y)
                ge = gdp_emu_usd.get(y)
                if gc and ge and ge > 0 and y not in level:
                    level[y] = ea_val * (gc / ge) * global_scale
                    source_map[y] = "oecd_ea19_alloc"

        # 4) Growth-chain fill from WB growth
        level = fill_from_growth(level, wb_growth, START_YEAR, PROVISIONAL_END_YEAR, source_map)

        # 5) Residual interpolation/carry
        filled = fill_years(level, START_YEAR, PROVISIONAL_END_YEAR)
        for y in range(START_YEAR, PROVISIONAL_END_YEAR + 1):
            if y not in source_map:
                if y in level:
                    source_map[y] = "growth_chained"
                else:
                    source_map[y] = "interpolated"

        # Growth series: prefer WB, fallback to implied from filled levels
        implied_growth = compute_growth_from_level(filled, START_YEAR, PROVISIONAL_END_YEAR)
        growth_final = {}
        for y in range(START_YEAR, PROVISIONAL_END_YEAR + 1):
            if y in wb_growth:
                growth_final[y] = wb_growth[y]
            elif y in implied_growth:
                growth_final[y] = implied_growth[y]
            else:
                growth_final[y] = None

        annual = []
        for y in range(START_YEAR, PROVISIONAL_END_YEAR + 1):
            annual.append(
                {
                    "year": y,
                    "m2_local": filled.get(y),
                    "m2_growth_pct": growth_final.get(y),
                    "lending_rate_pct": wb_interest.get(y),
                    "m2_source": source_map.get(y),
                }
            )

        country_payload[code] = {
            "name": cfg["name"],
            "wb": cfg["wb"],
            "currency": cfg["currency"],
            "gdpRank": cfg["gdpRank"],
            "annual": annual,
        }

    final_end = choose_final_end_year(country_payload, START_YEAR, PROVISIONAL_END_YEAR)

    # truncate to final_end
    for code in list(country_payload.keys()):
        country_payload[code]["annual"] = [r for r in country_payload[code]["annual"] if r["year"] <= final_end]

    out = {
        "meta": {
            "generatedAt": datetime.now(UTC).isoformat(),
            "startYear": START_YEAR,
            "endYear": final_end,
            "unitPolicy": "All comparisons rendered as billions of selected base currency.",
            "notes": [
                "M2 primary source: World Bank broad money (FM.LBL.BMNY.CN).",
                "Gap-filling source: OECD monetary aggregates (M3=MABM; fallback M1=MANM), annual XDC.",
                "DE/FR/IT gap fill: EA19 aggregate allocated by country GDP share within EMU, then globally calibrated.",
                "Residual gaps are filled via WB growth-chain and interpolation.",
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
                "name": "World Bank - Lending Interest Rate (%)",
                "url": "https://data.worldbank.org/indicator/FR.INR.LEND",
            },
            {
                "name": "OECD SDMX - Monetary Aggregates (DF_MONAGG, MABM/MANM)",
                "url": "https://sdmx.oecd.org/public/rest/dataflow/OECD.SDD.STES/DSD_STES@DF_MONAGG/4.0",
            },
            {
                "name": "World Bank - Official Exchange Rate (LCU per USD)",
                "url": "https://data.worldbank.org/indicator/PA.NUS.FCRF",
            },
            {
                "name": "Yahoo Finance (yfinance)",
                "url": "https://finance.yahoo.com/",
            },
        ],
        "diagnostics": {
            "globalOecdToWbScale": global_scale,
            "countryScaleFactors": scale_factors,
            "oecdAreasAvailableM3": sorted(list(oecd_m3.keys())),
            "oecdAreasAvailableM1": sorted(list(oecd_m1.keys())),
        },
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
    print("Range:", payload["meta"]["startYear"], payload["meta"]["endYear"])
    print("Global OECD->WB scale:", payload["diagnostics"]["globalOecdToWbScale"])
    print("Country scales:")
    for k, v in sorted(payload["diagnostics"]["countryScaleFactors"].items()):
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
