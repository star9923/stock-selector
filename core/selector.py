"""
selector.py - 智能选股核心逻辑（多线程并发版 + 情绪分析）
"""
import time
import traceback
import pandas as pd
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FuturesTimeout
from data.data_fetcher import (
    get_stock_list,
    get_realtime_quotes,
    get_realtime_quotes_from_sina,
    get_realtime_quotes_from_em,
    get_realtime_quotes_from_xueqiu,
    get_financial_indicator,
)
from data.stock_data_fallback import get_stock_history_with_fallback
from core.indicators import add_indicators, score_technical
from core.fundamental import score_fundamental, filter_basic
from services.sentiment import score_sentiment, get_sentiment_data

# 单只股票分析超时（秒）：avoid a single slow AkShare call from stalling the whole run
PER_STOCK_TIMEOUT = 30
# 整个并发阶段兜底超时（秒）：到时间强制收尾，防止极端长尾永远卡住
OVERALL_TIMEOUT = 30 * 60


def _analyze_single(code, realtime_dict, tech_weight, fund_weight, sentiment_weight, min_score,
                    hot_stocks, board_sentiment, stock_board_map):
    """分析单只股票，返回结果字典或 None（线程安全）"""
    try:
        hist = get_stock_history_with_fallback(code, days=120)
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
    except Exception as e:
        print(f"   ⚠️  分析 {code} 失败: {e.__class__.__name__}: {str(e)[:120]}")
        traceback.print_exc()
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
    volume_top_n: int = 500,
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
    :param volume_top_n: 只分析当日成交量市场前 N 只股票（默认500），0 或负数表示不限制
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

    # 只保留当日成交量排名前 volume_top_n 的股票（减少分析耗时）
    if volume_top_n and volume_top_n > 0 and "volume" in df_realtime.columns:
        vol = pd.to_numeric(df_realtime["volume"], errors="coerce").fillna(0)
        if (vol > 0).any():
            df_realtime = df_realtime.assign(_vol=vol) \
                .sort_values("_vol", ascending=False) \
                .head(volume_top_n) \
                .drop(columns=["_vol"]) \
                .reset_index(drop=True)
            print(f"🔥 按成交量取前 {volume_top_n} 只，剩余 {len(df_realtime)} 只进入分析")
        else:
            print(f"⚠️  行情数据无有效成交量，跳过过滤")

    filtered_codes = df_realtime["code"].tolist()
    print(f"   过滤后剩余 {len(filtered_codes)} 只股票")

    # 获取情绪数据
    hot_stocks, board_sentiment, stock_board_map, guba_data = pd.DataFrame(), pd.DataFrame(), {}, pd.DataFrame()
    if enable_sentiment:
        hot_stocks, board_sentiment, stock_board_map, guba_data = get_sentiment_data()
    else:
        print("⚠️  情绪分析已禁用")

    # 构建 code -> realtime_dict 映射
    realtime_map = {row["code"]: row.to_dict() for _, row in df_realtime.iterrows()}

    results = []
    print(f"📊 并发分析股票（{max_workers} 线程）...")

    deadline = time.monotonic() + OVERALL_TIMEOUT
    stalled = 0

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

        pending = set(futures.keys())
        pbar = tqdm(total=len(futures), desc="分析进度")
        try:
            for future in as_completed(futures, timeout=OVERALL_TIMEOUT):
                pending.discard(future)
                try:
                    result = future.result(timeout=PER_STOCK_TIMEOUT)
                except FuturesTimeout:
                    stalled += 1
                    future.cancel()
                    result = None
                except Exception as e:
                    print(f"   ⚠️  worker 异常: {e.__class__.__name__}: {str(e)[:120]}")
                    result = None
                if result is not None:
                    results.append(result)
                pbar.update(1)
                if time.monotonic() > deadline:
                    raise FuturesTimeout
        except FuturesTimeout:
            # 整体超时：取消剩余任务，继续用已完成结果出数
            print(f"   ⚠️  并发分析整体超时 ({OVERALL_TIMEOUT}s)，剩余 {len(pending)} 只放弃")
            for f in pending:
                f.cancel()
        finally:
            pbar.close()

    if stalled:
        print(f"   ℹ️  单只超时跳过 {stalled} 只")

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
