# strategy_params.py
# バックテスト実績値に基づく戦略別パラメータ定数
# 2015-2025 日本大型株ユニバース実績（NR4戦略）

STRATEGY_PARAMS = {

    # ============================================================
    # NR4収縮戦略（nr_scanner.py）
    # 実績: 勝率49% / PF1.54 / 平均リターン+0.58% / 保有5日
    # 最優秀パラメータ:
    #   NR4 / 収束条件あり / 利確+3% / 損切り=当日安値 / 保有5日
    #   ※ATR倍率は1.0〜2.0どれでも結果同じ（損切り=当日安値が支配的）
    # ============================================================
    "nr": {
        # エントリー（既存コードに準拠）
        "entry_atr_offset": 0.1,   # 当日高値 + ATR×0.1

        # 損切り（既存コードに準拠）
        "stop_base": "low",        # 当日安値そのまま

        # 利確（バックテスト最優秀値）
        "profit_target": 0.03,     # +3%

        # 保有期間（バックテスト最優秀値）
        "hold_days": 5,

        # バックテスト実績
        "win_rate":       0.49,
        "profit_factor":  1.54,
        "avg_pnl":        0.58,    # 平均損益（%）
    },
}


def calc_nr_levels(entry_price, stop_loss):
    """
    NR4戦略の定量売買水準を計算する。
    entry_price / stop_loss は get_nr_data() が計算済みの値を受け取る。

    Args:
        entry_price (float): 当日高値 + ATR×0.1（get_nr_dataが計算済み）
        stop_loss   (float): 当日安値（get_nr_dataが計算済み）

    Returns:
        dict: entry_price, stop_loss, target, hold_days
    """
    p = STRATEGY_PARAMS["nr"]
    target = round(entry_price * (1 + p["profit_target"]))

    return {
        "entry_price": round(entry_price),
        "stop_loss":   round(stop_loss),
        "target":      target,
        "hold_days":   p["hold_days"],
        "win_rate":    p["win_rate"],
        "pf":          p["profit_factor"],
    }
