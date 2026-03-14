"""
sentiment.py - 市场情绪与板块热度分析模块
"""
import os
import warnings

# 必须在导入 requests/akshare 之前设置
os.environ['NO_PROXY'] = '*'
os.environ['no_proxy'] = '*'
# 清除代理设置
for key in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY']:
    os.environ.pop(key, None)

import akshare as ak
import pandas as pd
from typing import Dict, List
import time
from functools import wraps
import json
from datetime import datetime, timedelta
from sector_fallback import update_sector_mapping_with_fallback

# 忽略 SSL 警告
warnings.filterwarnings('ignore', category=Warning)

# 配置 urllib3
import urllib3
urllib3.disable_warnings()

# 缓存目录
CACHE_DIR = os.path.join(os.path.dirname(__file__), '.cache')
os.makedirs(CACHE_DIR, exist_ok=True)


def load_cache(cache_name: str, max_age_hours: int = 24) -> pd.DataFrame:
    """加载缓存数据"""
    cache_file = os.path.join(CACHE_DIR, f"{cache_name}.json")
    if not os.path.exists(cache_file):
        return pd.DataFrame()

    try:
        with open(cache_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 检查缓存时间
        cache_time = datetime.fromisoformat(data['timestamp'])
        if datetime.now() - cache_time > timedelta(hours=max_age_hours):
            return pd.DataFrame()

        return pd.DataFrame(data['data'])
    except Exception:
        return pd.DataFrame()


def save_cache(cache_name: str, df: pd.DataFrame):
    """保存缓存数据"""
    cache_file = os.path.join(CACHE_DIR, f"{cache_name}.json")
    try:
        data = {
            'timestamp': datetime.now().isoformat(),
            'data': df.to_dict('records')
        }
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def retry_on_failure(max_retries=3, delay=2, backoff=2):
    """重试装饰器，支持指数退避和缓存降级"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_name = func.__name__

            # 先尝试从缓存加载
            cached = load_cache(cache_name, max_age_hours=6)

            retries = 0
            current_delay = delay
            while retries < max_retries:
                try:
                    result = func(*args, **kwargs)
                    # 成功则保存缓存
                    if not result.empty if isinstance(result, pd.DataFrame) else result:
                        save_cache(cache_name, result if isinstance(result, pd.DataFrame) else pd.DataFrame())
                    return result
                except Exception as e:
                    retries += 1
                    if retries >= max_retries:
                        print(f"   ⚠️  {func.__name__} 失败 (重试{max_retries}次): {str(e)[:80]}")
                        # 使用缓存降级
                        if not cached.empty:
                            print(f"   ℹ️  使用缓存数据 (可能不是最新)")
                            return cached
                        return pd.DataFrame() if 'DataFrame' in str(func.__annotations__.get('return', '')) else {}
                    print(f"   ⏳ {func.__name__} 重试 {retries}/{max_retries}，等待 {current_delay}s...")
                    time.sleep(current_delay)
                    current_delay *= backoff
            return cached if not cached.empty else pd.DataFrame()
        return wrapper
    return decorator


@retry_on_failure(max_retries=3, delay=1, backoff=2)
def get_hot_stocks() -> pd.DataFrame:
    """获取热门股票排行（东方财富）"""
    df = ak.stock_hot_rank_em()
    df = df.rename(columns={
        "代码": "code",
        "股票名称": "name",
        "当前排名": "rank",
    })
    # 提取纯数字代码
    df["code"] = df["code"].str.replace(r"^(SH|SZ)", "", regex=True)
    return df[["code", "name", "rank"]].head(100)


@retry_on_failure(max_retries=3, delay=3, backoff=2)
def get_board_sentiment() -> pd.DataFrame:
    """获取行业板块实时情绪（涨跌幅、领涨股数量）"""
    # 增加超时时间以应对慢速网络
    import socket
    original_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(30)

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
    finally:
        socket.setdefaulttimeout(original_timeout)


@retry_on_failure(max_retries=2, delay=1, backoff=1.5)
def get_stock_board_mapping() -> Dict[str, str]:
    """获取股票 -> 行业板块映射"""
    boards = ak.stock_board_industry_name_em()
    if boards.empty:
        return {}

    mapping = {}
    print(f"   正在获取 {len(boards)} 个板块的成分股...")

    # 限制只获取前50个板块，避免超时
    boards_limited = boards.head(50)

    for idx, row in boards_limited.iterrows():
        board_name = row["板块名称"]
        try:
            cons = ak.stock_board_industry_cons_em(symbol=board_name)
            for _, stock in cons.iterrows():
                code = stock["代码"]
                # 只保留第一个匹配的板块（避免重复）
                if code not in mapping:
                    mapping[code] = board_name
        except Exception:
            continue
        # 每10个板块打印进度
        if (idx + 1) % 10 == 0:
            print(f"   进度: {idx + 1}/{len(boards_limited)}")

    print(f"   映射完成: {len(mapping)} 只股票")
    return mapping


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
        print("   ⚠️  板块情绪数据为空，将使用备用方案获取板块映射")

    # 无论板块情绪是否成功，都尝试获取板块映射
    print("🗺️  构建股票-板块映射（较慢，请稍候）...")
    stock_board_map = get_stock_board_mapping()

    # 使用备用映射补充
    stock_board_map = update_sector_mapping_with_fallback(stock_board_map)

    if not stock_board_map:
        print("   ⚠️  板块映射获取失败，情绪分析功能受限")
    else:
        print(f"   映射完成: {len(stock_board_map)} 只股票（含备用数据）")

    return hot_stocks, board_sentiment, stock_board_map
