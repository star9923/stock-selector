"""
data_fetcher.py - AkShare 数据获取模块
"""
import data.akshare_config  # 必须在 akshare 之前导入
import akshare as ak
import pandas as pd
import json
import os
from datetime import datetime, timedelta

# 加载本地股票映射
_STOCK_MAPPING = {}
_mapping_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "stock_mapping.json")
if os.path.exists(_mapping_file):
    with open(_mapping_file, "r", encoding="utf-8") as f:
        _STOCK_MAPPING = json.load(f)


def get_stock_list() -> pd.DataFrame:
    """获取 A 股全部股票列表"""
    df = ak.stock_info_a_code_name()
    df.columns = ["code", "name"]
    return df


def get_daily_history(code: str, days: int = 120) -> pd.DataFrame:
    """
    获取单只股票日线历史数据（多源降级）
    优先级：东方财富 -> 新浪财经
    :param code: 股票代码，如 '000001'
    :param days: 获取最近 N 天
    :return: DataFrame，含 date/open/high/low/close/volume/turnover
    """
    # 1. 尝试东方财富
    df = _get_daily_history_em(code, days)
    if not df.empty and len(df) >= 60:
        return df

    # 2. 降级到新浪财经
    df = _get_daily_history_sina(code, days)
    if not df.empty and len(df) >= 60:
        return df

    return pd.DataFrame()


def _get_daily_history_em(code: str, days: int = 120) -> pd.DataFrame:
    """从东方财富获取历史数据"""
    end = datetime.today().strftime("%Y%m%d")
    start = (datetime.today() - timedelta(days=days)).strftime("%Y%m%d")
    try:
        df = ak.stock_zh_a_hist(
            symbol=code,
            period="daily",
            start_date=start,
            end_date=end,
            adjust="qfq",
        )
        df = df.rename(columns={
            "日期": "date",
            "开盘": "open",
            "最高": "high",
            "最低": "low",
            "收盘": "close",
            "成交量": "volume",
            "成交额": "turnover",
            "换手率": "turnover_rate",
        })
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)
        return df
    except Exception:
        return pd.DataFrame()


def _get_daily_history_sina(code: str, days: int = 120) -> pd.DataFrame:
    """从新浪财经获取历史数据"""
    try:
        # 新浪需要 sh/sz 前缀
        if code.startswith("6"):
            symbol = f"sh{code}"
        else:
            symbol = f"sz{code}"

        df = ak.stock_zh_a_daily(symbol=symbol, adjust="qfq")

        if df.empty:
            return pd.DataFrame()

        # 只取最近 N 天
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").tail(days).reset_index(drop=True)

        # 重命名列以匹配格式
        rename_map = {
            "amount": "turnover",
            "turnover": "turnover_rate",
        }
        df = df.rename(columns=rename_map)

        # 确保必要列存在
        if "turnover_rate" not in df.columns:
            df["turnover_rate"] = 0

        return df
    except Exception:
        return pd.DataFrame()


def get_stock_popularity_from_xueqiu() -> pd.DataFrame:
    """
    从雪球获取股票社区热度（独立接口）
    用途：获取股票关注人数，不用于选股
    :return: DataFrame with code, name, followers, price
    """
    try:
        print(f"   使用雪球获取股票社区热度...")
        df = ak.stock_hot_follow_xq()

        if df.empty:
            return pd.DataFrame()

        # 处理股票代码格式
        if '股票代码' in df.columns:
            df['code'] = df['股票代码'].str.replace(r'^(SH|SZ|BJ)', '', regex=True)

        # 重命名列
        column_mapping = {
            "股票简称": "name",
            "最新价": "price",
            "关注": "followers",
        }

        for old_col, new_col in column_mapping.items():
            if old_col in df.columns:
                df[new_col] = df[old_col]

        # 选择需要的列
        cols = ['code', 'name', 'price', 'followers']
        available_cols = [col for col in cols if col in df.columns]
        df = df[available_cols]

        # 过滤无效数据
        df = df[df['code'].notna()]
        df = df[df['code'].str.len() == 6]

        print(f"   ✅ 雪球: 获取到 {len(df)} 只股票的社区热度")
        return df

    except Exception as e:
        print(f"   ⚠️  雪球失败: {str(e)[:50]}")
        return pd.DataFrame()


