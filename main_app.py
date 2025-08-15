import streamlit as st
import requests
import pandas as pd
import hmac
import hashlib
import time
from datetime import datetime, timedelta, timezone
import importlib

# ====== Load Logic Module Dynamically ======
logic = importlib.import_module("logic")

# ====== Custom UI Styling ======
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Source+Code+Pro&display=swap" rel="stylesheet">
<style>
.stApp {
    background-color: #0e1117;
    color: white;
    font-family: 'Source Code Pro', monospace;
}
thead tr th {
    background-color: #1e1e1e !important;
    color: #cccccc !important;
}
tbody tr td {
    background-color: #0e1117 !important;
    color: white !important;
    font-family: 'Source Code Pro', monospace;
}
.green-cell {
    background-color: #137333 !important;
    color: white !important;
    font-weight: bold;
    text-align: right;
}
.red-cell {
    background-color: #a50e0e !important;
    color: white !important;
    font-weight: bold;
    text-align: right;
}
</style>
""", unsafe_allow_html=True)

# ==============================
# Helper Styling Function
# ==============================
def highlight_values(val):
    try:
        if val > 0:
            return 'background-color: #137333; color: white; font-weight: bold;'
        elif val < 0:
            return 'background-color: #a50e0e; color: white; font-weight: bold;'
    except:
        return ''
    return ''

# ==============================
# BTC Tracker
# ==============================
class BTCPriceTracker:
    def __init__(self, debug=False):
        self.base_url = "https://api.delta.exchange"
        self.symbol = "BTCUSDT"
        self.debug = debug
        try:
            self.api_key = st.secrets["btc_tracker"]["DELTA_API_KEY"]
            self.api_secret = st.secrets["btc_tracker"]["DELTA_API_SECRET"]
        except KeyError as e:
            st.error(f"❌ Missing API credential: {e}")
            st.stop()

    def get_current_price(self):
        try:
            url = f"{self.base_url}/v2/tickers/{self.symbol}"
            response = requests.get(url, timeout=10)
            data = response.json()
            if data.get('success') and data.get('result'):
                return float(data['result']['close'])
        except Exception as e:
            st.error(f"Error fetching current price: {e}")
        return None

    def get_exact_candle_close(self, target_datetime):
        try:
            end_time = int(target_datetime.replace(tzinfo=timezone.utc).timestamp())
            start_time = end_time - 60
            params = {
                "symbol": self.symbol,
                "resolution": "1m",
                "start": start_time,
                "end": end_time
            }
            url = f"{self.base_url}/v2/history/candles"
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            if data.get("success") and "result" in data:
                candles = data["result"]
                if candles:
                    return float(candles[-1]["close"])
        except Exception as e:
            st.error(f"Error fetching historical price: {e}")
        return None

    def calculate_percentage_change(self, old_price, new_price):
        if old_price is None or new_price is None:
            return None
        return ((new_price - old_price) / old_price) * 100

# ==============================
# Options Chain Fetch
# ==============================
class DeltaExchangeAPI:
    def __init__(self, api_key, api_secret, base_url="https://api.india.delta.exchange"):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url

    def _generate_signature(self, method, endpoint, payload=""):
        timestamp = str(int(time.time()))
        message = method + timestamp + endpoint + payload
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature, timestamp

    def _make_request(self, method, endpoint, params=None):
        url = f"{self.base_url}{endpoint}"
        payload = ""
        if method == "GET" and params:
            sorted_params = sorted(params.items())
            payload = "&".join([f"{k}={v}" for k, v in sorted_params])
        signature, timestamp = self._generate_signature(method, endpoint, payload)
        headers = {
            "api-key": self.api_key,
            "signature": signature,
            "timestamp": timestamp,
            "Content-Type": "application/json"
        }
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            return response.json()
        except Exception as e:
            st.error(f"API request failed: {str(e)}")
            return None

    def get_products(self):
        return self._make_request("GET", "/v2/products")

    def get_tickers(self):
        return self._make_request("GET", "/v2/tickers")

@st.cache_data(ttl=300)
def fetch_options_data(api_key, api_secret, base_url):
    api = DeltaExchangeAPI(api_key, api_secret, base_url)
    products_response = api.get_products()
    tickers_response = api.get_tickers()

    if not products_response or 'result' not in products_response:
        return None, None

    products = products_response['result']
    ticker_data = {}
    if tickers_response and 'result' in tickers_response:
        for ticker in tickers_response['result']:
            ticker_data[ticker.get('symbol')] = ticker

    options = []
    for product in products:
        if product.get('contract_type') in ['call_options', 'put_options'] and product.get('underlying_asset', {}).get('symbol') == 'BTC':
            symbol = product.get('symbol')
            if symbol in ticker_data:
                product.update(ticker_data[symbol])
            options.append(product)

    if not options:
        return None, None

    sorted_opts = sorted(options, key=lambda x: x.get('settlement_time', '9999'))
    nearest_expiry = sorted_opts[0].get('settlement_time')
    nearest_expiry_options = [opt for opt in sorted_opts if opt.get('settlement_time') == nearest_expiry]

    return nearest_expiry_options, nearest_expiry

def create_options_chain_table(options):
    calls = [opt for opt in options if opt.get('contract_type') == 'call_options']
    puts = [opt for opt in options if opt.get('contract_type') == 'put_options']

    strikes = {}
    for call in calls:
        strike = call.get('strike_price', 0)
        strikes.setdefault(strike, {})['call'] = call
    for put in puts:
        strike = put.get('strike_price', 0)
        strikes.setdefault(strike, {})['put'] = put

    chain_data = []
    for strike in sorted(strikes.keys()):
        call_data = strikes[strike].get('call', {})
        put_data = strikes[strike].get('put', {})
        chain_data.append({
            'Strike': strike,
            'Call_Symbol': call_data.get('symbol', ''),
            'Call_Price': call_data.get('mark_price', 0),
            'Put_Symbol': put_data.get('symbol', ''),
            'Put_Price': put_data.get('mark_price', 0)
        })

    return pd.DataFrame(chain_data)

# ==============================
# Main App
# ==============================
def main():
    st.set_page_config(page_title="BTC Price & Options", layout="wide")
    st.title("₿ BTC Price Tracker + Strategy Runner")

    # Load API keys
    try:
        api_key = st.secrets["delta_exchange"]["api_key"]
        api_secret = st.secrets["delta_exchange"]["api_secret"]
        base_url = st.secrets["delta_exchange"].get("base_url", "https://api.india.delta.exchange")
    except KeyError as e:
        st.error(f"Missing secret: {e}")
        st.stop()

    # BTC Price
    tracker = BTCPriceTracker()
    current_price = tracker.get_current_price()
    today = datetime.now()
    am_time_utc = datetime(today.year, today.month, today.day, 5, 29, 0) - timedelta(hours=5, minutes=30)
    am_price = tracker.get_exact_candle_close(am_time_utc)

    am_change = tracker.calculate_percentage_change(am_price, current_price) if am_price else None
    st.metric("Current BTC Futures Price", f"${current_price:,.2f}", delta=f"{am_change:+.2f}%" if am_change else "N/A")

    # Options Chain
    options, expiry = fetch_options_data(api_key, api_secret, base_url)
    if options:
        chain_df = create_options_chain_table(options)
        chain_df['Strike'] = pd.to_numeric(chain_df['Strike'], errors='coerce')
        chain_df['Call_Price'] = pd.to_numeric(chain_df['Call_Price'], errors='coerce')
        chain_df['Put_Price'] = pd.to_numeric(chain_df['Put_Price'], errors='coerce')

        st.subheader(f"BTC Options Chain (Nearest Expiry: {expiry})")
        st.dataframe(chain_df, use_container_width=True)

        # Run strategy from logic.py dynamically
        if hasattr(logic, "run_strategy"):
            result = logic.run_strategy(chain_df, current_price, am_price)
            st.subheader("📢 Strategy Signal")
            st.write(result.get("signal", "No signal output."))

            if result.get("details") is not None:
                st.dataframe(pd.DataFrame([result["details"]]), use_container_width=True)
        else:
            st.error("No function 'run_strategy' found in logic.py. Please define it.")

    else:
        st.warning("No BTC options data available.")

if __name__ == "__main__":
    main()
