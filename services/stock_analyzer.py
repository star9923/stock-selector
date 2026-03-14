"""
stock_analyzer.py - 个股深度分析模块
"""
import pandas as pd
import json
from datetime import datetime
from data.data_fetcher import get_daily_history, _get_daily_history_em, _get_daily_history_sina, get_financial_indicator, _STOCK_MAPPING
from core.indicators import add_indicators, score_technical
from core.fundamental import score_fundamental
from services.sentiment import score_sentiment, get_sentiment_data


def analyze_stock(code: str, enable_sentiment: bool = True, hist_source: str = "auto") -> dict:
    """
    深度分析单只股票
    :param code: 股票代码
    :param enable_sentiment: 是否启用情绪分析
    :return: 分析结果字典
    """
    result = {
        "code": code,
        "name": _STOCK_MAPPING.get(code, code),
        "success": False,
        "error": None,
        "basic_info": {},
        "technical": {},
        "fundamental": {},
        "sentiment": {},
        "price_data": [],
        "signals": [],
        "recommendation": "",
    }

    try:
        # 1. 获取历史数据（根据数据源选择）
        from data.stock_data_fallback import get_stock_history_with_fallback

        source_names = {"auto": "自动选择", "sina": "新浪财经", "em": "东方财富"}
        print(f"   历史数据源: {source_names.get(hist_source, hist_source)}")

        if hist_source == "sina":
            hist = _get_daily_history_sina(code, days=120)
        elif hist_source == "em":
            hist = _get_daily_history_em(code, days=120)
        else:
            # auto: 使用多源降级
            hist = get_stock_history_with_fallback(code, days=120)

        if hist.empty or len(hist) < 60:
            result["error"] = "历史数据不足"
            return result

        # 2. 基本信息
        latest = hist.iloc[-1]
        result["basic_info"] = {
            "price": float(latest["close"]),
            "change": float(latest["close"] - hist.iloc[-2]["close"]),
            "pct_change": float((latest["close"] - hist.iloc[-2]["close"]) / hist.iloc[-2]["close"] * 100),
            "volume": int(latest["volume"]),
            "turnover": float(latest["turnover"]),
            "turnover_rate": float(latest.get("turnover_rate", 0)),
            "high_52w": float(hist["high"].tail(250).max() if len(hist) >= 250 else hist["high"].max()),
            "low_52w": float(hist["low"].tail(250).min() if len(hist) >= 250 else hist["low"].min()),
        }

        # 3. 技术分析
        hist = add_indicators(hist)
        tech_score = score_technical(hist)

        import math
        def sf(v):
            try:
                f = float(v)
                return 0 if math.isnan(f) or math.isinf(f) else f
            except (TypeError, ValueError):
                return 0

        latest_with_ind = hist.iloc[-1]
        result["technical"] = {
            "score": tech_score,
            "ma5": sf(latest_with_ind.get("ma5", 0)),
            "ma10": sf(latest_with_ind.get("ma10", 0)),
            "ma20": sf(latest_with_ind.get("ma20", 0)),
            "ma60": sf(latest_with_ind.get("ma60", 0)),
            "macd_dif": sf(latest_with_ind.get("macd_dif", 0)),
            "macd_dea": sf(latest_with_ind.get("macd_dea", 0)),
            "macd_bar": sf(latest_with_ind.get("macd_bar", 0)),
            "rsi": sf(latest_with_ind.get("rsi14", 0)),
            "kdj_k": sf(latest_with_ind.get("kdj_k", 0)),
            "kdj_d": sf(latest_with_ind.get("kdj_d", 0)),
            "kdj_j": sf(latest_with_ind.get("kdj_j", 0)),
            "boll_upper": sf(latest_with_ind.get("boll_upper", 0)),
            "boll_mid": sf(latest_with_ind.get("boll_mid", 0)),
            "boll_lower": sf(latest_with_ind.get("boll_lower", 0)),
        }

        # 4. 基本面分析
        financial = get_financial_indicator(code)
        realtime_dict = {
            "pe": 0,
            "pb": 0,
            "market_cap": 0,
            "turnover_rate": result["basic_info"]["turnover_rate"],
            "pct_change": result["basic_info"]["pct_change"],
        }
        fund_score = score_fundamental(realtime_dict, financial)
        result["fundamental"] = {
            "score": fund_score,
            "roe": sf(financial.get("roe", 0)),
            "eps": sf(financial.get("eps", 0)),
            "gross_margin": sf(financial.get("gross_margin", 0)),
            "net_margin": sf(financial.get("net_margin", 0)),
            "revenue_growth": sf(financial.get("revenue_growth", 0)),
            "net_profit_growth": sf(financial.get("net_profit_growth", 0)),
            "debt_ratio": sf(financial.get("debt_ratio", 0)),
            "current_ratio": sf(financial.get("current_ratio", 0)),
        }

        # 5. 情绪分析
        if enable_sentiment:
            try:
                hot_stocks, board_sentiment, stock_board_map = get_sentiment_data()
                sentiment = score_sentiment(code, hot_stocks, board_sentiment, stock_board_map)
                result["sentiment"] = {
                    "score": sentiment["total"],
                    "hot_score": sentiment["hot_score"],
                    "board_score": sentiment["board_score"],
                    "board_name": sentiment["board_name"],
                }
            except Exception as e:
                result["sentiment"] = {
                    "score": 0,
                    "hot_score": 0,
                    "board_score": 0,
                    "board_name": "未知",
                    "error": str(e),
                }

        # 6. 价格数据（最近60天）
        recent = hist.tail(60)
        result["price_data"] = [
            {
                "date": row["date"].strftime("%Y-%m-%d"),
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": int(row["volume"]),
                "ma5": float(row.get("ma5", 0)),
                "ma10": float(row.get("ma10", 0)),
                "ma20": float(row.get("ma20", 0)),
            }
            for _, row in recent.iterrows()
        ]

        # 7. 交易信号
        signals = generate_signals(hist, tech_score, fund_score)
        result["signals"] = signals

        # 8. 投资建议
        sentiment_score = result["sentiment"].get("score", 0) if enable_sentiment else 0
        total_score = tech_score["total"] * 0.5 + fund_score["total"] * 0.3 + sentiment_score * 0.2
        result["recommendation"] = generate_recommendation(total_score, signals)

        result["success"] = True

    except Exception as e:
        result["error"] = str(e)

    return result


