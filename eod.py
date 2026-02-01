import os, json, requests
from datetime import datetime
from zoneinfo import ZoneInfo

STATE_FILE = "state.json"

def compute_unrealized(state):
    ltp = state.get("last_price")
    if not isinstance(ltp, (int, float)):
        return 0.0
    qty = state.get("qty", 0)
    avg = state.get("avg_price", 0.0)
    if qty <= 0:
        return 0.0
    return (ltp - avg) * qty

def send_telegram(text: str):
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        raise RuntimeError("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID secrets")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    requests.post(url, data={"chat_id": chat_id, "text": text}, timeout=20).raise_for_status()

def main():
    with open(STATE_FILE, "r") as f:
        state = json.load(f)

    unreal = compute_unrealized(state)
    realized = float(state.get("realized_pnl", 0.0))
    net = realized + unreal

    ist = ZoneInfo("Asia/Kolkata")
    day = datetime.now(ist).strftime("%Y-%m-%d")

    msg = (
        f"📊 Paper Trading EOD ({day})\n"
        f"Cash: {state.get('cash', 0):.2f}\n"
        f"Position: {state.get('qty', 0)} @ avg {state.get('avg_price', 0):.2f}\n"
        f"Last price: {state.get('last_price')}\n\n"
        f"Realized P/L: {realized:.2f}\n"
        f"Unrealized P/L: {unreal:.2f}\n"
        f"Net P/L: {net:.2f}\n"
    )

    send_telegram(msg)

if __name__ == "__main__":
    main()
