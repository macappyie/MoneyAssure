from flask import Flask, render_template
import pandas as pd
from kiteconnect import KiteConnect

app = Flask(__name__)

# ================= CONFIG =================
API_KEY = "awh2j04pcd83zfvq"
with open("access_token.txt") as f:
    ACCESS_TOKEN = f.read().strip()

kite = KiteConnect(api_key=API_KEY)
kite.set_access_token(ACCESS_TOKEN)

# ================= LOAD INSTRUMENTS =================
df = pd.read_csv("instruments.csv", low_memory=False)
df = df[(df.exchange == "NSE") & (df.instrument_type == "EQ")]
symbol_token = dict(zip(df.tradingsymbol, df.instrument_token))

with open("watchlist.txt") as f:
    WATCHLIST = [x.strip() for x in f if x.strip()]

# ================= HELPERS =================
def fmt_vol(v):
    if v >= 1e7: return f"{v/1e7:.1f}Cr"
    if v >= 1e5: return f"{v/1e5:.1f}L"
    if v >= 1e3: return f"{v/1e3:.1f}K"
    return str(v)

# ================= ROUTE =================
@app.route("/")
def index():

    rows = []
    tokens = [symbol_token[s] for s in WATCHLIST if s in symbol_token]
    quotes = kite.quote(tokens)

    for sym in WATCHLIST:
        if sym not in symbol_token:
            continue
        try:
            q = quotes[str(symbol_token[sym])]
            ltp = q["last_price"]
            prev = q["ohlc"]["close"]
            vol = q.get("volume", 0)

            if prev <= 0:
                continue

            pct = round(((ltp - prev) / prev) * 100, 2)

            rows.append({
                "symbol": sym,
                "pct": pct,
                "vol": vol,
                "vol_txt": fmt_vol(vol)
            })
        except:
            continue

    dfm = pd.DataFrame(rows)

    top_pct = dfm.sort_values("pct", ascending=False).head(30)
    bot_pct = dfm.sort_values("pct").head(30)

    return render_template(
        "index.html",
        top_pct=top_pct.to_dict("records"),
        bot_pct=bot_pct.to_dict("records"),
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3003, debug=True)

