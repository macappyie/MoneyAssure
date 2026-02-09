from flask import Flask, render_template, jsonify
import pandas as pd
from kiteconnect import KiteConnect
from datetime import datetime, timedelta, time as dtime
import time
import json
import os

app = Flask(__name__)

# ================= CONFIG =================
API_KEY = "awh2j04pcd83zfvq"

# ACCESS TOKEN FROM RENDER ENV
ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN")

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
            c10 = next((c for c in candles if c["date"].strftime("%H:%M")=="10:00"),None)
            c12 = next((c for c in candles if c["date"].strftime("%H:%M")=="12:00"),None)

            from_date = today - timedelta(days=15)
            vols = kite.historical_data(token, from_date, today- timedelta(days=1),"day")

            avg_raw = 0
            if len(vols)>=7:
                avg_raw = sum([v["volume"] for v in vols[-7:]])/7


            rows.append({
                "symbol":sym,
                "ltp":round(ltp,2),
                "change":pct,
                "avg_vol":fmt_vol(avg_raw),
                "vol_915":fmt_vol(c915["volume"]),
                "ty_vol": f"{round(total_vol/avg_raw,2)}x" if avg_raw>0 else "",
                "ty_vol_num": round(total_vol/avg_raw,2) if avg_raw>0 else 0,
                "pct_915_high":round(((c915["high"]-prev_close)/prev_close)*100,2),
                "pct_915_low":round(((c915["low"]-prev_close)/prev_close)*100,2),
                "pct_10_high":round(((c10["high"]-prev_close)/prev_close)*100,2) if c10 else "",
                "pct_10_low":round(((c10["low"]-prev_close)/prev_close)*100,2) if c10 else "",
                "pct_12_high":round(((c12["high"]-prev_close)/prev_close)*100,2) if c12 else "",
                "pct_12_low":round(((c12["low"]-prev_close)/prev_close)*100,2) if c12 else "",
                "total_vol":fmt_vol(total_vol)
            })

            time.sleep(0.1)
        except:
            continue

    dfm = pd.DataFrame(rows)

    # TOP 10 ONLY
    gainers = dfm[dfm["change"]>0].sort_values("change",ascending=False).head(10)
    losers = dfm[dfm["change"]<0].sort_values("change").head(10)

    now = datetime.now().strftime("%H:%M:%S")

    for _,r in pd.concat([gainers,losers]).iterrows():
        if r["symbol"] not in FIRST_SEEN:
            FIRST_SEEN[r["symbol"]] = now

    with open(FIRST_SEEN_FILE,"w") as f:
        json.dump(FIRST_SEEN,f)

    gainers["first_seen"]=gainers["symbol"].map(FIRST_SEEN)
    losers["first_seen"]=losers["symbol"].map(FIRST_SEEN)

    return render_template(
        "index.html",
        gainers=gainers.to_dict("records"),
        losers=losers.to_dict("records")
    )

# ================= CHART =================
@app.route("/chart/<symbol>")
def chart(symbol):
    return render_template("chart.html",symbol=symbol)

@app.route("/api/candles/<symbol>")
def api_candles(symbol):

    if symbol not in symbol_token:
        return jsonify({"candles":[], "sma20":[], "sma50":[], "line10":None})

    token = symbol_token[symbol]
    to_date = datetime.now().date()
    from_date = to_date - timedelta(days=5)

    candles = kite.historical_data(token,from_date,to_date,"5minute")

    chart=[]
    closes=[]
    times=[]
    high10=None

    for c in candles:
        t=c["date"].time()
        if t<dtime(9,15) or t>dtime(15,30):
            continue

        ts=int(c["date"].timestamp())
        chart.append({
            "time":ts,
            "open":c["open"],
            "high":c["high"],
            "low":c["low"],
            "close":c["close"]
        })

        closes.append(c["close"])
        times.append(ts)

        if c["date"].strftime("%H:%M")=="10:00":
            high10=c["high"]

    sma20=[]
    sma50=[]

    for i in range(len(closes)):
        if i>=19:
            sma20.append({"time":times[i],"value":sum(closes[i-19:i+1])/20})
        if i>=49:
            sma50.append({"time":times[i],"value":sum(closes[i-49:i+1])/50})

    return jsonify({
        "candles":chart,
        "sma20":sma20,
        "sma50":sma50,
        "line10":high10
    })

if __name__=="__main__":
    app.run()

