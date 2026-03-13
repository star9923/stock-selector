"""
data_fetcher.py - AkShare 数据获取模块
"""
import akshare as ak
import pandas as pd
import json
import os
from datetime import datetime, timedelta

# 加载本地股票映射
_STOCK_MAPPING = {}
_mapping_file = os.path.join(os.path.dirname(__file__), "stock_mapping.json")
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
    获取单只股票日线历史数据
    :param code: 股票代码，如 '000001'
    :param days: 获取最近 N 天
    :return: DataFrame，含 date/open/high/low/close/volume/turnover
    """
    end = datetime.today().strftime("%Y%m%d")
    start = (datetime.today() - timedelta(days=days)).strftime("%Y%m%d")
    try:
        df = ak.stock_zh_a_hist(
            symbol=code,
            period="daily",
            start_date=start,
            end_date=end,
            adjust="qfq",  # 前复权
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


def get_realtime_quotes(codes: list, max_workers: int = 8) -> pd.DataFrame:
    """
    获取多只股票实时行情（并发版）
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
    print(f"   并发获取最新行情（共 {len(target_codes)} 只，{max_workers} 线程）...")

    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_fetch_one, code): code for code in target_codes}
        for future in tqdm(as_completed(futures), total=len(futures), desc="行情获取"):
            result = future.result()
            if result is not None:
                results.append(result)

    return pd.DataFrame(results)


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
