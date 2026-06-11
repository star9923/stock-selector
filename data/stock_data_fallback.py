"""
stock_data_fallback.py - 个股数据缓存方案
当API获取失败时，从本地缓存加载
"""
import pandas as pd
import json
import os
from datetime import datetime, timedelta


STOCK_CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.cache', 'stock_history')


def save_stock_history_cache(code: str, df: pd.DataFrame):
    """
    保存股票历史数据到缓存
    """
    try:
        os.makedirs(STOCK_CACHE_DIR, exist_ok=True)
        cache_file = os.path.join(STOCK_CACHE_DIR, f"{code}.json")

        # 转换日期为字符串
        df_copy = df.copy()
        df_copy['date'] = df_copy['date'].dt.strftime('%Y-%m-%d')

        data = {
            'timestamp': datetime.now().isoformat(),
            'code': code,
            'data': df_copy.to_dict('records')
        }

        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"   ⚠️  保存股票缓存失败: {e}")


def load_stock_history_cache(code: str, max_age_days: int = 1) -> pd.DataFrame:
    """
    从缓存加载股票历史数据
    """
    cache_file = os.path.join(STOCK_CACHE_DIR, f"{code}.json")

    if not os.path.exists(cache_file):
        return pd.DataFrame()

    try:
        with open(cache_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 检查缓存时间
        cache_time = datetime.fromisoformat(data['timestamp'])
        if datetime.now() - cache_time > timedelta(days=max_age_days):
            return pd.DataFrame()

        df = pd.DataFrame(data['data'])
        df['date'] = pd.to_datetime(df['date'])

        return df
    except Exception as e:
        print(f"   ⚠️  加载股票缓存失败 {code}: {e}")
        return pd.DataFrame()


def get_stock_history_with_fallback(code: str, days: int = 120, prefer_cache: bool = False) -> pd.DataFrame:
    """
    获取股票历史数据，失败时使用缓存
    :param code: 股票代码
    :param days: 获取最近 N 天
    :param prefer_cache: 是否优先使用 1 天内本地缓存，适合盘中重复快速筛选
    """
    from data.data_fetcher import get_daily_history

    if prefer_cache:
        df = load_stock_history_cache(code, max_age_days=1)
        if not df.empty and len(df) >= 60:
            return df.tail(days).reset_index(drop=True)

    # 1. 尝试从 API 获取
    df = get_daily_history(code, days)
    if not df.empty and len(df) >= 60:
        save_stock_history_cache(code, df)
        return df

    # 2. 从缓存加载
    df = load_stock_history_cache(code, max_age_days=1)
    if not df.empty and len(df) >= 60:
        return df.tail(days).reset_index(drop=True)

    # 无可用数据
    return pd.DataFrame()
