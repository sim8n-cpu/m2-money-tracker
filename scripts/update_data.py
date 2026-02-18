#!/usr/bin/env python3
"""Scheduled update entrypoint for the M2 tracker dataset.

This script exposes an `update_data()` function so it can be:
- called directly from Python
- run from cron/systemd timers
- triggered from CI/CD workflows

Behavior:
1) rebuilds docs/static data JSON via build_m2_dataset.build()
2) optionally re-runs macro analysis summary
3) writes a machine-readable update summary
4) optionally fails fast if missing values remain
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import build_m2_dataset as build_mod  # noqa: E402
import analyze_m2_macro_links as analysis_mod  # noqa: E402

DATA_DOCS = ROOT / "docs" / "data" / "m2_long_history.json"
DATA_STATIC = ROOT / "static" / "data" / "m2_long_history.json"
SUMMARY_DEFAULT = ROOT / "reports" / "data_update_summary.json"


def _is_valid_number(x: Any) -> bool:
    return isinstance(x, (int, float)) and math.isfinite(float(x))


def _coverage_summary(payload: dict) -> dict:
    start = int(payload["meta"]["startYear"])
    end = int(payload["meta"]["endYear"])
    expected_years = end - start + 1

    countries = payload["countries"]
    by_country: Dict[str, dict] = {}
    total_missing_m2 = 0

    for code, c in countries.items():
        annual = c.get("annual", [])
        valid_m2 = sum(1 for r in annual if _is_valid_number(r.get("m2_local")))
        valid_growth = sum(1 for r in annual if _is_valid_number(r.get("m2_growth_pct")))
        missing_m2 = expected_years - valid_m2

        total_missing_m2 += max(missing_m2, 0)
        by_country[code] = {
            "rows": len(annual),
            "expected_rows": expected_years,
            "valid_m2": valid_m2,
            "valid_growth": valid_growth,
            "missing_m2": max(missing_m2, 0),
            "first_year": annual[0]["year"] if annual else None,
            "last_year": annual[-1]["year"] if annual else None,
        }

    return {
        "startYear": start,
        "endYear": end,
        "expectedYearsPerCountry": expected_years,
        "countryCount": len(countries),
        "totalMissingM2": total_missing_m2,
        "byCountry": by_country,
    }


def update_data(
    *,
    run_analysis: bool = True,
    strict: bool = False,
    summary_path: Path = SUMMARY_DEFAULT,
) -> dict:
    """Run full update pipeline and return update summary.

    Args:
      run_analysis: regenerate reports/m2_macro_analysis_summary.json
      strict: raise RuntimeError if any m2_local values remain missing
      summary_path: path for generated run summary JSON
    """

    print("[update] rebuilding dataset...")
    payload = build_mod.build()

    DATA_DOCS.parent.mkdir(parents=True, exist_ok=True)
    DATA_STATIC.parent.mkdir(parents=True, exist_ok=True)

    txt = json.dumps(payload, indent=2)
    DATA_DOCS.write_text(txt)
    DATA_STATIC.write_text(txt)

    print(f"[update] wrote {DATA_DOCS}")
    print(f"[update] wrote {DATA_STATIC}")

    if run_analysis:
        print("[update] running macro analysis summary...")
        analysis_mod.main()

    coverage = _coverage_summary(payload)

    summary = {
        "updatedAt": datetime.now(UTC).isoformat(),
        "dataFiles": {
            "docs": str(DATA_DOCS),
            "static": str(DATA_STATIC),
        },
        "ranAnalysis": run_analysis,
        "coverage": coverage,
        "notes": [
            "Generated via scripts/update_data.py",
            "Use strict=true for scheduled runs that must fail on residual missing M2.",
        ],
    }

    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2))
    print(f"[update] wrote summary {summary_path}")

    print(
        "[update] coverage: "
        f"{coverage['startYear']}–{coverage['endYear']}, "
        f"countries={coverage['countryCount']}, "
        f"totalMissingM2={coverage['totalMissingM2']}"
    )

    if strict and coverage["totalMissingM2"] > 0:
        raise RuntimeError(
            f"Strict mode failed: totalMissingM2={coverage['totalMissingM2']}"
        )

    return summary


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Update M2 dataset + optional analysis")
    p.add_argument(
        "--skip-analysis",
        action="store_true",
        help="skip analyze_m2_macro_links.py",
    )
    p.add_argument(
        "--strict",
        action="store_true",
        help="exit non-zero if any missing m2_local values remain",
    )
    p.add_argument(
        "--summary-path",
        default=str(SUMMARY_DEFAULT),
        help="path to write run summary JSON",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    update_data(
        run_analysis=not args.skip_analysis,
        strict=args.strict,
        summary_path=Path(args.summary_path),
    )


if __name__ == "__main__":
    main()
