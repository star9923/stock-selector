"""
app.py - Flask Web 服务（单线程稳定版）
"""
import json
import os
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from selector import run_selection
from stock_analyzer import analyze_stock
from data_fetcher import _STOCK_MAPPING
import pandas as pd
from datetime import datetime

CONFIG_FILE = "config.json"


def load_config():
    default_config = {
        "top": 20,
        "min_score": 20,
        "tech_weight": 0.6,
        "fund_weight": 0.4,
    }
    if not os.path.exists(CONFIG_FILE):
        return default_config
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        cfg = json.load(f)
        for key, value in default_config.items():
            if key not in cfg:
                cfg[key] = value
        return cfg


app = Flask(__name__)
CORS(app)

# 加载配置
config = load_config()

# 缓存最近一次选股结果
cache = {"data": None, "timestamp": None, "params": None}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/select", methods=["POST"])
def select_stocks():
    """执行选股"""
    params = request.json or {}
    top_n = params.get("top", config.get("top", 20))
    min_score = params.get("min_score", config.get("min_score", 20))
    tech_weight = params.get("tech_weight", config.get("tech_weight", 0.6))
    fund_weight = params.get("fund_weight", config.get("fund_weight", 0.4))
    max_workers = min(int(params.get("max_workers", 8)), 16)

    try:
        df = run_selection(
            top_n=top_n,
            tech_weight=tech_weight,
            fund_weight=fund_weight,
            min_score=min_score,
            max_workers=max_workers,
        )

        if df.empty:
            return jsonify({"success": False, "message": "未找到符合条件的股票，尝试降低最低得分"})

        # 更新缓存
        cache["data"] = df.to_dict(orient="records")
        cache["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cache["params"] = params

        # 统计信息
        stats = {
            "avg_tech": round(df["tech_score"].mean(), 1),
            "avg_fund": round(df["fund_score"].mean(), 1),
            "avg_total": round(df["total_score"].mean(), 1),
            "avg_pe": round(df["pe"].mean(), 1),
            "avg_pb": round(df["pb"].mean(), 2),
        }

        return jsonify({
            "success": True,
            "data": cache["data"],
            "timestamp": cache["timestamp"],
            "count": len(df),
            "stats": stats,
        })

    except Exception as e:
        return jsonify({"success": False, "message": f"错误: {str(e)}"})


@app.route("/api/cache", methods=["GET"])
def get_cache():
    """获取缓存的选股结果"""
    if cache["data"] is None:
        return jsonify({"success": False, "message": "暂无数据，请先执行选股"})

    return jsonify({
        "success": True,
        "data": cache["data"],
        "timestamp": cache["timestamp"],
        "count": len(cache["data"]),
    })


@app.route("/api/analyze/<code>", methods=["GET"])
def analyze(code):
    """分析单只股票"""
    try:
        result = analyze_stock(code)
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/search", methods=["GET"])
def search_stock():
    """搜索股票"""
    keyword = request.args.get("q", "").strip()
    if not keyword:
        return jsonify({"success": False, "message": "请输入搜索关键词"})

    results = []
    for code, name in _STOCK_MAPPING.items():
        if keyword in code or keyword in name:
            results.append({"code": code, "name": name})
            if len(results) >= 20:  # 限制返回数量
                break

    return jsonify({"success": True, "data": results, "count": len(results)})


if __name__ == "__main__":
    print("\n" + "="*60)
    print("  A股智能选股系统 v2.1 - Web 服务")
    print("="*60)
    print(f"  访问地址: http://localhost:5001")
    print(f"  默认配置: top={config.get('top')}, min_score={config.get('min_score')}")
    print(f"  权重: tech={config.get('tech_weight')}, fund={config.get('fund_weight')}")
    print("="*60 + "\n")
    app.run(host="0.0.0.0", port=5001, debug=True)