def get_realtime_quotes_from_xueqiu() -> pd.DataFrame:
    """
    从雪球获取全市场实时行情（推荐）
    优势：稳定、数据全面、社区热度
    :return: DataFrame
    """
    try:
        print(f"   使用雪球获取全市场行情...")
        df = ak.stock_hot_follow_xq()

        if df.empty:
            print(f"   ⚠️  雪球返回空数据")
            return pd.DataFrame()

        # 处理股票代码格式（雪球带有 SH/SZ 前缀）
        if '股票代码' in df.columns:
            df['code'] = df['股票代码'].str.replace(r'^(SH|SZ|BJ)', '', regex=True)

        # 重命名列以匹配原有格式
        column_mapping = {
            "股票代码": "raw_code",
            "股票简称": "name",
            "最新价": "price",
            "关注": "followers",  # 雪球特有：关注人数
        }

        for old_col, new_col in column_mapping.items():
            if old_col in df.columns and new_col not in df.columns:
                df[new_col] = df[old_col]

        # 雪球数据缺少的字段，设置默认值
        default_fields = {
            "pct_change": 0,
            "volume": 0,
            "turnover": 0,
            "turnover_rate": 0,
            "pe": 0,
            "pb": 0,
            "market_cap": 0,
            "float_cap": 0,
        }

        for field, default_value in default_fields.items():
            if field not in df.columns:
                df[field] = default_value

        # 选择需要的列
        required_cols = ["code", "name", "price", "pct_change", "volume",
                        "turnover", "turnover_rate", "pe", "pb", "market_cap", "float_cap"]

        # 只保留存在的列
        available_cols = [col for col in required_cols if col in df.columns]
        df = df[available_cols]

        # 过滤掉无效数据
        df = df[df['code'].notna()]
        df = df[df['code'].str.len() == 6]  # 只保留6位代码

        print(f"   ✅ 雪球: 获取到 {len(df)} 只股票")
        return df

    except Exception as e:
        print(f"   ⚠️  雪球失败: {str(e)[:50]}")
        return pd.DataFrame()


def get_realtime_quotes_from_sina() -> pd.DataFrame:
    """
    从新浪财经获取全市场实时行情（推荐）
    优势：稳定、快速、非交易时间也可用
    :return: DataFrame
    """
    import time

    max_retries = 3
    for attempt in range(max_retries):
        try:
            print(f"   使用新浪财经获取全市场行情...")
            df = ak.stock_zh_a_spot()

            if df.empty:
                print(f"   ⚠️  新浪财经返回空数据")
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                return pd.DataFrame()

            # 处理股票代码格式（新浪可能带有 sh/sz 前缀）
            if 'code' not in df.columns and '代码' in df.columns:
                df['code'] = df['代码']

            # 清理代码格式（去除 sh/sz/bj 前缀）
            if 'code' in df.columns:
                df['code'] = df['code'].str.replace(r'^(sh|sz|bj)', '', regex=True)

            # 重命名列以匹配原有格式
            column_mapping = {
                "代码": "code",
                "名称": "name",
                "最新价": "price",
                "涨跌幅": "pct_change",
                "成交量": "volume",
                "成交额": "turnover",
                "换手率": "turnover_rate",
                "市盈率": "pe",
                "市净率": "pb",
                "总市值": "market_cap",
                "流通市值": "float_cap",
            }

            for old_col, new_col in column_mapping.items():
                if old_col in df.columns and new_col not in df.columns:
                    df[new_col] = df[old_col]

            # 确保必要的列存在
            for col in ["pe", "pb", "market_cap", "float_cap"]:
                if col not in df.columns:
                    df[col] = 0

            # 选择需要的列
            required_cols = ["code", "name", "price", "pct_change", "volume",
                            "turnover", "turnover_rate", "pe", "pb", "market_cap", "float_cap"]

            # 只保留存在的列
            available_cols = [col for col in required_cols if col in df.columns]
            df = df[available_cols]

            # 过滤掉无效数据
            df = df[df['code'].notna()]
            df = df[df['code'].str.len() == 6]  # 只保留6位代码

            print(f"   ✅ 新浪财经: 获取到 {len(df)} 只股票")
            return df

        except Exception as e:
            print(f"   ⚠️  新浪财经失败 (尝试 {attempt + 1}/{max_retries}): {str(e)[:50]}")
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
                return pd.DataFrame()

    return pd.DataFrame()


