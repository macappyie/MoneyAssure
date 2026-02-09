from flask import Flask, render_template
import pandas as pd
from kiteconnect import KiteConnect
from datetime import datetime
import os, time

app = Flask(__name__)

API_KEY = "awh2j04pcd83zfvq"
ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN")

kite = KiteConnect(api_key=API_KEY)
kite.set_access_token(ACCESS_TOKEN)

# Load instruments
df = pd.read_csv("instruments.csv", low_memory=False)
df = df[(df.exchange=="NSE") & (df.instrument_type=="EQ")]
symbol_token = dict(zip(df.tradingsymbol, df.instrument_token))

with open("watchlist.txt") as f:
    WATCHLIST=[x.strip() for x in f if x.strip()]

TOP_N = 30

@app.route("/")
def index():
    rows=[]
    tokens=[symbol_token[s] for s in WATCHLIST if s in symbol_token]
    quotes=kite.quote(tokens)

    for sym in WATCHLIST:
        try:
            q=quotes[str(symbol_token[sym])]
            ltp=q["last_price"]
            prev=q["ohlc"]["close"]
            pct=round(((ltp-prev)/prev)*100,2)
            rows.append([sym,round(ltp,2),pct])
        except:
            pass

    dfm=pd.DataFrame(rows,columns=["Stock","LTP","Change"])
    gainers=dfm[dfm.Change>0].sort_values("Change",ascending=False).head(TOP_N)
    losers=dfm[dfm.Change<0].sort_values("Change").head(TOP_N)

    return render_template("index.html",
        gainers=gainers.to_dict("records"),
        losers=losers.to_dict("records"),
        time=datetime.now().strftime("%H:%M:%S")
    )

