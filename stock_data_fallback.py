"""
stock_data_fallback.py - 个股数据缓存方案
当API获取失败时，从本地缓存加载
"""
import pandas as pd
import json
import os
from datetime import datetime, timedelta


STOCK_CACHE_DIR = os.path.join(os.path.dirname(__file__), '.cache', 'stock_history')


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

        print(f"   ✅ 股票 {code} 历史数据已保存到缓存")
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
            print(f"   ⚠️  股票缓存已过期 (>{max_age_days}天)")
            return pd.DataFrame()

        df = pd.DataFrame(data['data'])
        df['date'] = pd.to_datetime(df['date'])

        print(f"   ℹ️  从缓存加载股票 {code} 历史数据 ({len(df)} 天)")
        return df
    except Exception as e:
        print(f"   ⚠️  加载股票缓存失败: {e}")
        return pd.DataFrame()


def get_stock_history_with_fallback(code: str, days: int = 120) -> pd.DataFrame:
    """
    获取股票历史数据，失败时使用缓存
    优先级：
    1. 尝试从API获取
    2. 从缓存加载（1天内）
    """
    from data_fetcher import get_daily_history

    # 1. 尝试从API获取
    df = get_daily_history(code, days)
    if not df.empty and len(df) >= 60:
        save_stock_history_cache(code, df)
        return df

    # 2. 从缓存加载
    df = load_stock_history_cache(code, max_age_days=1)
    if not df.empty and len(df) >= 60:
        return df

    # 无可用数据
    return pd.DataFrame()