def generate_signals(hist: pd.DataFrame, tech_score: dict, fund_score: dict) -> list:
    """生成交易信号"""
    signals = []
    latest = hist.iloc[-1]
    prev = hist.iloc[-2]

    # 均线信号
    if latest["ma5"] > latest["ma10"] > latest["ma20"]:
        signals.append({"type": "bullish", "signal": "多头排列", "desc": "短中长期均线呈多头排列"})
    elif latest["ma5"] < latest["ma10"] < latest["ma20"]:
        signals.append({"type": "bearish", "signal": "空头排列", "desc": "短中长期均线呈空头排列"})

    # MACD信号
    if latest["macd_bar"] > 0 and prev["macd_bar"] <= 0:
        signals.append({"type": "bullish", "signal": "MACD金叉", "desc": "MACD柱状图由负转正"})
    elif latest["macd_bar"] < 0 and prev["macd_bar"] >= 0:
        signals.append({"type": "bearish", "signal": "MACD死叉", "desc": "MACD柱状图由正转负"})

    # RSI信号
    rsi = latest.get("rsi14", 0)
    if rsi < 30:
        signals.append({"type": "bullish", "signal": "RSI超卖", "desc": f"RSI={rsi:.1f}，处于超卖区域"})
    elif rsi > 70:
        signals.append({"type": "bearish", "signal": "RSI超买", "desc": f"RSI={rsi:.1f}，处于超买区域"})

    # KDJ信号
    if latest["kdj_k"] < 20 and latest["kdj_d"] < 20:
        signals.append({"type": "bullish", "signal": "KDJ超卖", "desc": "KDJ指标处于超卖区域"})
    elif latest["kdj_k"] > 80 and latest["kdj_d"] > 80:
        signals.append({"type": "bearish", "signal": "KDJ超买", "desc": "KDJ指标处于超买区域"})

    # 布林带信号
    if latest["close"] < latest["boll_lower"]:
        signals.append({"type": "bullish", "signal": "触及下轨", "desc": "价格触及布林带下轨，可能反弹"})
    elif latest["close"] > latest["boll_upper"]:
        signals.append({"type": "bearish", "signal": "触及上轨", "desc": "价格触及布林带上轨，可能回调"})

    # 成交量信号
    avg_volume = hist["volume"].tail(20).mean()
    if latest["volume"] > avg_volume * 2:
        signals.append({"type": "neutral", "signal": "放量", "desc": "成交量显著放大"})

    return signals


def generate_recommendation(total_score: float, signals: list) -> str:
    """生成投资建议"""
    bullish_count = sum(1 for s in signals if s["type"] == "bullish")
    bearish_count = sum(1 for s in signals if s["type"] == "bearish")

    if total_score >= 70 and bullish_count > bearish_count:
        return "强烈推荐"
    elif total_score >= 60 and bullish_count >= bearish_count:
        return "推荐"
    elif total_score >= 50:
        return "中性"
    elif total_score >= 40:
        return "观望"
    else:
        return "不推荐"


def batch_analyze(codes: list, max_count: int = 20) -> list:
    """批量分析股票"""
    results = []
    for code in codes[:max_count]:
        result = analyze_stock(code)
        if result["success"]:
            results.append(result)
    return results
