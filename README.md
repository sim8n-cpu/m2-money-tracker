# M2 Money Supply Tracker

A web application that tracks and visualizes M2 money supply data for the world's largest economies.

## Overview

This application provides:
- **Real-time M2 visualization** for major economies (US, China, EU, Japan, UK)
- **Interactive comparison** - Select any combination of countries
- **Historical trends** - View M2 data from 2018 to present
- **Cited sources** - All data clearly attributed to official central bank sources

## Features

### 🌍 Country Coverage
| Country | Currency | Data Source |
|---------|----------|-------------|
| United States | USD | Federal Reserve |
| China | CNY | People's Bank of China |
| Euro Area | EUR | European Central Bank |
| Japan | JPY | Bank of Japan |
| United Kingdom | GBP | Bank of England |

### 📊 Visualizations
- **Time Series Chart** - Track M2 growth over time
- **Bar Chart** - Compare latest values across selected countries

## Data Sources

All data is sourced from official public sources:

1. **Federal Reserve Economic Data (FRED)** - US M2 Money Stock
   - https://fred.stlouisfed.org/series/M2SL

2. **European Central Bank** - M2 for Euro Area
   - https://www.ecb.europa.eu/stats/

3. **People's Bank of China** - Money Supply Statistics
   - http://www.pbc.gov.cn/en/

4. **Bank of Japan** - Money Stock
   - https://www.boj.or.jp/en/statistics/ms/ms.htm

5. **Bank of England** - M2 Money Supply
   - https://www.bankofengland.co.uk/statistics

6. **World Bank** - Global Money Supply Data
   - https://data.worldbank.org/indicator/FM.LBL.MQMY.CN

## Disclaimer

> Data shown is approximate and based on historical records from public sources. Different countries define and measure M2 differently. For precise comparisons, consider exchange rates and purchasing power parity. This tool is for educational purposes only.

## Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py

# Open browser to http://localhost:5000
```

## Technologies

- **Backend**: Python Flask
- **Frontend**: Vanilla JavaScript with Chart.js
- **Data**: Public APIs from central banks

## License

MIT License - Free for educational and research purposes.
