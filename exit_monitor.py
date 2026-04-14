import json
import yfinance as yf
import requests
import os
import pandas as pd
from datetime import datetime, timedelta, timezone

DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK")
PROFIT_TARGET = 0.03   # 利確目標 +3%（バックテスト最適値）
LIMIT_DAYS    = 5      # 最大保有日数（変更なし）

def get_current_data(ticker):
    """直近60日分を取得してATR・現値を返す"""
    df = yf.download(ticker, period="60d", progress=False, auto_adjust=True)
    if df.empty:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    current_price = float(df["Close"].iloc[-1])
    atr = float((df["High"] - df["Low"]).rolling(14).mean().iloc[-1])
    return current_price, atr

def check_positions():
    if not os.path.exists("positions.json"):
        requests.post(DISCORD_WEBHOOK, json={"content": "✅ **【NR Exit 監視】** positions.jsonが存在しません。"})
        return

    with open("positions.json", "r", encoding="utf-8") as f:
        positions = json.load(f)

    if not positions:
        requests.post(DISCORD_WEBHOOK, json={"content": "✅ **【NR Exit 監視完了】** 保有ポジションなし。"})
        return

    exit_alerts  = []   # 決済推奨
    hold_alerts  = []   # 保有継続

    for pos in positions:
        try:
            ticker     = pos["ticker"]
            name       = pos.get("name", ticker)
            entry_price = float(pos["entry_price"])
            stop_loss   = float(pos.get("stop_loss", entry_price * 0.97))  # stop_lossがなければ-3%
            entry_date  = datetime.strptime(pos["entry_date"], "%Y-%m-%d")
            days_held   = (datetime.now() - entry_date).days

            result = get_current_data(ticker)
            if result is None:
                continue
            current_price, atr = result

            profit_pct   = (current_price - entry_price) / entry_price * 100
            
            atr_stop = entry_price - atr * 1.0  # ATRストップ（1.0倍・バックテスト最適値）

            # --- 決済判定（優先順位順）---
            reason = ""

            # ① 損切りライン割れ（最優先）
            if current_price <= stop_loss:
                reason = f"🛑 損切りライン割れ（{profit_pct:+.1f}%）"

            # ② ATRストップ
            elif current_price <= atr_stop and profit_pct < 0:
                reason = f"⚠️ ATRストップ発動（{profit_pct:+.1f}%）"

            # ③ 利確目標到達
            elif profit_pct >= PROFIT_TARGET * 100:
                reason = f"💰 利確目標到達（{profit_pct:+.1f}%）"

            # ④ 保有期間満了
            elif days_held >= LIMIT_DAYS:
                reason = f"⏰ 保有期間満了 {days_held}日（{profit_pct:+.1f}%）"

            if reason:
                exit_alerts.append(
                    f"**{name}（{ticker}）** {reason}\n"
                    f"　現値:{current_price:.0f}円 / 損切:{stop_loss:.0f}円 / 保有{days_held}日"
                )
            else:
                hold_alerts.append(
                    f"　{name}（{ticker}）{profit_pct:+.1f}% / 保有{days_held}日目"
                )

        except Exception as e:
            print(f"エラー {pos.get('ticker','?')}: {e}")

    # --- Discord通知 ---
    msg = "📊 **【NR Exit 監視レポート】**\n"

    if exit_alerts:
        msg += "\n🚨 **【決済推奨】**\n"
        msg += "\n".join(exit_alerts)

    if hold_alerts:
        msg += "\n\n✅ **【保有継続】**\n"
        msg += "\n".join(hold_alerts)

    jst = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=9)))
    msg += f"\n🕒 {jst.strftime('%Y/%m/%d %H:%M')} JST"
    requests.post(DISCORD_WEBHOOK, json={"content": msg})

if __name__ == "__main__":
    check_positions()
