#!/usr/bin/env python3
"""
Offline checks for the fast selection path.

Run with:
    python tests/test_fast_selection_flow.py
"""
import importlib.util
import json
import os
import sys
import types
from datetime import datetime

import pandas as pd


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

for stream in (sys.stdout, sys.stderr):
    try:
        stream.reconfigure(encoding="utf-8")
    except Exception:
        pass


def install_common_shims():
    sys.modules["data.akshare_config"] = types.SimpleNamespace()
    sys.modules["tqdm"] = types.SimpleNamespace(tqdm=lambda iterable, **kwargs: iterable)


def test_em_batch_quotes():
    install_common_shims()

    cols = {
        "code": "\u4ee3\u7801",
        "name": "\u540d\u79f0",
        "price": "\u6700\u65b0\u4ef7",
        "pct": "\u6da8\u8dcc\u5e45",
        "volume": "\u6210\u4ea4\u91cf",
        "turnover": "\u6210\u4ea4\u989d",
        "turnover_rate": "\u6362\u624b\u7387",
        "pe": "\u5e02\u76c8\u7387-\u52a8\u6001",
        "pb": "\u5e02\u51c0\u7387",
        "market_cap": "\u603b\u5e02\u503c",
        "float_cap": "\u6d41\u901a\u5e02\u503c",
    }
    fake_ak = types.SimpleNamespace()
    fake_ak.stock_zh_a_spot_em = lambda: pd.DataFrame([
        {
            cols["code"]: 1,
            cols["name"]: "\u5e73\u5b89\u94f6\u884c",
            cols["price"]: "12.3",
            cols["pct"]: "-0.5",
            cols["volume"]: "234567",
            cols["turnover"]: "123456789",
            cols["turnover_rate"]: "1.2",
            cols["pe"]: "6.4",
            cols["pb"]: "0.7",
            cols["market_cap"]: "250000000000",
            cols["float_cap"]: "249000000000",
        }
    ])
    sys.modules["akshare"] = fake_ak

    sys.modules.pop("data.data_fetcher", None)
    from data.data_fetcher import get_realtime_quotes_from_em

    df = get_realtime_quotes_from_em(["000001"], max_workers=1)
    assert list(df["code"]) == ["000001"], df
    assert float(df.iloc[0]["pb"]) == 0.7
    assert {
        "code", "name", "price", "pct_change", "volume", "turnover",
        "turnover_rate", "pe", "pb", "market_cap", "float_cap",
    }.issubset(df.columns)


def test_history_cache_preference():
    install_common_shims()
    sys.modules["akshare"] = types.SimpleNamespace()
    sys.modules.pop("data.stock_data_fallback", None)

    import data.stock_data_fallback as stock_cache

    cache_root = os.path.join(os.getcwd(), ".cache", "stock_history")
    os.makedirs(cache_root, exist_ok=True)
    cache_file = os.path.join(cache_root, "TEST01.json")

    rows = []
    base = pd.Timestamp("2026-01-01")
    for i in range(70):
        rows.append({
            "date": (base + pd.Timedelta(days=i)).strftime("%Y-%m-%d"),
            "open": 1,
            "high": 2,
            "low": 1,
            "close": 1 + i,
            "volume": 100,
            "turnover": 1000,
        })

    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump({"timestamp": datetime.now().isoformat(), "code": "TEST01", "data": rows}, f)

    calls = {"n": 0}
    fake_fetcher = types.ModuleType("data.data_fetcher")

    def fake_daily(code, days):
        calls["n"] += 1
        return pd.DataFrame()

    fake_fetcher.get_daily_history = fake_daily
    sys.modules["data.data_fetcher"] = fake_fetcher

    try:
        cached = stock_cache.get_stock_history_with_fallback("TEST01", days=60, prefer_cache=True)
        assert calls["n"] == 0, calls
        assert len(cached) == 60, len(cached)
        assert int(cached.iloc[-1]["close"]) == 70

        missing = stock_cache.get_stock_history_with_fallback("MISSING", days=60, prefer_cache=False)
        assert calls["n"] == 1, calls
        assert missing.empty
    finally:
        if os.path.exists(cache_file):
            os.remove(cache_file)


