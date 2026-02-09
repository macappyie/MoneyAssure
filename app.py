from flask import Flask, render_template
import pandas as pd
from kiteconnect import KiteConnect
from datetime import datetime, timedelta
import os, time, json

app = Flask(__name__)

API_KEY = "awh2j04pcd83zfvq"
ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN")

kite = KiteConnect(api_key=API_KEY)
kite.set_access_token(ACCESS_TOKEN)

TOP_N = 30
FIRST_FILE = "first_seen.json"

if os.path.exists(FIRST_FILE):
    FIRST = json.load(open(FIRST_FILE))
else:
    FIRST = {}

# Load instruments
df = pd.read_csv("instruments.csv", low_memory=False)
df = df[(df.exchange=="NSE") & (df.instrument_type=="EQ")]
symbol_token = dict(zip(df.tradingsymbol, df.instrument_token))

with open("watchlist.txt") as f:
    WATCHLIST=[x.strip() for x in f if x.strip()]

def fmt(v):
    if v>=1e7: return f"{v/1e7:.2f} Cr"
    if v>=1e5: return f"{v/1e5:.2f} L"
    return str(int(v))

@app.route("/")
def index():
    rows=[]
    today=datetime.now().date()
    tokens=[symbol_token[s] for s in WATCHLIST if s in symbol_token]
    quotes=kite.quote(tokens)

    for s in WATCHLIST:
        try:
            q=quotes[str(symbol_token[s])]
            ltp=q["last_price"]
            prev=q["ohlc"]["close"]
            pct=round(((ltp-prev)/prev)*100,2)
            vol=q.get("volume",0)

            candles=kite.historical_data(symbol_token[s],today,today,"5minute")
            if not candles: continue
            c915=candles[0]

            rows.append({
                "Stock":s,
                "LTP":round(ltp,2),
                "%Chg":pct,
                "9:15 Vol":fmt(c915["volume"]),
                "TY Vol":round(vol/max(c915["volume"],1),2)
            })
            time.sleep(0.2)
        except:
            pass


    dfm=pd.DataFrame(rows)
    gainers=dfm[dfm["%Chg"]>0].sort_values("%Chg",ascending=False).head(TOP_N)
    losers=dfm[dfm["%Chg"]<0].sort_values("%Chg").head(TOP_N)

    now=datetime.now().strftime("%H:%M:%S")
    for _,r in pd.concat([gainers,losers]).iterrows():
        FIRST.setdefault(r["Stock"],now)

    json.dump(FIRST,open(FIRST_FILE,"w"))

    gainers["First Seen"]=gainers["Stock"].map(FIRST)
    losers["First Seen"]=losers["Stock"].map(FIRST)

    return render_template("index.html",
        gainers=gainers.to_dict("records"),
        losers=losers.to_dict("records"),
        time=now
    )

