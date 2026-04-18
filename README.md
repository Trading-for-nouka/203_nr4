# 📦 203_nr4 — NR4 戦略

直近4日間で最小レンジを記録した銘柄（NR4）をスキャンし、
ブレイク後のポジションを毎日監視して決済シグナルを Discord に通知します。

## 戦略概要

| 項目 | 値 |
|---|---|
| エントリー条件 | 直近4日間が最小レンジ（NR4） |
| 利確目標 | +3% |
| 最大保有日数 | 5日 |
| 損切りライン | エントリー価格 × 0.97（または ATR ストップ） |

## スケジュール

| ワークフロー | 時刻 (JST) | 内容 |
|---|---|---|
| `nr_scan.yml` | 平日 15:30 | NR4 銘柄スキャン |
| `exit_monitor.yml` | 平日 17:11 | 保有ポジション監視・決済判定 |

## Secrets

| 名前 | 内容 |
|---|---|
| `DISCORD_WEBHOOK` | Discord の Webhook URL |
| `PAT_TOKEN` | 102_market_phase の market_phase.json 読み取り用 |
| `ANTHROPIC_API_KEY` | Claude API（銘柄コメント生成） |

## ファイル構成

```
203_nr4/
├── nr_scanner.py              # エントリースキャン
├── exit_monitor.py            # ポジション監視・決済判定
├── claude_comment.py          # Claude API コメント生成
├── strategy_params.py         # 戦略パラメータ定義
├── universe496.csv            # 対象銘柄リスト（496銘柄）
├── requirements.txt
└── .github/workflows/
    ├── nr_scan.yml
    └── exit_monitor.yml
```

## 主要ファイル

- `nr_watchlist.json` — スキャン結果（Actions が自動コミット）
- `positions.json` — 保有ポジション（手動または他ツールで管理）
