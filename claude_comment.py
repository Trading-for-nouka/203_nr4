# claude_comment.py
# Claude APIを使ってNR4候補銘柄のコメントを生成するモジュール

import os
import requests

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
API_URL = "https://api.anthropic.com/v1/messages"
MODEL   = "claude-haiku-4-5-20251001"   # コスト重視。品質向上時はsonnet-4-6に変更

# ============================================================
# システムプロンプト
# ============================================================
SYSTEM_PROMPT = """
あなたは日本株NR4ボラティリティ収縮トレードのアシスタントです。
スキャン結果データをもとに、個人トレーダー向けの簡潔なコメントを日本語で生成してください。

【出力形式】必ず以下の3行構成で出力すること。余計な前置きは不要。
1行目: NR4収縮の根拠（収縮度・SMA200との位置関係から1〜2点を選んで1文で説明）
2行目: 📌 エントリー: {entry_price}円（高値ブレイク） / 🛑 損切り: {stop_loss}円（当日安値） / 🎯 利確: {target}円（+3%）
3行目: ⚠️ 注意点（1文、翌日始値でのブレイク確認必須・5日以内決済など）

数値は必ずデータの値をそのまま使うこと。自分で計算しないこと。
""".strip()


def _build_user_prompt(signal):
    """NR4戦略用ユーザープロンプトを生成する"""

    inside_str = "あり（インサイドバー併発）" if signal.get("is_inside") else "なし"

    prompt = f"""
戦略: NR4ボラティリティ収縮（Narrow Range 4）
銘柄: {signal['ticker']} {signal['name']}
市場フェーズ: {signal['phase']}

【NR4判定データ】
NRタイプ: {signal['type']}
インサイドバー: {inside_str}
収縮条件: 当日レンジ ≤ 30日平均レンジ × 0.8（必須クリア済み）
SMA200比: {signal['strength']:.2f}倍（1.0超 = SMA200上で上昇トレンド確認済み）

【定量売買水準（Pythonで計算済み）】
エントリー:   {signal['entry_price']}円（当日高値ブレイク、翌日始値で確認）
損切りライン: {signal['stop_loss']}円（当日安値）
利確目標:     {signal['target']}円（エントリーから+3%）
保有期間目安: {signal['hold_days']}日

【バックテスト実績（2015-2025）】
勝率: 49% / PF: 1.54 / 平均損益: +0.58% / 保有5日
戦略概要: NR4 × 収縮条件必須 × 翌日高値ブレイクエントリー × 利確+3%

上記の形式でコメントを生成してください。
""".strip()

    return prompt


def generate_comment(signal):
    """
    Claude APIを呼び出してNR4コメントを生成する。

    Args:
        signal (dict): スキャン結果 + 定量売買水準を含む辞書

    Returns:
        str: 生成されたコメント。失敗時はNone。
    """
    if not ANTHROPIC_API_KEY:
        print("⚠️ ANTHROPIC_API_KEY が設定されていません。コメント生成をスキップします。")
        return None

    headers = {
        "x-api-key":         ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type":      "application/json",
    }

    payload = {
        "model":      MODEL,
        "max_tokens": 300,
        "system":     SYSTEM_PROMPT,
        "messages": [
            {
                "role":    "user",
                "content": _build_user_prompt(signal)
            }
        ],
    }

    try:
        resp = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return data["content"][0]["text"].strip()

    except requests.exceptions.Timeout:
        print(f"⚠️ Claude API タイムアウト ({signal['ticker']})")
        return None
    except Exception as e:
        print(f"⚠️ Claude API エラー ({signal['ticker']}): {e}")
        return None


def generate_comments_batch(signals, max_count=5):
    """
    複数銘柄のコメントをまとめて生成する（上位N件のみ）。

    Args:
        signals   (list): signal辞書のリスト（strength降順を前提）
        max_count (int):  コメント生成する最大件数（コスト節約）

    Returns:
        list: signal辞書に "comment" キーを追加したリスト
    """
    results = []
    for i, sig in enumerate(signals):
        if i < max_count:
            print(f"  💬 コメント生成中: {sig['ticker']} {sig['name']} ({i+1}/{min(len(signals), max_count)})")
            comment = generate_comment(sig)
            sig["comment"] = comment if comment else "（コメント生成失敗）"
        else:
            sig["comment"] = None
        results.append(sig)
    return results
