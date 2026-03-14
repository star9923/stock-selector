"""
sector_data_fallback.py - 板块数据缓存方案
当API获取失败时，从本地缓存加载
"""
import pandas as pd
import json
import os
from datetime import datetime, timedelta


FALLBACK_CACHE_FILE = os.path.join(os.path.dirname(__file__), '.cache', 'board_sentiment_fallback.json')
SECTOR_STOCKS_CACHE_DIR = os.path.join(os.path.dirname(__file__), '.cache', 'sector_stocks')


def save_board_data_to_fallback(df: pd.DataFrame):
    """保存板块数据到备用缓存文件"""
    try:
        os.makedirs(os.path.dirname(FALLBACK_CACHE_FILE), exist_ok=True)
        data = {
            'timestamp': datetime.now().isoformat(),
            'data': df.to_dict('records')
        }
        with open(FALLBACK_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"   ✅ 板块数据已保存到备用缓存")
    except Exception as e:
        print(f"   ⚠️  保存备用缓存失败: {e}")


def load_board_data_from_fallback(max_age_days: int = 7) -> pd.DataFrame:
    """从备用缓存加载板块数据"""
    if not os.path.exists(FALLBACK_CACHE_FILE):
        return pd.DataFrame()

    try:
        with open(FALLBACK_CACHE_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)

        cache_time = datetime.fromisoformat(data['timestamp'])
        if datetime.now() - cache_time > timedelta(days=max_age_days):
            print(f"   ⚠️  备用缓存已过期 (>{max_age_days}天)")
            return pd.DataFrame()

        df = pd.DataFrame(data['data'])
        print(f"   ℹ️  从备用缓存加载板块数据 ({len(df)} 个板块)")
        return df
    except Exception as e:
        print(f"   ⚠️  加载备用缓存失败: {e}")
        return pd.DataFrame()


def get_board_sentiment_with_fallback() -> pd.DataFrame:
    """
    获取板块情绪数据，失败时使用缓存
    优先级：
    1. 尝试从API获取
    2. 从备用缓存加载
    """
    from sentiment import get_board_sentiment

    # 1. 尝试从API获取
    df = get_board_sentiment()
    if not df.empty:
        df['total_count'] = df['up_count'] + df['down_count']
        save_board_data_to_fallback(df)
        return df

    # 2. 从备用缓存加载
    df = load_board_data_from_fallback()
    if not df.empty:
        return df

    # 无可用数据
    return pd.DataFrame()


def save_sector_stocks_cache(sector_name: str, df: pd.DataFrame):
    """保存板块成分股到缓存"""
    try:
        os.makedirs(SECTOR_STOCKS_CACHE_DIR, exist_ok=True)
        cache_file = os.path.join(SECTOR_STOCKS_CACHE_DIR, f"{sector_name}.json")

        data = {
            'timestamp': datetime.now().isoformat(),
            'sector_name': sector_name,
            'data': df.to_dict('records')
        }

        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"   ✅ 板块 {sector_name} 成分股已保存到缓存")
    except Exception as e:
        print(f"   ⚠️  保存板块缓存失败: {e}")


def load_sector_stocks_cache(sector_name: str, max_age_days: int = 7) -> pd.DataFrame:
    """从缓存加载板块成分股"""
    cache_file = os.path.join(SECTOR_STOCKS_CACHE_DIR, f"{sector_name}.json")

    if not os.path.exists(cache_file):
        return pd.DataFrame()

    try:
        with open(cache_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        cache_time = datetime.fromisoformat(data['timestamp'])
        if datetime.now() - cache_time > timedelta(days=max_age_days):
            print(f"   ⚠️  板块缓存已过期 (>{max_age_days}天)")
            return pd.DataFrame()

        df = pd.DataFrame(data['data'])
        print(f"   ℹ️  从缓存加载板块 {sector_name} 成分股 ({len(df)} 只)")
        return df
    except Exception as e:
        print(f"   ⚠️  加载板块缓存失败: {e}")
        return pd.DataFrame()


def get_sector_stocks_with_fallback(sector_name: str) -> pd.DataFrame:
    """
    获取板块成分股，失败时使用缓存
    优先级：
    1. 尝试从API获取
    2. 从缓存加载
    """
    from sector_analyzer import get_sector_stocks

    # 1. 尝试从API获取
    df = get_sector_stocks(sector_name)
    if not df.empty:
        save_sector_stocks_cache(sector_name, df)
        return df

    # 2. 从缓存加载
    df = load_sector_stocks_cache(sector_name)
    if not df.empty:
        return df

    # 无可用数据
    return pd.DataFrame()
