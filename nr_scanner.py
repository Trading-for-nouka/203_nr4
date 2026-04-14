import yfinance as yf
import pandas as pd
import requests
import os
import json
from datetime import datetime, timedelta, timezone
from strategy_params import calc_nr_levels
from claude_comment import generate_comments_batch

DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK")
PAT_TOKEN = os.environ.get("PAT_TOKEN")

def get_market_phase():
    url = f"https://api.github.com/repos/trading-for-nouka/102_market_phase/contents/market_phase.json"  # ← 変更
    headers = {"Authorization": f"token {PAT_TOKEN}" if PAT_TOKEN else "", "Accept": "application/vnd.github.v3.raw"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json().get("phase", "NEUTRAL")
    except: pass
    return "NEUTRAL"

def get_nr_data(ticker, name):
    from datetime import datetime
    
    df = yf.download(ticker, period="250d", progress=False, auto_adjust=True)
    if len(df) < 200: return None

    df['SMA200'] = df['Close'].rolling(window=200).mean()
    df['VolSMA20'] = df['Volume'].rolling(window=20).mean()
    
    current_val = float(df['Close'].iloc[-1].item())
    sma200_val = float(df['SMA200'].iloc[-1].item())
    current_vol = float(df['Volume'].iloc[-1].item())
    vol_sma20 = float(df['VolSMA20'].iloc[-1].item())
    
    if current_val <= sma200_val or current_vol < (vol_sma20 * 1.2):
        return None

    df_short = df.tail(60).copy()
    df_short['range'] = df_short['High'] - df_short['Low']
    
    is_nr4 = df_short['range'].iloc[-1] == df_short['range'].rolling(4).min().iloc[-1]
    if not is_nr4: return None

    is_compressed = bool(df_short['range'].iloc[-1] <= (df_short['range'].rolling(30).mean().iloc[-1] * 0.8))
    if not is_compressed: return None

    latest = df_short.iloc[-1]
    prev = df_short.iloc[-2]

    atr = float(df_short['range'].rolling(14).mean().iloc[-1])
    
    entry_p   = round(float(latest['High'].item()) + atr * 0.1, 0)
    stop_p    = round(float(latest['Low'].item()), 0)
    levels    = calc_nr_levels(entry_p, stop_p)

    return {
        "ticker":        ticker,
        "name":          name,
        "type":          "NR4",
        "is_inside":     bool((latest['High'].item() < prev['High'].item()) and (latest['Low'].item() > prev['Low'].item())),
        "is_compressed": is_compressed,
        "strength":      float(current_val / sma200_val),
        "entry_price":   levels["entry_price"],
        "stop_loss":     levels["stop_loss"],
        "target":        levels["target"],
        "hold_days":     levels["hold_days"],
        "entry_date":    datetime.now().strftime("%Y-%m-%d"),
    }

def send_discord(msg):
    for i in range(0, len(msg), 1900):
        requests.post(DISCORD_WEBHOOK, json={"content": msg[i:i+1900]})

def main():
    phase = get_market_phase()
    if phase == "CRASH": return

    universe = pd.read_csv("universe496.csv", encoding="cp932")  # ← 変更
    results = []
    
    for _, row in universe.iterrows():
        data = get_nr_data(row['ticker'], row['name'])
        if data:
            results.append(data)
    
    with open("nr_watchlist.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
            
    high_potential = results
    
    if high_potential:
        top_picks = sorted(high_potential, key=lambda x: x['strength'], reverse=True)[:5]

        for p in top_picks:
            p["phase"] = phase

        print("💬 Claude APIコメント生成中...")
        top_picks = generate_comments_batch(top_picks, max_count=5)

        msg = f"🚀 **【厳選NR4 スキャン結果】 市場フェーズ: {phase}**\n"
        msg += f"🔥 **トレンド最強・収束トップ5 (候補: {len(high_potential)}件)**\n"
        msg += "━━━━━━━━━━━━━━━━━━━━\n"
        for r in top_picks:
            inside_mark = "📦IB " if r["is_inside"] else ""
            msg += (
                f"**{r['name']}** ({r['ticker']}) {inside_mark}| SMA200比: {r['strength']:.2f}\n"
                f"　 📌 エントリー: {r['entry_price']}円 | 🛑 損切: {r['stop_loss']}円 | 🎯 利確: {r['target']}円（保有{r['hold_days']}日）\n"
            )
            if r.get("comment"):
                msg += f"　 💬 {r['comment']}\n"
            msg += "\n"
        jst = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=9)))
        msg += f"🕒 {jst.strftime('%Y/%m/%d %H:%M')} JST\n"
        send_discord(msg)

    else:
        msg = f"✅ 本日のスキャン完了（候補なし）\n"
        msg += f"- 全取得銘柄数: {len(results)}件\n"
        msg += "⚠️ 今回は条件を満たす銘柄はありませんでした。"
        jst = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=9)))
        msg += f"🕒 {jst.strftime('%Y/%m/%d %H:%M')} JST\n"
        send_discord(msg)

if __name__ == "__main__":
    main()
