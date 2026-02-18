#!/usr/bin/env python3
"""Quantitative analysis linking M2 growth with interest and FX dynamics.

Reads docs/data/m2_long_history.json and writes a summary JSON for reporting.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "docs" / "data" / "m2_long_history.json"
OUT_PATH = ROOT / "reports" / "m2_macro_analysis_summary.json"


def safe_corr(a: pd.Series, b: pd.Series) -> float | None:
    z = pd.concat([a, b], axis=1).dropna()
    if len(z) < 5:
        return None
    v = float(z.iloc[:, 0].corr(z.iloc[:, 1]))
    return None if np.isnan(v) else v


def main() -> None:
    payload = json.loads(DATA_PATH.read_text())
    countries = payload["countries"]
    fx = payload["fx"]["usdPerCurrency"]

    rows: List[dict] = []
    for code, info in countries.items():
        ccy = info["currency"]
        fx_ser = pd.Series({int(y): float(v) for y, v in fx[ccy].items()}).sort_index()
        fx_ret = 100.0 * fx_ser.pct_change()  # + => local currency appreciated vs USD

        annual = pd.DataFrame(info["annual"])
        if annual.empty or "year" not in annual.columns:
            continue
        annual = annual.sort_values("year")

        annual["fx_change_pct"] = annual["year"].map(fx_ret)
        annual["m2_growth_lag1"] = annual["m2_growth_pct"].shift(1)
        annual["code"] = code
        annual["country"] = info["name"]
        annual["currency"] = ccy
        rows.extend(annual.to_dict("records"))

    df = pd.DataFrame(rows)

    # Country-level correlations
    corr_rows = []
    for code, g in df.groupby("code"):
        corr_rows.append(
            {
                "code": code,
                "country": g["country"].iloc[0],
                "corr_m2_interest": safe_corr(g["m2_growth_pct"], g["lending_rate_pct"]),
                "corr_m2_fx": safe_corr(g["m2_growth_pct"], g["fx_change_pct"]),
                "obs": int(g[["m2_growth_pct", "lending_rate_pct", "fx_change_pct"]].dropna().shape[0]),
            }
        )

    # Pooled OLS with country dummies
    reg_df = df[["m2_growth_pct", "lending_rate_pct", "fx_change_pct", "m2_growth_lag1", "code"]].dropna().copy()
    y = reg_df["m2_growth_pct"].values

    dummies = pd.get_dummies(reg_df["code"], drop_first=True)
    X_df = pd.concat(
        [
            pd.Series(1.0, index=reg_df.index, name="const"),
            reg_df[["lending_rate_pct", "fx_change_pct", "m2_growth_lag1"]],
            dummies,
        ],
        axis=1,
    )

    X = X_df.values.astype(float)
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    y_hat = X @ beta
    resid = y - y_hat

    n = len(y)
    k = X.shape[1]
    dof = max(n - k, 1)
    sigma2 = float((resid @ resid) / dof)
    xtx_inv = np.linalg.inv(X.T @ X)
    se = np.sqrt(np.diag(sigma2 * xtx_inv))
    t_stats = beta / se

    ss_tot = float(((y - y.mean()) ** 2).sum())
    ss_res = float((resid**2).sum())
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else None

    coeffs = []
    for i, name in enumerate(X_df.columns):
        coeffs.append(
            {
                "variable": name,
                "coef": float(beta[i]),
                "std_err": float(se[i]),
                "t_stat": float(t_stats[i]),
            }
        )

    # Event windows: average M2 growth across countries around key years
    event_stats = []
    years = sorted(df["year"].dropna().unique())
    for ev in payload.get("events", []):
        y0 = int(ev["year"])
        w = df[df["year"].between(y0 - 1, y0 + 1)]
        y_only = df[df["year"] == y0]
        event_stats.append(
            {
                "year": y0,
                "title": ev["title"],
                "mean_m2_growth_event_year": float(y_only["m2_growth_pct"].mean()) if not y_only.empty else None,
                "mean_m2_growth_window_pm1": float(w["m2_growth_pct"].mean()) if not w.empty else None,
                "mean_lending_rate_window_pm1": float(w["lending_rate_pct"].mean()) if not w.empty else None,
                "mean_fx_change_window_pm1": float(w["fx_change_pct"].mean()) if not w.empty else None,
                "obs_window": int(w["m2_growth_pct"].count()),
            }
        )

    # Cross-country summary for recent period
    recent = df[df["year"].between(2015, 2025)]
    recent_summary = (
        recent.groupby(["code", "country"], as_index=False)
        .agg(
            mean_m2_growth_pct=("m2_growth_pct", "mean"),
            mean_lending_rate_pct=("lending_rate_pct", "mean"),
            mean_fx_change_pct=("fx_change_pct", "mean"),
            obs=("year", "count"),
        )
        .sort_values("mean_m2_growth_pct", ascending=False)
    )

    out = {
        "meta": payload.get("meta", {}),
        "sample": {
            "rows": int(len(df)),
            "countries": int(df["code"].nunique()),
            "start_year": int(df["year"].min()),
            "end_year": int(df["year"].max()),
        },
        "country_correlations": corr_rows,
        "pooled_ols": {
            "n_obs": n,
            "n_params": k,
            "r2": r2,
            "coefficients": coeffs,
            "spec": "m2_growth_pct ~ lending_rate_pct + fx_change_pct + m2_growth_lag1 + country_fixed_effects",
        },
        "event_windows": event_stats,
        "recent_summary_2015_2025": recent_summary.to_dict("records"),
    }

    def _sanitize(v):
        if isinstance(v, float) and (np.isnan(v) or np.isinf(v)):
            return None
        if isinstance(v, dict):
            return {k: _sanitize(x) for k, x in v.items()}
        if isinstance(v, list):
            return [_sanitize(x) for x in v]
        return v

    out = _sanitize(out)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(out, indent=2, allow_nan=False))
    print(f"Wrote {OUT_PATH}")
    print(json.dumps(out["sample"], indent=2))
    print("R2:", out["pooled_ols"]["r2"])


if __name__ == "__main__":
    main()
