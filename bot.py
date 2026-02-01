import os, json
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

STATE_FILE = "state.json"

def load_state():
    with open(STATE_FILE, "r") as f:
        return json.load(f)

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

def is_market_open_ist() -> bool:
    ist = ZoneInfo("Asia/Kolkata")
    now = datetime.now(ist)
    if now.weekday() >= 5:  # Sat/Sun
        return False
    open_t = now.replace(hour=9, minute=15, second=0, microsecond=0)
    close_t = now.replace(hour=15, minute=30, second=0, microsecond=0)
    return open_t <= now <= close_t

def fetch_ltp(token: str, instrument_key: str) -> float:
    url = "https://api.upstox.com/v2/market-quote/quotes"
    headers = {"Accept": "application/json", "Authorization": f"Bearer {token}"}
    r = requests.get(url, headers=headers, params={"instrument_key": instrument_key}, timeout=20)
    if r.status_code == 401:
        raise RuntimeError("Upstox token expired/invalid. Update UPSTOX_ACCESS_TOKEN in GitHub Secrets.")
    r.raise_for_status()
    data = r.json()
    payload = data.get("data", {})
    first_key = next(iter(payload.keys()))
    return float(payload[first_key]["last_price"])

def sma(prices, n):
    return sum(prices[-n:]) / n

def signal(state, short=20, long=50):
    p = state["prices"]
    if len(p) < long + 2:
        return "HOLD"
    s_prev, l_prev = sma(p[:-1], short), sma(p[:-1], long)
    s_now,  l_now  = sma(p, short),    sma(p, long)
    if s_prev <= l_prev and s_now > l_now:
        return "BUY"
    if s_prev >= l_prev and s_now < l_now:
        return "SELL"
    return "HOLD"

def paper_exec(state, action, ltp, qty=1):
    if action == "BUY":
        cost = ltp * qty
        if state["cash"] >= cost:
            new_qty = state["qty"] + qty
            state["avg_price"] = ((state["avg_price"] * state["qty"]) + (ltp * qty)) / new_qty
            state["qty"] = new_qty
            state["cash"] -= cost
    elif action == "SELL":
        if state["qty"] >= qty:
            state["realized_pnl"] += (ltp - state["avg_price"]) * qty
            state["qty"] -= qty
            state["cash"] += ltp * qty
            if state["qty"] == 0:
                state["avg_price"] = 0.0

def main():
    token = os.environ["UPSTOX_ACCESS_TOKEN"].strip()
    key = os.environ["UPSTOX_INSTRUMENT_KEY"].strip()

    # Only trade during NSE hours (IST)
    # if not is_market_open_ist():
    #     return

    if not is_market_open_ist():
    state = load_state()
    state["last_price"] = "MARKET_CLOSED"
    save_state(state)
    return


    state = load_state()
    ltp = fetch_ltp(token, key)
    state["last_price"] = ltp

    state["prices"].append(ltp)
    state["prices"] = state["prices"][-200:]

    act = signal(state, 20, 50)
    paper_exec(state, act, ltp, qty=1)

    save_state(state)

if __name__ == "__main__":
    main()
