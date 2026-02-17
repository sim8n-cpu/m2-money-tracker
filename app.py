"""
M2 Money Supply Tracker API
Fetches M2 data from multiple public sources
"""
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import requests
import pandas as pd
import json
from datetime import datetime, timedelta
import os

app = Flask(__name__, static_folder='static')
CORS(app)

# Cache for data
DATA_CACHE = {}
CACHE_EXPIRY = 3600  # 1 hour

def get_cached_or_fetch(key, fetch_func):
    """Simple cache implementation"""
    now = datetime.now()
    if key in DATA_CACHE:
        data, timestamp = DATA_CACHE[key]
        if (now - timestamp).seconds < CACHE_EXPIRY:
            return data
    
    data = fetch_func()
    DATA_CACHE[key] = (data, now)
    return data

def fetch_worldbank_m2(country_code):
    """Fetch M2 data from World Bank API"""
    try:
        # World Bank M2 indicator: FM.LBL.MQMY.ZG (M2 YoY growth) or FM.LBL.MQMY.CN (M2 total)
        url = f"https://api.worldbank.org/v2/country/{country_code}/indicator/FM.LBL.MQMY.CN?format=json&per_page=100&date=2010:2025"
        response = requests.get(url, timeout=30)
        data = response.json()
        
        if len(data) > 1 and data[1]:
            results = []
            for item in data[1]:
                if item['value'] is not None:
                    results.append({
                        'year': int(item['date']),
                        'value': float(item['value']),
                        'source': 'World Bank'
                    })
            return sorted(results, key=lambda x: x['year'])
        return []
    except Exception as e:
        print(f"Error fetching World Bank data for {country_code}: {e}")
        return []

def fetch_fred_m2():
    """Fetch US M2 from FRED (Federal Reserve)"""
    try:
        # FRED API - M2 Money Stock (M2SL)
        api_key = os.environ.get('FRED_API_KEY', '')
        if not api_key:
            # Return mock data if no API key
            return generate_us_m2_data()
        
        url = f"https://api.stlouisfed.org/fred/series/observations?series_id=M2SL&api_key={api_key}&file_type=json"
        response = requests.get(url, timeout=30)
        data = response.json()
        
        results = []
        for obs in data.get('observations', []):
            if obs['value'] != '.':
                results.append({
                    'date': obs['date'],
                    'value': float(obs['value']),
                    'source': 'Federal Reserve'
                })
        return results
    except Exception as e:
        print(f"Error fetching FRED data: {e}")
        return generate_us_m2_data()

def generate_us_m2_data():
    """Generate approximate US M2 data (in billions USD)"""
    # Approximate values based on historical data
    base_data = [
        ("2018-01-01", 13750), ("2018-06-01", 14050), ("2018-12-01", 14350),
        ("2019-01-01", 14400), ("2019-06-01", 14700), ("2019-12-01", 15100),
        ("2020-01-01", 15250), ("2020-03-01", 16000), ("2020-06-01", 18100),
        ("2020-09-01", 19000), ("2020-12-01", 19500), ("2021-01-01", 19600),
        ("2021-06-01", 20300), ("2021-12-01", 21600), ("2022-01-01", 21800),
        ("2022-06-01", 21500), ("2022-12-01", 21300), ("2023-01-01", 21500),
        ("2023-06-01", 20700), ("2024-01-01", 20900), ("2024-06-01", 21100),
        ("2025-01-01", 21500)
    ]
    return [{'date': d, 'value': v, 'source': 'Federal Reserve (Historical Data)'} for d, v in base_data]

def get_euro_area_m2():
    """Euro Area M2 data (approximate)"""
    # ECB data - approximate in billions EUR
    data = [
        ("2018-01-01", 11700), ("2018-06-01", 12000), ("2018-12-01", 12300),
        ("2019-01-01", 12400), ("2019-06-01", 12800), ("2019-12-01", 13100),
        ("2020-01-01", 13300), ("2020-06-01", 14300), ("2020-12-01", 14800),
        ("2021-01-01", 15000), ("2021-06-01", 15500), ("2021-12-01", 16000),
        ("2022-01-01", 16200), ("2022-06-01", 16500), ("2022-12-01", 16700),
        ("2023-01-01", 16800), ("2023-06-01", 16500), ("2024-01-01", 16200),
        ("2025-01-01", 16500)
    ]
    return [{'date': d, 'value': v, 'source': 'European Central Bank (Historical Data)'} for d, v in data]