def test_app_select_and_cache_meta():
    fake_request = types.SimpleNamespace(json={}, args={})

    class FakeFlask:
        def __init__(self, name):
            self.name = name

        def route(self, *args, **kwargs):
            def decorate(fn):
                return fn
            return decorate

        def run(self, *args, **kwargs):
            return None

    fake_flask = types.ModuleType("flask")
    fake_flask.Flask = FakeFlask
    fake_flask.render_template = lambda *args, **kwargs: {}
    fake_flask.jsonify = lambda obj=None, **kwargs: obj if obj is not None else kwargs
    fake_flask.request = fake_request
    fake_flask.send_file = lambda *args, **kwargs: {}
    sys.modules["flask"] = fake_flask
    sys.modules["flask_cors"] = types.SimpleNamespace(CORS=lambda app: None)
    sys.modules["dotenv"] = types.SimpleNamespace(load_dotenv=lambda: None)

    selector = types.ModuleType("core.selector")

    def fake_run_selection(**kwargs):
        assert kwargs["enable_sentiment"] is False
        assert kwargs["enable_financial"] is False
        assert kwargs["prefer_history_cache"] is True
        assert kwargs["max_workers"] == 8
        assert kwargs["volume_top_n"] == 200
        df = pd.DataFrame([{
            "code": "000001",
            "name": "\u5e73\u5b89\u94f6\u884c",
            "price": 12.3,
            "pct_change": 1.2,
            "pe": 6.4,
            "pb": 0.7,
            "market_cap": 1,
            "turnover_rate": 1.1,
            "tech_score": 70.0,
            "fund_score": 45.0,
            "sentiment_score": 0.0,
            "total_score": 62.5,
            "board_name": "-",
        }])
        df.attrs["analyzed_count"] = 200
        df.attrs["quote_count"] = 5300
        return df

    selector.run_selection = fake_run_selection
    sys.modules["core.selector"] = selector

    stock_analyzer = types.ModuleType("services.stock_analyzer")
    stock_analyzer.analyze_stock = lambda *args, **kwargs: {"success": True}
    sys.modules["services.stock_analyzer"] = stock_analyzer

    sector_analyzer = types.ModuleType("services.sector_analyzer")
    sector_analyzer.analyze_sector = lambda *args, **kwargs: {"success": True}
    sector_analyzer.get_all_sectors = lambda: []
    sector_analyzer.get_hot_sectors = lambda *args, **kwargs: pd.DataFrame()
    sys.modules["services.sector_analyzer"] = sector_analyzer

    export_service = types.ModuleType("services.export_service")
    for name in ["export_stock_selection", "export_stock_analysis", "export_sector_analysis"]:
        setattr(export_service, name, lambda *args, **kwargs: "dummy.xlsx")
    export_service.get_export_files = lambda: []
    export_service.delete_export_file = lambda filename: True
    export_service.clean_old_exports = lambda days=7: None
    sys.modules["services.export_service"] = export_service

    history_service = types.ModuleType("services.history_service")
    history_service.init_db = lambda: None
    history_service.save_snapshot = lambda *args, **kwargs: 1
    history_service.list_snapshots = lambda: []
    history_service.get_snapshot = lambda sid: None
    history_service.delete_snapshot = lambda sid: True
    services_pkg = types.ModuleType("services")
    services_pkg.history_service = history_service
    sys.modules["services"] = services_pkg
    sys.modules["services.history_service"] = history_service

    data_fetcher = types.ModuleType("data.data_fetcher")
    data_fetcher._STOCK_MAPPING = {"000001": "\u5e73\u5b89\u94f6\u884c"}
    data_fetcher.get_daily_history = lambda *args, **kwargs: pd.DataFrame()
    sys.modules["data.data_fetcher"] = data_fetcher

    spec = importlib.util.spec_from_file_location("app_under_test", "app.py")
    app_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(app_module)

    fake_request.json = {
        "top": 20,
        "min_score": 45,
        "tech_weight": 0.7,
        "fund_weight": 0.3,
        "sentiment_weight": 0,
        "quote_source": "auto",
        "volume_top_n": 200,
        "max_workers": 99,
        "enable_sentiment": False,
        "enable_financial": False,
        "prefer_history_cache": True,
    }

    selected = app_module.select_stocks()
    assert selected["success"] is True, selected
    assert selected["meta"]["max_workers"] == 8, selected["meta"]
    assert selected["meta"]["prefer_history_cache"] is True, selected["meta"]
    assert selected["meta"]["enable_financial"] is False, selected["meta"]
    assert selected["meta"]["quote_count"] == 5300, selected["meta"]
    assert selected["stats"]["avg_total"] == 62.5, selected["stats"]

    cached = app_module.get_cache()
    assert cached["success"] is True, cached
    assert cached["meta"] == selected["meta"], cached
    assert cached["stats"] == selected["stats"], cached


def main():
    test_em_batch_quotes()
    test_history_cache_preference()
    test_app_select_and_cache_meta()
    print("fast selection flow checks ok")


if __name__ == "__main__":
    main()
