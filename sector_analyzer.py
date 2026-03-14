"""
sector_analyzer.py - 板块分析模块
"""
import pandas as pd
from typing import Dict, List
from sentiment import get_board_sentiment, get_stock_board_mapping, retry_on_failure
import akshare as ak


@retry_on_failure(max_retries=3, delay=2)
def get_sector_stocks(sector_name: str) -> pd.DataFrame:
    """获取板块成分股"""
    df = ak.stock_board_industry_cons_em(symbol=sector_name)
    if df.empty:
        return pd.DataFrame()

    df = df.rename(columns={
        "代码": "code",
        "名称": "name",
        "最新价": "price",
        "涨跌幅": "pct_change",
        "涨跌额": "change",
        "成交量": "volume",
        "成交额": "turnover",
        "振幅": "amplitude",
        "换手率": "turnover_rate",
        "市盈率-动态": "pe",
        "市净率": "pb",
    })
    return df


def analyze_sector(sector_name: str) -> dict:
    """
    分析单个板块
    :param sector_name: 板块名称
    :return: 板块分析结果
    """
    result = {
        "sector_name": sector_name,
        "success": False,
        "error": None,
        "summary": {},
        "top_stocks": [],
        "sector_sentiment": {},
    }

    try:
        # 1. 获取板块成分股
        stocks_df = get_sector_stocks(sector_name)
        if stocks_df.empty:
            result["error"] = "无法获取板块成分股数据"
            return result

        # 2. 板块概览统计
        result["summary"] = {
            "total_stocks": len(stocks_df),
            "up_count": len(stocks_df[stocks_df["pct_change"] > 0]),
            "down_count": len(stocks_df[stocks_df["pct_change"] < 0]),
            "avg_pct_change": round(stocks_df["pct_change"].mean(), 2),
            "max_pct_change": round(stocks_df["pct_change"].max(), 2),
            "min_pct_change": round(stocks_df["pct_change"].min(), 2),
            "total_turnover": round(stocks_df["turnover"].sum() / 100000000, 2),  # 转换为亿
            "avg_pe": round(stocks_df["pe"].mean(), 2),
            "avg_pb": round(stocks_df["pb"].mean(), 2),
        }

        # 3. 获取板块情绪
        board_sentiment = get_board_sentiment()
        if not board_sentiment.empty:
            sector_row = board_sentiment[board_sentiment["board_name"] == sector_name]
            if not sector_row.empty:
                result["sector_sentiment"] = {
                    "board_pct": float(sector_row["board_pct"].iloc[0]),
                    "sentiment_score": float(sector_row["sentiment_score"].iloc[0]),
                    "up_count": int(sector_row["up_count"].iloc[0]),
                    "down_count": int(sector_row["down_count"].iloc[0]),
                }

        # 4. 涨幅前10和跌幅前10
        top_gainers = stocks_df.nlargest(10, "pct_change")
        top_losers = stocks_df.nsmallest(10, "pct_change")

        result["top_stocks"] = {
            "gainers": top_gainers[["code", "name", "price", "pct_change", "turnover_rate", "pe", "pb"]].to_dict("records"),
            "losers": top_losers[["code", "name", "price", "pct_change", "turnover_rate", "pe", "pb"]].to_dict("records"),
        }

        result["success"] = True

    except Exception as e:
        result["error"] = str(e)

    return result


def get_all_sectors() -> List[Dict]:
    """
    获取所有板块列表
    :return: 板块列表
    """
    try:
        df = ak.stock_board_industry_name_em()
        if df.empty:
            return []

        sectors = []
        for _, row in df.iterrows():
            sectors.append({
                "name": row["板块名称"],
                "code": row.get("板块代码", ""),
            })
        return sectors
    except Exception as e:
        print(f"获取板块列表失败: {e}")
        return []


def get_hot_sectors(top_n: int = 10) -> pd.DataFrame:
    """
    获取热门板块排行
    :param top_n: 返回前N个板块
    :return: 热门板块DataFrame
    """
    try:
        board_sentiment = get_board_sentiment()
        if board_sentiment.empty:
            return pd.DataFrame()

        # 按情绪得分排序
        hot_sectors = board_sentiment.nlargest(top_n, "sentiment_score")
        return hot_sectors

    except Exception as e:
        print(f"获取热门板块失败: {e}")
        return pd.DataFrame()