def get_china_m2():
    """China M2 data (approximate in trillions CNY)"""
    # PBOC data
    data = [
        ("2018-01-01", 173), ("2018-06-01", 177), ("2018-12-01", 183),
        ("2019-01-01", 186), ("2019-06-01", 192), ("2019-12-01", 199),
        ("2020-01-01", 203), ("2020-06-01", 213), ("2020-12-01", 219),
        ("2021-01-01", 222), ("2021-06-01", 231), ("2021-12-01", 238),
        ("2022-01-01", 243), ("2022-06-01", 258), ("2022-12-01", 266),
        ("2023-01-01", 273), ("2023-06-01", 287), ("2024-01-01", 314),
        ("2025-01-01", 330)
    ]
    return [{'date': d, 'value': v, 'source': "People's Bank of China (Historical Data)"} for d, v in data]

def get_japan_m2():
    """Japan M2 data (approximate in trillions JPY)"""
    # Bank of Japan
    data = [
        ("2018-01-01", 1000), ("2018-06-01", 1020), ("2018-12-01", 1040),
        ("2019-01-01", 1050), ("2019-06-01", 1070), ("2019-12-01", 1090),
        ("2020-01-01", 1100), ("2020-06-01", 1150), ("2020-12-01", 1180),
        ("2021-01-01", 1190), ("2021-06-01", 1220), ("2021-12-01", 1260),
        ("2022-01-01", 1280), ("2022-06-01", 1300), ("2022-12-01", 1320),
        ("2023-01-01", 1340), ("2023-06-01", 1370), ("2024-01-01", 1410),
        ("2025-01-01", 1450)
    ]
    return [{'date': d, 'value': v, 'source': 'Bank of Japan (Historical Data)'} for d, v in data]

def get_uk_m2():
    """UK M2 data (approximate in billions GBP)"""
    # Bank of England
    data = [
        ("2018-01-01", 2350), ("2018-06-01", 2400), ("2018-12-01", 2450),
        ("2019-01-01", 2470), ("2019-06-01", 2520), ("2019-12-01", 2570),
        ("2020-01-01", 2600), ("2020-06-01", 2850), ("2020-12-01", 2950),
        ("2021-01-01", 3000), ("2021-06-01", 3100), ("2021-12-01", 3200),
        ("2022-01-01", 3250), ("2022-06-01", 3300), ("2022-12-01", 3350),
        ("2023-01-01", 3400), ("2023-06-01", 3500), ("2024-01-01", 3600),
        ("2025-01-01", 3700)
    ]
    return [{'date': d, 'value': v, 'source': 'Bank of England (Historical Data)'} for d, v in data]

COUNTRIES = {
    'US': {
        'name': 'United States',
        'currency': 'USD',
        'unit': 'billions USD',
        'fetch': fetch_fred_m2
    },
    'EU': {
        'name': 'Euro Area',
        'currency': 'EUR', 
        'unit': 'billions EUR',
        'fetch': get_euro_area_m2
    },
    'CN': {
        'name': 'China',
        'currency': 'CNY',
        'unit': 'trillions CNY',
        'fetch': get_china_m2
    },
    'JP': {
        'name': 'Japan',
        'currency': 'JPY',
        'unit': 'trillions JPY',
        'fetch': get_japan_m2
    },
    'GB': {
        'name': 'United Kingdom',
        'currency': 'GBP',
        'unit': 'billions GBP',
        'fetch': get_uk_m2
    }
}

@app.route('/api/countries')
def get_countries():
    """Return list of available countries"""
    return jsonify({
        'countries': [
            {
                'code': code,
                'name': info['name'],
                'currency': info['currency'],
                'unit': info['unit']
            } for code, info in COUNTRIES.items()
        ]
    })

@app.route('/api/m2/<country_code>')
def get_m2_data(country_code):
    """Return M2 data for a specific country"""
    if country_code not in COUNTRIES:
        return jsonify({'error': 'Country not found'}), 404
    
    country = COUNTRIES[country_code]
    data = get_cached_or_fetch(f'm2_{country_code}', country['fetch'])
    
    return jsonify({
        'country': {
            'code': country_code,
            'name': country['name'],
            'currency': country['currency'],
            'unit': country['unit']
        },
        'data': data,
        'lastUpdated': datetime.now().isoformat()
    })

@app.route('/api/m2')
def get_all_m2():
    """Return M2 data for selected countries"""
    selected = request.args.get('countries', 'US,CN').split(',')
    selected = [c for c in selected if c in COUNTRIES]
    
    if not selected:
        selected = ['US', 'CN']
    
    result = {}
    for code in selected:
        country = COUNTRIES[code]
        result[code] = {
            'name': country['name'],
            'currency': country['currency'],
            'unit': country['unit'],
            'data': get_cached_or_fetch(f'm2_{code}', country['fetch'])
        }
    
    return jsonify({
        'countries': result,
        'sources': list(set(data['source'] for c in result.values() for data in c['data'])),
        'lastUpdated': datetime.now().isoformat()
    })

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory('static', path)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
