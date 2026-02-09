from flask import Flask, render_template, jsonify
import pandas as pd
from kiteconnect import KiteConnect
from datetime import datetime, timedelta, time as dtime
import time, json, os

app = Flask(__name__)

# ================= CONFIG =================
API_KEY = "awh2j04pcd83zfvq"

ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN")
if not ACCESS_TOKEN:
    raise Exception("ACCESS_TOKEN environment variable not set")

kite = KiteConnect(api_key=API_KEY)
kite.set_access_token(ACCESS_TOKEN)

# ================= FIRST SEEN =================
FIRST_SEEN_FILE = "first_seen.json"

if os.path.exists(FIRST_SEEN_FILE):
    with open(FIRST_SEEN_FILE) as f:
        FIRST_SEEN = json.load(f)
else:
    FIRST_SEEN = {}

# ================= LOAD INSTRUMENTS =================
df = pd.read_csv("instruments.csv", low_memory=False)
df = df[(df.exchange == "NSE") & (df.instrument_type == "EQ")]
symbol_token = dict(zip(df.tradingsymbol, df.instrument_token))

with open("watchlist.txt") as f:
    WATCHLIST = [x.strip() for x in f if x.strip()]

# ================= HELPERS =================
def fmt_vol(v):
    if v >= 1e7: return f"{v/1e7:.2f} Cr"
    if v >= 1e5: return f"{v/1e5:.2f} L"
    if v >= 1e3: return f"{v/1e3:.1f} K"
    return str(int(v))

# ================= INDEX =================
@app.route("/")
def index():

    rows = []
    today = datetime.now().date()

    tokens = [symbol_token[s] for s in WATCHLIST if s in symbol_token]
    quotes = kite.quote(tokens)

    for sym in WATCHLIST:
        try:
            token = symbol_token[sym]
            q = quotes[str(token)]

            ltp = q["last_price"]
            prev_close = q["ohlc"]["close"]
            pct = round(((ltp-prev_close)/prev_close)*100,2)
            total_vol = q.get("volume",0)

            candles = kite.historical_data(token, today, today, "5minute")
            if not candles:
                continue

            c915 = candles[0]

            rows.append({
                "symbol": sym,
                "ltp": round(ltp,2),
                "change": pct,
                "vol_915": fmt_vol(c915["volume"]),
                "total_vol": fmt_vol(total_vol)
            })

            time.sleep(0.2)
        except:
            pass

    dfm = pd.DataFrame(rows)



    gainers = dfm[dfm["change"]>0].sort_values("change",ascending=False).head(20)
    losers  = dfm[dfm["change"]<0].sort_values("change").head(20)

    return render_template(
        "index.html",
        gainers=gainers.to_dict("records"),
        losers=losers.to_dict("records")
    )

# ================= API FOR CHART =================
@app.route("/api/candles/<symbol>")
def api_candles(symbol):

    if symbol not in symbol_token:
        return jsonify({"candles": []})

    token = symbol_token[symbol]
    to_date = datetime.now().date()
    from_date = to_date - timedelta(days=3)

    candles = kite.historical_data(token, from_date, to_date, "5minute")

    chart = []

    for c in candles:
        t = c["date"].time()
        if t < dtime(9,15) or t > dtime(15,30):
            continue

        chart.append({
            "time": int(c["date"].timestamp()),
            "open": c["open"],
            "high": c["high"],
            "low": c["low"],
            "close": c["close"]
        })

    return jsonify({"candles": chart})

