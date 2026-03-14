"""
selector.py - 智能选股核心逻辑（多线程并发版 + 情绪分析）
"""
import pandas as pd
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from data_fetcher import (
    get_stock_list,
    get_daily_history,
    get_realtime_quotes,
    get_realtime_quotes_from_sina,
    get_realtime_quotes_from_em,
    get_realtime_quotes_from_xueqiu,
    get_financial_indicator,
)
from indicators import add_indicators, score_technical
from fundamental import score_fundamental, filter_basic
from sentiment import score_sentiment, get_sentiment_data


def _analyze_single(code, realtime_dict, tech_weight, fund_weight, sentiment_weight, min_score,
                    hot_stocks, board_sentiment, stock_board_map):
    """分析单只股票，返回结果字典或 None（线程安全）"""
    try:
        hist = get_daily_history(code, days=120)
        if hist.empty or len(hist) < 60:
            return None

        hist = add_indicators(hist)
        tech = score_technical(hist)

        financial = get_financial_indicator(code)
        fund = score_fundamental(realtime_dict, financial)

        # 情绪分析
        sentiment = score_sentiment(code, hot_stocks, board_sentiment, stock_board_map)

        # 综合得分（三维度加权）
        total = (tech["total"] * tech_weight +
                 fund["total"] * fund_weight +
                 sentiment["total"] * sentiment_weight)

        if total < min_score:
            return None

        return {
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
            "sentiment_score":  round(sentiment["total"], 1),
            "hot_score":        sentiment["hot_score"],
            "board_score":      sentiment["board_score"],
            "board_name":       sentiment["board_name"],
            "total_score":      round(total, 1),
        }
    except Exception:
        return None


def run_selection(
    top_n: int = 20,
    tech_weight: float = 0.5,
    fund_weight: float = 0.3,
    sentiment_weight: float = 0.2,
    min_score: float = 40.0,
    max_workers: int = 8,
    enable_sentiment: bool = True,
    quote_source: str = "auto",
) -> pd.DataFrame:
    """
    执行智能选股（多线程并发版 + 情绪分析）
    :param top_n: 返回前 N 只股票
    :param tech_weight: 技术面权重
    :param fund_weight: 基本面权重
    :param sentiment_weight: 情绪面权重
    :param min_score: 最低综合得分阈值
    :param max_workers: 并发线程数（建议 4~16，过高易触发限流）
    :param enable_sentiment: 是否启用情绪分析（较慢）
    :param quote_source: 数据源选择 (auto/sina/em/xueqiu)
    :return: 选股结果 DataFrame
    """
    print("📋 获取股票列表...")
    stock_list = get_stock_list()

    print("📡 获取实时行情...")
    all_codes = stock_list["code"].tolist()

    # 根据用户选择的数据源获取行情
    source_names = {"auto": "自动选择", "sina": "新浪财经", "em": "东方财富", "xueqiu": "雪球"}
    print(f"   数据源: {source_names.get(quote_source, quote_source)}")

    if quote_source == "sina":
        df_realtime = get_realtime_quotes_from_sina()
        if not df_realtime.empty and all_codes:
            df_realtime = df_realtime[df_realtime['code'].isin(all_codes)]
    elif quote_source == "em":
        df_realtime = get_realtime_quotes_from_em(all_codes, max_workers=max_workers)
    elif quote_source == "xueqiu":
        df_realtime = get_realtime_quotes_from_xueqiu()
        if not df_realtime.empty and all_codes:
            df_realtime = df_realtime[df_realtime['code'].isin(all_codes)]
    else:
        # auto: 使用多源降级
        df_realtime = get_realtime_quotes(all_codes, max_workers=max_workers)

    print(f"   获取到 {len(df_realtime)} 条行情数据")
    if not df_realtime.empty:
        print(f"   列名: {df_realtime.columns.tolist()}")
        print(f"   前3行样例:\n{df_realtime.head(3)}")

    print("🔍 基础过滤（去 ST、小市值、停牌、涨跌停）...")
    df_realtime = filter_basic(df_realtime)

    if df_realtime.empty:
        print("⚠️  过滤后没有剩余股票，请检查数据源")
        return pd.DataFrame()

    if "code" not in df_realtime.columns:
        print(f"⚠️  DataFrame 缺少 'code' 列，当前列: {df_realtime.columns.tolist()}")
        return pd.DataFrame()

    filtered_codes = df_realtime["code"].tolist()
    print(f"   过滤后剩余 {len(filtered_codes)} 只股票")

    # 获取情绪数据
    hot_stocks, board_sentiment, stock_board_map = pd.DataFrame(), pd.DataFrame(), {}
    if enable_sentiment:
        hot_stocks, board_sentiment, stock_board_map = get_sentiment_data()
    else:
        print("⚠️  情绪分析已禁用")

    # 构建 code -> realtime_dict 映射
    realtime_map = {row["code"]: row.to_dict() for _, row in df_realtime.iterrows()}

    results = []
    print(f"📊 并发分析股票（{max_workers} 线程）...")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                _analyze_single,
                code,
                realtime_map[code],
                tech_weight,
                fund_weight,
                sentiment_weight,
                min_score,
                hot_stocks,
                board_sentiment,
                stock_board_map,
            ): code
            for code in filtered_codes
            if code in realtime_map
        }

        for future in tqdm(as_completed(futures), total=len(futures), desc="分析进度"):
            result = future.result()
            if result is not None:
                results.append(result)

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
