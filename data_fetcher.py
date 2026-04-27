"""
data_fetcher.py - AkShare 数据获取模块（支持东方财富/新浪财经）
"""
import akshare as ak
import pandas as pd
import json
import os
import time
import requests
from datetime import datetime, timedelta
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

_session = requests.Session()
_session.mount("http://", HTTPAdapter(max_retries=Retry(total=3, backoff_factor=1)))
_session.mount("https://", HTTPAdapter(max_retries=Retry(total=3, backoff_factor=1)))

_data_source = "sina"  # eastmoney or sina
_STOCK_MAPPING = {}


def get_stock_list() -> pd.DataFrame:
    """获取 A 股全部股票列表"""
    for attempt in range(3):
        try:
            df = ak.stock_info_a_code_name()
            df.columns = ["code", "name"]
            return df
        except Exception as e:
            if attempt < 2:
                time.sleep(2)
            else:
                raise e
    return pd.DataFrame()


def _init_stock_mapping():
    """初始化股票代码映射"""
    global _STOCK_MAPPING
    try:
        df = get_stock_list()
        if not df.empty:
            _STOCK_MAPPING = dict(zip(df["code"].astype(str), df["name"].astype(str)))
            print(f"[INFO] 股票列表加载完成: {len(_STOCK_MAPPING)} 只")
    except Exception as e:
        print(f"[WARN] 股票列表加载失败: {e}")


# 启动时初始化
_init_stock_mapping()


_history_cache = {}

def get_daily_history(code: str, days: int = 60) -> pd.DataFrame:
    """
    获取单只股票日线历史数据
    :param code: 股票代码，如 '000001'
    :param days: 获取最近 N 天
    :return: DataFrame，含 date/open/high/low/close/volume/turnover
    """
    df = _get_daily_history_eastmoney(code, days)
    if df.empty:
        df = _get_daily_history_sina(code, days)
    return df


def _get_daily_history_eastmoney(code: str, days: int = 120) -> pd.DataFrame:
    end = datetime.today().strftime("%Y%m%d")
    start = (datetime.today() - timedelta(days=days)).strftime("%Y%m%d")
    for attempt in range(3):
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
            if attempt < 2:
                time.sleep(2)
    return pd.DataFrame()


def _get_daily_history_sina(code: str, days: int = 120) -> pd.DataFrame:
    """使用新浪财经接口获取历史数据"""
    try:
        if code.startswith("6"):
            sina_code = f"sh{code}"
        else:
            sina_code = f"sz{code}"
        
        url = f"https://quotes.sina.cn/cn/api/jsonp.php/var%20_{code}=/CN_MarketDataService.getKLineData?symbol={sina_code}&scale=240&ma=5&datalen={days}"
        resp = requests.get(url, timeout=10)
        text = resp.text
        if not text or "null" in text:
            return pd.DataFrame()
        
        import re
        match = re.search(r'\[.*\]', text)
        if not match:
            return pd.DataFrame()
        
        import json as json_lib
        data = json_lib.loads(match.group())
        if not data:
            return pd.DataFrame()
        
        df = pd.DataFrame(data)
        df = df.rename(columns={
            "day": "date",
            "open": "open",
            "high": "high",
            "low": "low",
            "close": "close",
            "volume": "volume",
        })
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)
        df["turnover"] = 0
        df["turnover_rate"] = 0
        return df
    except Exception:
        return pd.DataFrame()


