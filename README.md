# M2 Money Supply Tracker

Long-history tracker for broad money (M2 proxy) across major economies, with conversion into a **single common basis**.

## What this app now does

- Uses long-run annual data (1980 onward, where available)
- Lets user select countries to compare
- Lets user select base currency (USD/EUR/CNY/JPY/GBP/INR)
- Converts all selected series into **billions of base currency** (no mixed trillion/billion basis)
- Shows major economic/political event tags in chart hover tooltips
- Cites public sources directly in the UI

## Data architecture

### Core macro data (World Bank)
- Broad money (current LCU): `FM.LBL.BMNY.CN`
- Broad money growth (annual %): `FM.LBL.BMNY.ZG`
- Lending interest rate (%): `FR.INR.LEND`
- Official exchange rate fallback (LCU per USD): `PA.NUS.FCRF`

### FX conversion data
- Primary: Yahoo Finance via `yfinance`
- Fallback: World Bank `PA.NUS.FCRF`

## Build pipeline

Generate dataset:

```bash
/home/piclaw/.openclaw/workspace/.venv/bin/python scripts/build_m2_dataset.py
```

Output files:
- `docs/data/m2_long_history.json`
- `static/data/m2_long_history.json`

Run quantitative summary used by report:

```bash
/home/piclaw/.openclaw/workspace/.venv/bin/python scripts/analyze_m2_macro_links.py
```

Output:
- `reports/m2_macro_analysis_summary.json`

## Scheduled updater (new)

Use the unified updater function/script:

```bash
/home/piclaw/.openclaw/workspace/.venv/bin/python scripts/update_data.py --strict
```

What it does:
- rebuilds dataset JSON (docs + static)
- reruns macro analysis summary
- writes run summary to `reports/data_update_summary.json`
- in `--strict` mode, exits non-zero if any `m2_local` gaps remain

### Cron example (daily at 06:10)

```bash
10 6 * * * /home/piclaw/.openclaw/workspace/.venv/bin/python /home/piclaw/.openclaw/workspace/m2-money-tracker/scripts/update_data.py --strict >> /home/piclaw/.openclaw/workspace/m2-money-tracker/reports/update_cron.log 2>&1
```

### Python function usage

```python
from scripts.update_data import update_data

summary = update_data(run_analysis=True, strict=True)
print(summary["coverage"]["totalMissingM2"])
```

## Run locally

```bash
pip install -r requirements.txt
python app.py
# open http://localhost:5000
```

## GitHub Pages

The deployed site serves from:
- `docs/index.html`
- `docs/data/m2_long_history.json`

## Notes on comparability

- Even after FX conversion, cross-country money aggregates are only approximately comparable because monetary definitions and financial structures differ.
- Use this as a macro-analytical tool, not a mechanical ranking instrument.

## License

MIT