def get_realtime_quotes_from_em(codes: list, max_workers: int = 8) -> pd.DataFrame:
    """
    从东方财富获取实时行情（备用）
    :param codes: 股票代码列表
    :param max_workers: 并发线程数
    :return: DataFrame
    """
    from tqdm import tqdm
    from concurrent.futures import ThreadPoolExecutor, as_completed

    def _fetch_one(code):
        try:
            df = ak.stock_zh_a_hist(
                symbol=code,
                period="daily",
                start_date=(datetime.today() - timedelta(days=10)).strftime("%Y%m%d"),
                end_date=datetime.today().strftime("%Y%m%d"),
                adjust="qfq",
            )
            if df.empty:
                return None
            latest = df.iloc[-1]
            return {
                "code":         code,
                "name":         _STOCK_MAPPING.get(code, code),
                "price":        latest.get("收盘", 0),
                "pct_change":   latest.get("涨跌幅", 0),
                "volume":       latest.get("成交量", 0),
                "turnover":     latest.get("成交额", 0),
                "turnover_rate": latest.get("换手率", 0),
                "pe":           0,
                "pb":           0,
                "market_cap":   0,
                "float_cap":    latest.get("成交额", 0) * 100,
            }
        except Exception:
            return None

    target_codes = codes[:500]
    print(f"   使用东方财富获取行情（共 {len(target_codes)} 只，{max_workers} 线程）...")

    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_fetch_one, code): code for code in target_codes}
        for future in tqdm(as_completed(futures), total=len(futures), desc="行情获取"):
            result = future.result()
            if result is not None:
                results.append(result)

    if results:
        print(f"   ✅ 东方财富: 获取到 {len(results)} 只股票")
    else:
        print(f"   ⚠️  东方财富: 获取失败")

    return pd.DataFrame(results)


def get_realtime_quotes(codes: list, max_workers: int = 8) -> pd.DataFrame:
    """
    获取多只股票实时行情（多源降级版）
    优先级：新浪财经 -> 东方财富
    注：雪球数据不完整，仅用于社区热度，不用于选股
    :param codes: 股票代码列表（新浪会忽略此参数，获取全市场）
    :param max_workers: 并发线程数
    :return: DataFrame
    """
    # 1. 优先使用新浪财经（全市场，稳定）
    df = get_realtime_quotes_from_sina()
    if not df.empty:
        # 如果指定了codes，只返回这些股票
        if codes:
            df = df[df['code'].isin(codes)]
        return df

    # 2. 降级到东方财富（需要逐个获取）
    print("   ℹ️  新浪财经失败，尝试东方财富...")
    df = get_realtime_quotes_from_em(codes, max_workers)
    return df


def get_financial_indicator(code: str) -> dict:
    """
    获取股票基本面财务指标（最新一期）
    :param code: 股票代码
    :return: dict，含 roe/eps/revenue_growth 等
    """
    try:
        df = ak.stock_financial_analysis_indicator(symbol=code, start_year="2023")
        if df.empty:
            return {}
        latest = df.iloc[0]
        return {
            "roe": _safe_float(latest.get("净资产收益率(%)")),
            "eps": _safe_float(latest.get("基本每股收益(元)")),
            "gross_margin": _safe_float(latest.get("销售毛利率(%)")),
        }
    except Exception:
        return {}


def _safe_float(val) -> float:
    try:
        return float(val)
    except (TypeError, ValueError):
        return float("nan")