def get_realtime_quotes(codes: list, max_workers: int = 8, max_stocks: int = None) -> pd.DataFrame:
    """
    获取多只股票实时行情（并发版）
    :param codes: 股票代码列表
    :param max_workers: 并发线程数
    :param max_stocks: 最大股票数量，默认从配置文件读取
    :return: DataFrame
    """
    import json
    from tqdm import tqdm
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    if max_stocks is None:
        try:
            with open("config.json", "r") as f:
                config = json.load(f)
                max_stocks = config.get("max_stocks", 2000)
        except:
            max_stocks = 2000
    
    codes = codes[:max_stocks]

    def _fetch_via_spot():
        """Use EastMoney spot API"""
        try:
            df = ak.stock_zh_a_spot_em()
            if not df.empty:
                df = df[df["代码"].isin(codes)]
                rename_dict = {
                    "代码": "code",
                    "名称": "name",
                    "最新价": "price",
                    "涨跌幅": "pct_change",
                    "成交量": "volume",
                    "成交额": "turnover",
                    "振幅": "amplitude",
                    "最高": "high",
                    "最低": "low",
                    "今开": "open",
                    "昨收": "pre_close",
                    "量比": "volume_ratio",
                    "换手率": "turnover_rate",
                    "市盈率-动态": "pe",
                    "市净率": "pb",
                    "总市值": "market_cap",
                    "流通市值": "float_cap",
                }
                df = df.rename(columns=rename_dict)
                return df
        except Exception as e:
            print(f"Spot API error: {e}")
        return pd.DataFrame()

    def _fetch_via_eastmoney(codes: list) -> pd.DataFrame:
        """Use EastMoney HTTP API"""
        try:
            results = []
            all_codes = codes[:max_stocks]
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://quote.eastmoney.com",
                "Accept": "*/*",
            }
            for i in range(0, len(all_codes), 100):
                batch = all_codes[i:i+100]
                secids = ",".join([f"1.{code}" if code.startswith("6") else f"0.{code}" for code in batch])
                url = f"http://push2.eastmoney.com/api/qt/ulist.np/get?pn=1&pz=100&po=1&np=1&fltt=2&invt=2&fid=f3&fs=m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23&secids={secids}&fields=f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f13,f14,f15,f16,f17,f18,f20,f21,f23,f24,f25,f37,f38,f39,f40,f41,f45,f57,f62,f115,f128,f140,f141"
                resp = requests.get(url, headers=headers, timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("data", {}).get("diff"):
                        for item in data["data"]["diff"]:
                            try:
                                code = str(item.get("f12", ""))
                                price = item.get("f2", 0)
                                # 处理非交易时段返回'-'的情况
                                if price == "-" or price is None:
                                    price = 0
                                pct = item.get("f3", 0)
                                if pct == "-" or pct is None:
                                    pct = 0
                                volume = item.get("f5", 0)
                                if volume == "-" or volume is None:
                                    volume = 0
                                turnover = item.get("f6", 0)
                                if turnover == "-" or turnover is None:
                                    turnover = 0
                                if code and price:
                                    results.append({
                                        "code": code,
                                        "name": item.get("f14", ""),
                                        "price": price,
                                        "pct_change": pct,
                                        "volume": volume,
                                        "turnover": turnover,
                                        "turnover_rate": item.get("f8", 0),
                                        "volume_ratio": item.get("f10", 0),
                                        "pe": item.get("f9", 0),
                                        "pb": item.get("f23", 0),
                                        "market_cap": item.get("f20", 0),
                                        "float_cap": item.get("f21", 0),
                                    })
                            except Exception:
                                pass
            return pd.DataFrame(results)
        except Exception as e:
            print(f"EastMoney API error: {e}")
        return pd.DataFrame()

    def _fetch_via_sina(codes: list) -> pd.DataFrame:
        """Use Sina财经 API"""
        try:
            results = []
            all_codes = codes[:max_stocks]
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": "http://finance.sina.com.cn",
                "Accept": "*/*",
            }
            for i in range(0, len(all_codes), 80):
                batch = all_codes[i:i+80]
                sina_codes = []
                for code in batch:
                    if code.startswith("6"):
                        sina_code = f"sh{code}"
                    else:
                        sina_code = f"sz{code}"
                    sina_codes.append(sina_code)
                url = f"http://hq.sinajs.cn/list={','.join(sina_codes)}"
                resp = requests.get(url, headers=headers, timeout=10)
                if resp.status_code == 200:
                    text = resp.content.decode("gbk")
                    for line in text.split("\n"):
                        if "=" in line:
                            parts = line.split("=")[1].split(",")
                            if len(parts) > 30:
                                try:
                                    sina_code = line.split("=")[0].split("_")[-1]
                                    code = sina_code[2:] if sina_code.startswith("sh") or sina_code.startswith("sz") else ""
                                    name = parts[0].strip('"') if parts[0] else code
                                    price = float(parts[3]) if parts[3] else 0
                                    pre_close = float(parts[2]) if parts[2] else 0
                                    pct = 0
                                    if pre_close > 0:
                                        pct = (price - pre_close) / pre_close * 100
                                    open_price = float(parts[1]) if parts[1] else 0
                                    high = float(parts[4]) if parts[4] else 0
                                    low = float(parts[5]) if parts[5] else 0
                                    volume = float(parts[8]) if parts[8] else 0
                                    turnover = float(parts[9]) if parts[9] else 0
                                    turnover_rate = float(parts[38]) if len(parts) > 38 and parts[38] else 0
                                    pe = float(parts[43]) if len(parts) > 43 and parts[43] else 0
                                    pb = float(parts[46]) if len(parts) > 46 and parts[46] else 0
                                    market_cap = float(parts[45]) if len(parts) > 45 and parts[45] else 0
                                    float_cap = float(parts[44]) if len(parts) > 44 and parts[44] else 0
                                    if code and price > 0:
                                        results.append({
                                            "code": code,
                                            "name": name,
                                            "price": price,
                                            "pct_change": pct,
                                            "volume": volume,
                                            "turnover": turnover,
                                            "turnover_rate": turnover_rate,
                                            "volume_ratio": 0,
                                            "pe": pe,
                                            "pb": pb,
                                            "market_cap": market_cap,
                                            "float_cap": float_cap,
                                        })
                                except:
                                    pass
            return pd.DataFrame(results)
        except Exception as e:
            print(f"Sina API error: {e}")
        return pd.DataFrame()

    def _fetch_one(code):
        for attempt in range(3):
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
                    "volume_ratio": 0,
                    "pe":           0,
                    "pb":           0,
                    "market_cap":   0,
                    "float_cap":    latest.get("成交额", 0) * 100,
                }
            except Exception:
                if attempt < 2:
                    time.sleep(1)
                else:
                    return None
        return None

    # Try EastMoney API first
    print(f"   Trying EastMoney API...")
    df_em = _fetch_via_eastmoney(codes)
    if not df_em.empty:
        df_em["price"] = pd.to_numeric(df_em["price"], errors="coerce").fillna(0)
        df_em["pct_change"] = pd.to_numeric(df_em["pct_change"], errors="coerce").fillna(0)
        df_em["volume"] = pd.to_numeric(df_em["volume"], errors="coerce").fillna(0)
        df_em["turnover"] = pd.to_numeric(df_em["turnover"], errors="coerce").fillna(0)
        df_em["turnover_rate"] = pd.to_numeric(df_em["turnover_rate"], errors="coerce").fillna(0)
        df_em["volume_ratio"] = pd.to_numeric(df_em["volume_ratio"], errors="coerce").fillna(0)
        df_em["pe"] = pd.to_numeric(df_em["pe"], errors="coerce").fillna(0)
        df_em["pb"] = pd.to_numeric(df_em["pb"], errors="coerce").fillna(0)
        df_em["market_cap"] = pd.to_numeric(df_em["market_cap"], errors="coerce").fillna(0)
        df_em["float_cap"] = pd.to_numeric(df_em["float_cap"], errors="coerce").fillna(0)
        
        # 检查是否有有效数据
        valid_count = len(df_em[df_em["price"] > 0])
        print(f"   Got {len(df_em)} stocks, {valid_count} with valid price")
        
        if valid_count > 100:
            return df_em
    
    # Try Sina API (fallback)
    print(f"   Trying Sina API...")
    df_sina = _fetch_via_sina(codes)
    if not df_sina.empty:
        df_sina["price"] = pd.to_numeric(df_sina["price"], errors="coerce").fillna(0)
        df_sina["pct_change"] = pd.to_numeric(df_sina["pct_change"], errors="coerce").fillna(0)
        df_sina["volume"] = pd.to_numeric(df_sina["volume"], errors="coerce").fillna(0)
        df_sina["turnover"] = pd.to_numeric(df_sina["turnover"], errors="coerce").fillna(0)
        df_sina["turnover_rate"] = pd.to_numeric(df_sina["turnover_rate"], errors="coerce").fillna(0)
        df_sina["volume_ratio"] = pd.to_numeric(df_sina["volume_ratio"], errors="coerce").fillna(0)
        df_sina["pe"] = pd.to_numeric(df_sina["pe"], errors="coerce").fillna(0)
        df_sina["pb"] = pd.to_numeric(df_sina["pb"], errors="coerce").fillna(0)
        df_sina["market_cap"] = pd.to_numeric(df_sina["market_cap"], errors="coerce").fillna(0)
        df_sina["float_cap"] = pd.to_numeric(df_sina["float_cap"], errors="coerce").fillna(0)
        valid_count = len(df_sina[df_sina["price"] > 0])
        print(f"   Got {len(df_sina)} stocks, {valid_count} with valid price")
        
        if valid_count > 100:
            return df_sina

    # Last fallback: use last close price from historical data (limited to 500 for speed)
    target_codes = codes[:max_stocks]
    print(f"   Fallback: fetching quotes ({len(target_codes)} stocks, {max_workers} threads)...")

    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_fetch_one, code): code for code in target_codes}
        for future in tqdm(as_completed(futures), total=len(futures), desc="Fetching quotes"):
            result = future.result()
            if result is not None:
                results.append(result)

    return pd.DataFrame(results)


