"""
selector.py - 智能选股核心逻辑（多线程并发版）
"""
import pandas as pd
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from data_fetcher import (
    get_stock_list,
    get_daily_history,
    get_realtime_quotes,
    get_financial_indicator,
)
from indicators import add_indicators, score_technical
from fundamental import score_fundamental, filter_basic


def _analyze_single(code, realtime_dict, tech_weight, fund_weight, min_score):
    """分析单只股票，返回结果字典或 None（线程安全）"""
    try:
        hist = get_daily_history(code, days=120)
        if hist.empty or len(hist) < 60:
            return None

        hist = add_indicators(hist)
        tech = score_technical(hist)

        financial = get_financial_indicator(code)
        fund = score_fundamental(realtime_dict, financial)

        total = tech["total"] * tech_weight + fund["total"] * fund_weight
        if total < min_score:
            return None

        code_full = f"{code}.SZ" if not code.startswith("6") else f"{code}.SH"
        return {
            "code":           code_full,
            "name":           realtime_dict.get("name", ""),
            "price":          realtime_dict.get("price"),
            "pct_change":     realtime_dict.get("pct_change"),
            "pe":             realtime_dict.get("pe"),
            "pb":             realtime_dict.get("pb"),
            "market_cap":     realtime_dict.get("market_cap"),
            "turnover_rate":  realtime_dict.get("turnover_rate"),
            "tech_score":     round(tech["total"], 1),
            "tech_trend":     tech["trend"],
            "tech_momentum":  tech["momentum"],
            "tech_volume":    tech["volume"],
            "fund_score":     round(fund["total"], 1),
            "fund_valuation": fund["valuation"],
            "fund_profit":    fund["profitability"],
            "fund_growth":    fund["growth"],
            "fund_liquidity": fund["liquidity"],
            "total_score":    round(total, 1),
            "pct_change":     realtime_dict.get("pct_change"),
        }
    except Exception:
        return None


def run_selection(
    top_n: int = 20,
    tech_weight: float = 0.6,
    fund_weight: float = 0.4,
    min_score: float = 40.0,
    max_workers: int = 16,
) -> pd.DataFrame:
    """
    执行智能选股（多线程并发版）
    :param top_n: 返回前 N 只股票
    :param tech_weight: 技术面权重
    :param fund_weight: 基本面权重
    :param min_score: 最低综合得分阈值
    :param max_workers: 并发线程数（建议 4~16，过高易触发限流）
    :return: 选股结果 DataFrame
    """
    print("[INFO] Getting stock list...")
    stock_list = get_stock_list()

    print("[INFO] Getting realtime quotes...")
    all_codes = stock_list["code"].tolist()
    df_realtime = get_realtime_quotes(all_codes, max_workers=max_workers)

    print(f"   Fetched {len(df_realtime)} records")
    if not df_realtime.empty:
        print(f"   Columns: {df_realtime.columns.tolist()}")

    print("[INFO] Filtering stocks (remove ST, low cap, etc)...")
    df_realtime = filter_basic(df_realtime)

    if df_realtime.empty:
        print("[WARNING] No stocks left after filtering")
        return pd.DataFrame()

    if "code" not in df_realtime.columns:
        print(f"[WARNING] DataFrame missing 'code' column: {df_realtime.columns.tolist()}")
        return pd.DataFrame()

    filtered_codes = df_realtime["code"].tolist()
    max_analyze = 500
    if len(filtered_codes) > max_analyze:
        filtered_codes = filtered_codes[:max_analyze]
        print(f"   {len(filtered_codes)} stocks remaining (capped for performance)")
    else:
        print(f"   {len(filtered_codes)} stocks remaining")

    realtime_map = {row["code"]: row.to_dict() for _, row in df_realtime.iterrows()}

    results = []
    print(f"[INFO] Analyzing stocks ({max_workers} threads)...")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                _analyze_single,
                code,
                realtime_map[code],
                tech_weight,
                fund_weight,
                min_score,
            ): code
            for code in filtered_codes
            if code in realtime_map
        }

        for future in tqdm(as_completed(futures), total=len(futures), desc="分析进度"):
            result = future.result()
            if result is not None:
                results.append(result)

    if not results:
        print("[WARNING] No stocks met the min score requirement")
        return pd.DataFrame()

    df_result = (
        pd.DataFrame(results)
        .sort_values("total_score", ascending=False)
        .head(top_n)
        .reset_index(drop=True)
    )
    df_result.index += 1
    return df_result
