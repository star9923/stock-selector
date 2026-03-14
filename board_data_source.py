"""
board_data_source.py - 板块数据多源获取（优化版）
策略：
1. 板块列表 - 长期缓存（30天），优先同花顺
2. 板块行情 - 短期缓存（1小时），仅东方财富
"""
import akshare_config
import akshare as ak
import pandas as pd
import os
import json
from datetime import datetime, timedelta


SETTINGS_FILE = os.path.join(os.path.dirname(__file__), '.cache', 'settings.json')
CACHE_DIR = os.path.join(os.path.dirname(__file__), '.cache')
BOARD_LIST_CACHE = os.path.join(CACHE_DIR, 'board_list_cache.json')
BOARD_QUOTE_CACHE = os.path.join(CACHE_DIR, 'board_quote_cache.json')


def get_preferred_source() -> str:
    """获取用户首选数据源"""
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                return settings.get('data_source', 'ths')
        except:
            pass
    return 'ths'  # 默认同花顺


def save_board_list_cache(df: pd.DataFrame):
    """保存板块列表到缓存（长期）"""
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        data = {
            'timestamp': datetime.now().isoformat(),
            'data': df.to_dict('records')
        }
        with open(BOARD_LIST_CACHE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"   ✅ 板块列表已缓存 ({len(df)} 个)")
    except Exception as e:
        print(f"   ⚠️  缓存失败: {e}")


def load_board_list_cache(max_age_days: int = 30) -> pd.DataFrame:
    """加载板块列表缓存"""
    if not os.path.exists(BOARD_LIST_CACHE):
        return pd.DataFrame()

    try:
        with open(BOARD_LIST_CACHE, 'r', encoding='utf-8') as f:
            data = json.load(f)

        cache_time = datetime.fromisoformat(data['timestamp'])
        if datetime.now() - cache_time > timedelta(days=max_age_days):
            print(f"   ⚠️  板块列表缓存已过期")
            return pd.DataFrame()

        df = pd.DataFrame(data['data'])
        age_hours = (datetime.now() - cache_time).total_seconds() / 3600
        print(f"   ℹ️  使用板块列表缓存 ({len(df)} 个，{age_hours:.1f}小时前)")
        return df
    except:
        return pd.DataFrame()


def save_board_quote_cache(df: pd.DataFrame):
    """保存板块行情到缓存（短期）"""
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        data = {
            'timestamp': datetime.now().isoformat(),
            'data': df.to_dict('records')
        }
        with open(BOARD_QUOTE_CACHE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"   ✅ 板块行情已缓存 ({len(df)} 个)")
    except Exception as e:
        print(f"   ⚠️  缓存失败: {e}")


def load_board_quote_cache(max_age_hours: int = 1) -> pd.DataFrame:
    """加载板块行情缓存"""
    if not os.path.exists(BOARD_QUOTE_CACHE):
        return pd.DataFrame()

    try:
        with open(BOARD_QUOTE_CACHE, 'r', encoding='utf-8') as f:
            data = json.load(f)

        cache_time = datetime.fromisoformat(data['timestamp'])
        age = datetime.now() - cache_time

        if age > timedelta(hours=max_age_hours):
            print(f"   ⚠️  板块行情缓存已过期")
            return pd.DataFrame()

        df = pd.DataFrame(data['data'])
        age_minutes = age.total_seconds() / 60
        print(f"   ℹ️  使用板块行情缓存 ({len(df)} 个，{age_minutes:.0f}分钟前)")
        return df
    except:
        return pd.DataFrame()


def get_board_list_from_ths() -> pd.DataFrame:
    """
    从同花顺获取行业板块列表
    返回格式: board_name, board_code
    """
    try:
        df = ak.stock_board_industry_name_ths()
        if df.empty:
            return pd.DataFrame()

        df = df.rename(columns={'name': 'board_name', 'code': 'board_code'})
        print(f"   ✅ 同花顺: 获取到 {len(df)} 个行业板块")
        return df
    except Exception as e:
        print(f"   ⚠️  同花顺接口失败: {str(e)[:50]}")
        return pd.DataFrame()


def get_board_list_from_em() -> pd.DataFrame:
    """
    从东方财富获取行业板块列表
    返回格式: board_name
    """
    try:
        df = ak.stock_board_industry_name_em()
        if df.empty:
            return pd.DataFrame()

        df = df.rename(columns={'板块名称': 'board_name', '板块代码': 'board_code'})
        print(f"   ✅ 东方财富: 获取到 {len(df)} 个行业板块")
        return df
    except Exception as e:
        print(f"   ⚠️  东方财富接口失败: {str(e)[:50]}")
        return pd.DataFrame()


def get_board_sentiment_from_em() -> pd.DataFrame:
    """
    从东方财富获取板块实时行情（含涨跌幅、上涨下跌家数）
    """
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
            df["board_pct"] * 2 +
            (df["up_count"] / (df["up_count"] + df["down_count"] + 1)) * 30
        )

        df['total_count'] = df['up_count'] + df['down_count']

        print(f"   ✅ 东方财富: 获取到 {len(df)} 个板块行情")
        return df[["board_name", "board_pct", "sentiment_score", "up_count", "down_count", "total_count"]]
    except Exception as e:
        print(f"   ⚠️  东方财富板块行情失败: {str(e)[:50]}")
        return pd.DataFrame()
    finally:
        socket.setdefaulttimeout(original_timeout)


def get_board_list_multi_source() -> pd.DataFrame:
    """
    多源获取板块列表（优化版）
    策略：
    1. 尝试从缓存加载（30天有效）
    2. 缓存失效则根据用户设置获取
    3. 成功后更新缓存
    """
    # 1. 尝试缓存
    df = load_board_list_cache(max_age_days=30)
    if not df.empty:
        return df

    # 2. 根据设置获取
    preferred = get_preferred_source()

    if preferred == 'ths':
        # 优先同花顺
        df = get_board_list_from_ths()
        if not df.empty:
            save_board_list_cache(df)
            return df
        # 备用东方财富
        print("   ℹ️  同花顺失败，尝试东方财富")
        df = get_board_list_from_em()
        if not df.empty:
            save_board_list_cache(df)
            return df
    else:
        # 优先东方财富
        df = get_board_list_from_em()
        if not df.empty:
            save_board_list_cache(df)
            return df
        # 备用同花顺
        print("   ℹ️  东方财富失败，尝试同花顺")
        df = get_board_list_from_ths()
        if not df.empty:
            save_board_list_cache(df)
            return df

    return pd.DataFrame()


def get_board_sentiment_multi_source() -> pd.DataFrame:
    """
    获取板块行情数据（优化版）
    策略：
    1. 尝试从东方财富获取实时数据
    2. 失败则使用缓存（1小时内）
    3. 成功后更新缓存
    """
    # 1. 尝试实时获取
    df = get_board_sentiment_from_em()
    if not df.empty:
        save_board_quote_cache(df)
        return df

    # 2. 使用缓存
    df = load_board_quote_cache(max_age_hours=24)  # 放宽到24小时
    if not df.empty:
        return df

    return pd.DataFrame()
