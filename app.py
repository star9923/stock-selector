"""
app.py - Flask Web 服务（单线程稳定版）
"""
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from selector import run_selection
from stock_analyzer import analyze_stock
from data_fetcher import _STOCK_MAPPING
import pandas as pd
from datetime import datetime

app = Flask(__name__)
CORS(app)

# 缓存最近一次选股结果
cache = {"data": None, "timestamp": None, "params": None}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/select", methods=["POST"])
def select_stocks():
    """执行选股"""
    params = request.json or {}
    top_n = params.get("top", 20)
    min_score = params.get("min_score", 40.0)
    tech_weight = params.get("tech_weight", 0.5)
    fund_weight = params.get("fund_weight", 0.3)
    sentiment_weight = params.get("sentiment_weight", 0.2)
    max_workers = min(int(params.get("max_workers", 8)), 16)
    enable_sentiment = params.get("enable_sentiment", True)

    try:
        df = run_selection(
            top_n=top_n,
            tech_weight=tech_weight,
            fund_weight=fund_weight,
            sentiment_weight=sentiment_weight,
            min_score=min_score,
            max_workers=max_workers,
            enable_sentiment=enable_sentiment,
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
    print("  A股智能选股系统 v2.1 - Web 服务（单线程稳定版）")
    print("="*60)
    print("  访问地址: http://localhost:5001")
    print("  运行模式: 单线程稳定模式")
    print("  默认最低得分: 40 分（更容易选出股票）")
    print("="*60 + "\n")
    app.run(host="0.0.0.0", port=5001, debug=True)