def get_financial_indicator(code: str) -> dict:
    """
    获取股票基本面财务指标（最新一期）
    :param code: 股票代码
    :return: dict，含 roe/资产负债率 等
    """
    try:
        df = ak.stock_financial_analysis_indicator(symbol=code, start_year="2023")
        if df.empty:
            return {}
        latest = df.iloc[0]
        
        result = {
            "roe": _safe_float(latest.get("净资产收益率(%)")),
            "debt_ratio": _safe_float(latest.get("资产负债率(%)")),
        }
        
        return result
    except Exception:
        return {}


def get_stock_realtime(code: str) -> dict:
    """
    获取单只股票实时行情
    :param code: 股票代码
    :return: dict，含 price/pct_change/pe/pb/market_cap/turnover_rate 等
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://quote.eastmoney.com",
            "Accept": "*/*",
        }
        secid = f"1.{code}" if code.startswith("6") else f"0.{code}"
        url = f"https://push2.eastmoney.com/api/qt/ulist.np/get?pn=1&pz=1&po=1&np=1&fltt=2&invt=2&fid=f3&fs=m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23&secids={secid}&fields=f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f13,f14,f15,f16,f17,f18,f20,f21,f23,f24,f25,f37,f38,f39,f40,f41,f45,f57,f62,f115,f128,f140,f141"
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("data") and data["data"].get("diff"):
                item = data["data"]["diff"][0]
                return {
                    "price": _safe_float(item.get("f2")),
                    "pct_change": _safe_float(item.get("f3")),
                    "change": _safe_float(item.get("f4")),
                    "pe": _safe_float(item.get("f9")),
                    "pb": _safe_float(item.get("f23")),
                    "market_cap": _safe_float(item.get("f20")),
                    "float_cap": _safe_float(item.get("f21")),
                    "turnover_rate": _safe_float(item.get("f8")),
                }
    except Exception as e:
        print(f"[WARN] 获取实时行情失败: {e}")
    return {}


def get_financial_detail(code: str) -> dict:
    """
    获取股票财务详情（每股收益、毛利率等）
    使用 EastMoney 财务分析接口
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
        }
        # 上海sh / 深圳sz
        market = "SH" if code.startswith("6") else "SZ"
        url = f"https://emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/PageAjax?code={market}{code}"
        resp = requests.get(url, headers=headers, timeout=15)
        
        if resp.status_code == 200:
            text = resp.text
            # 从HTML中提取JSON数据
            import re
            # 尝试找到 var 定义的财务数据
            patterns = [
                r'var\s+totalData\s*=\s*(\{[^;]+\})',
                r'"grossMarginRate"\s*:\s*([0-9.]+)',
                r'"basicEps"\s*:\s*([0-9.]+)',
                r'"roe"\s*:\s*([0-9.]+)',
            ]
            result = {}
            
            # 尝试解析页面中的财务数据
            if '"grossMarginRatio"' in text or '毛利率' in text:
                # 尝试匹配财务数据
                match = re.search(r'"grossMarginRatio"\s*:\s*([0-9.]+)', text)
                if match:
                    result["gross_margin"] = float(match.group(1)) * 100
                
                match = re.search(r'"basicEps"\s*:\s*([0-9.]+)', text)
                if match:
                    result["eps"] = float(match.group(1))
                
                match = re.search(r'"roe"\s*:\s*([0-9.]+)', text)
                if match:
                    result["roe"] = float(match.group(1))
            
            if result:
                return result
    except Exception as e:
        print(f"[WARN] 获取财务详情失败: {e}")
    return {}


def _safe_float(val) -> float:
    try:
        return float(val)
    except (TypeError, ValueError):
        return float("nan")

