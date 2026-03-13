"""
sentiment.py - 市场情绪与板块热度分析模块
"""
import akshare as ak
import pandas as pd
from typing import Dict, List


def get_hot_stocks() -> pd.DataFrame:
    """获取热门股票排行（东方财富）"""
    try:
        df = ak.stock_hot_rank_em()
        df = df.rename(columns={
            "代码": "code",
            "股票名称": "name",
            "当前排名": "rank",
        })
        # 提取纯数字代码
        df["code"] = df["code"].str.replace(r"^(SH|SZ)", "", regex=True)
        return df[["code", "name", "rank"]].head(100)
    except Exception:
        return pd.DataFrame()


def get_board_sentiment() -> pd.DataFrame:
    """获取行业板块实时情绪（涨跌幅、领涨股数量）"""
    try:
        df = ak.stock_board_industry_spot_em()
        if df.empty:
            return pd.DataFrame()

        df = df.rename(columns={
            "板块名称": "board_name",
            "涨跌幅": "board_pct",
            "总市值": "board_cap",
            "换手率": "board_turnover",
            "上涨家数": "up_count",
            "下跌家数": "down_count",
        })
        # 计算板块情绪得分
        df["sentiment_score"] = (
            df["board_pct"] * 2 +  # 涨跌幅权重
            (df["up_count"] / (df["up_count"] + df["down_count"] + 1)) * 30  # 上涨比例
        )
        return df[["board_name", "board_pct", "sentiment_score", "up_count", "down_count"]]
    except Exception as e:
        print(f"   ⚠️  板块数据获取失败: {str(e)[:100]}")
        return pd.DataFrame()


def get_stock_board_mapping() -> Dict[str, str]:
    """获取股票 -> 行业板块映射"""
    try:
        boards = ak.stock_board_industry_name_em()
        if boards.empty:
            return {}

        mapping = {}
        print(f"   正在获取 {len(boards)} 个板块的成分股...")
        for idx, row in boards.iterrows():
            board_name = row["板块名称"]
            try:
                cons = ak.stock_board_industry_cons_em(symbol=board_name)
                for _, stock in cons.iterrows():
                    code = stock["代码"]
                    mapping[code] = board_name
            except Exception:
                continue
            # 每10个板块打印进度
            if (idx + 1) % 10 == 0:
                print(f"   进度: {idx + 1}/{len(boards)}")
        return mapping
    except Exception as e:
        print(f"   ⚠️  板块映射获取失败: {str(e)[:100]}")
        return {}


def score_sentiment(code: str, hot_stocks: pd.DataFrame, board_sentiment: pd.DataFrame,
                    stock_board_map: Dict[str, str]) -> dict:
    """
    计算单只股票的市场情绪得分
    :param code: 股票代码
    :param hot_stocks: 热门股票 DataFrame
    :param board_sentiment: 板块情绪 DataFrame
    :param stock_board_map: 股票->板块映射
    :return: 情绪得分字典
    """
    hot_score = 0
    board_score = 0
    board_name = "未知"

    # 1. 热度得分（0-30分）
    if not hot_stocks.empty and code in hot_stocks["code"].values:
        rank = hot_stocks[hot_stocks["code"] == code]["rank"].iloc[0]
        if rank <= 10:
            hot_score = 30
        elif rank <= 30:
            hot_score = 20
        elif rank <= 50:
            hot_score = 15
        else:
            hot_score = 10

    # 2. 板块情绪得分（0-30分）
    if stock_board_map:
        board_name = stock_board_map.get(code, "未知")
        if board_name != "未知" and not board_sentiment.empty:
            board_row = board_sentiment[board_sentiment["board_name"] == board_name]
            if not board_row.empty:
                sentiment = board_row["sentiment_score"].iloc[0]
                board_pct = board_row["board_pct"].iloc[0]

                # 板块涨幅加分
                if board_pct > 3:
                    board_score += 20
                elif board_pct > 1:
                    board_score += 15
                elif board_pct > 0:
                    board_score += 10
                elif board_pct < -2:
                    board_score -= 10

                # 板块情绪加分
                if sentiment > 20:
                    board_score += 10
                elif sentiment > 10:
                    board_score += 5

    total = hot_score + board_score

    return {
        "total": min(max(total, 0), 60),  # 限制在 0-60 分
        "hot_score": hot_score,
        "board_score": board_score,
        "board_name": board_name,
    }


def get_sentiment_data() -> tuple:
    """
    获取所有情绪数据（缓存用）
    :return: (hot_stocks, board_sentiment, stock_board_map)
    """
    print("📰 获取市场情绪数据...")
    hot_stocks = get_hot_stocks()
    print(f"   热门股票: {len(hot_stocks)} 只")

    board_sentiment = get_board_sentiment()
    if not board_sentiment.empty:
        print(f"   板块情绪: {len(board_sentiment)} 个板块")
    else:
        print("   ⚠️  板块情绪数据为空，可能是网络问题")

    stock_board_map = {}
    if not board_sentiment.empty:
        print("🗺️  构建股票-板块映射（较慢，请稍候）...")
        stock_board_map = get_stock_board_mapping()
        print(f"   映射完成: {len(stock_board_map)} 只股票")
    else:
        print("   ⚠️  跳过板块映射（板块数据不可用）")

    return hot_stocks, board_sentiment, stock_board_map
