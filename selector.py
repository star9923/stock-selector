"""
selector.py - 智能选股核心逻辑（单线程稳定版）
"""
import pandas as pd
from tqdm import tqdm
from data_fetcher import (
    get_stock_list,
    get_daily_history,
    get_realtime_quotes,
    get_financial_indicator,
)
from indicators import add_indicators, score_technical
from fundamental import score_fundamental, filter_basic


def run_selection(
    top_n: int = 20,
    tech_weight: float = 0.6,
    fund_weight: float = 0.4,
    min_score: float = 40.0,
) -> pd.DataFrame:
    """
    执行智能选股（单线程稳定版）
    :param top_n: 返回前 N 只股票
    :param tech_weight: 技术面权重
    :param fund_weight: 基本面权重
    :param min_score: 最低综合得分阈值
    :return: 选股结果 DataFrame
    """
    print("📋 获取股票列表...")
    stock_list = get_stock_list()

    print("📡 获取实时行情...")
    all_codes = stock_list["code"].tolist()
    df_realtime = get_realtime_quotes(all_codes)

    # 调试：检查原始数据
    print(f"   获取到 {len(df_realtime)} 条行情数据")
    if not df_realtime.empty:
        print(f"   列名: {df_realtime.columns.tolist()}")
        print(f"   前3行样例:\n{df_realtime.head(3)}")

    print("🔍 基础过滤（去 ST、小市值、停牌、涨跌停）...")
    df_realtime = filter_basic(df_realtime)

    # 调试：检查过滤后的数据
    if df_realtime.empty:
        print("⚠️  过滤后没有剩余股票，请检查数据源")
        return pd.DataFrame()

    if "code" not in df_realtime.columns:
        print(f"⚠️  DataFrame 缺少 'code' 列，当前列: {df_realtime.columns.tolist()}")
        return pd.DataFrame()

    filtered_codes = df_realtime["code"].tolist()
    print(f"   过滤后剩余 {len(filtered_codes)} 只股票")

    results = []

    print("📊 逐只分析股票（单线程稳定模式）...")
    for code in tqdm(filtered_codes):
        try:
            # 获取实时数据
            realtime_row = df_realtime[df_realtime["code"] == code]
            if realtime_row.empty:
                continue
            realtime_dict = realtime_row.iloc[0].to_dict()

            # 技术面分析
            hist = get_daily_history(code, days=120)
            if hist.empty or len(hist) < 60:
                continue
            
            hist = add_indicators(hist)
            tech = score_technical(hist)

            # 基本面分析
            financial = get_financial_indicator(code)
            fund = score_fundamental(realtime_dict, financial)

            # 综合得分
            total = tech["total"] * tech_weight + fund["total"] * fund_weight

            if total >= min_score:
                results.append({
                    "code":             code,
                    "name":             realtime_dict.get("name", ""),
                    "price":            realtime_dict.get("price"),
                    "pct_change":       realtime_dict.get("pct_change"),
                    "pe":               realtime_dict.get("pe"),
                    "pb":               realtime_dict.get("pb"),
                    "market_cap":       realtime_dict.get("market_cap"),
                    "turnover_rate":    realtime_dict.get("turnover_rate"),
                    "tech_score":       round(tech["total"], 1),
                    "tech_trend":       tech["trend"],
                    "tech_momentum":    tech["momentum"],
                    "tech_volume":      tech["volume"],
                    "fund_score":       round(fund["total"], 1),
                    "fund_valuation":   fund["valuation"],
                    "fund_profit":      fund["profitability"],
                    "fund_growth":      fund["growth"],
                    "total_score":      round(total, 1),
                })

        except Exception as e:
            # 静默跳过错误，继续下一只
            continue

    if not results:
        print("⚠️  没有股票达到最低得分要求")
        return pd.DataFrame()

    df_result = (
        pd.DataFrame(results)
        .sort_values("total_score", ascending=False)
        .head(top_n)
        .reset_index(drop=True)
    )
    df_result.index += 1

    return df_result
