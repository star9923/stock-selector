"""
app.py - Flask Web 服务（单线程稳定版）
"""
from flask import Flask, render_template, jsonify, request, send_file
from flask_cors import CORS
from selector import run_selection
from stock_analyzer import analyze_stock
from sector_analyzer import analyze_sector, get_all_sectors, get_hot_sectors
from export_service import (
    export_stock_selection, export_stock_analysis, export_sector_analysis,
    get_export_files, delete_export_file, clean_old_exports
)
from data_fetcher import _STOCK_MAPPING
import pandas as pd
from datetime import datetime
import os

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


@app.route("/api/sectors", methods=["GET"])
def get_sectors():
    """获取所有板块列表"""
    try:
        sectors = get_all_sectors()
        return jsonify({"success": True, "data": sectors, "count": len(sectors)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/sectors/hot", methods=["GET"])
def get_hot_sectors_api():
    """获取热门板块"""
    try:
        top_n = int(request.args.get("top", 10))
        hot_sectors_df = get_hot_sectors(top_n)
        if hot_sectors_df.empty:
            return jsonify({"success": False, "message": "暂无热门板块数据"})

        data = hot_sectors_df.to_dict("records")
        return jsonify({"success": True, "data": data, "count": len(data)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/sectors/<sector_name>", methods=["GET"])
def analyze_sector_api(sector_name):
    """分析单个板块"""
    try:
        result = analyze_sector(sector_name)
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/export/selection", methods=["POST"])
def export_selection():
    """导出选股结果"""
    try:
        data = request.json.get("data", [])
        format = request.json.get("format", "excel")

        if not data:
            # 如果没有传数据，使用缓存的数据
            if cache["data"] is None:
                return jsonify({"success": False, "message": "没有可导出的数据"})
            data = cache["data"]

        filepath = export_stock_selection(data, format)
        filename = os.path.basename(filepath)

        return jsonify({
            "success": True,
            "filename": filename,
            "message": f"导出成功：{filename}"
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/export/analysis/<code>", methods=["GET"])
def export_analysis(code):
    """导出股票分析报告"""
    try:
        format = request.args.get("format", "excel")

        # 获取分析数据
        analysis_data = analyze_stock(code)
        if not analysis_data.get("success"):
            return jsonify({"success": False, "message": "股票分析失败"})

        filepath = export_stock_analysis(analysis_data, format)
        filename = os.path.basename(filepath)

        return jsonify({
            "success": True,
            "filename": filename,
            "message": f"导出成功：{filename}"
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/export/sector/<sector_name>", methods=["GET"])
def export_sector(sector_name):
    """导出板块分析"""
    try:
        format = request.args.get("format", "excel")

        # 获取板块分析数据
        sector_data = analyze_sector(sector_name)
        if not sector_data.get("success"):
            return jsonify({"success": False, "message": "板块分析失败"})

        filepath = export_sector_analysis(sector_data, format)
        filename = os.path.basename(filepath)

        return jsonify({
            "success": True,
            "filename": filename,
            "message": f"导出成功：{filename}"
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/export/files", methods=["GET"])
def list_export_files():
    """获取导出文件列表"""
    try:
        files = get_export_files()
        return jsonify({"success": True, "data": files, "count": len(files)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/export/download/<filename>", methods=["GET"])
def download_export_file(filename):
    """下载导出文件"""
    try:
        from export_service import EXPORT_DIR
        filepath = os.path.join(EXPORT_DIR, filename)

        if not os.path.exists(filepath):
            return jsonify({"success": False, "message": "文件不存在"})

        return send_file(
            filepath,
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/export/delete/<filename>", methods=["DELETE"])
def delete_export(filename):
    """删除导出文件"""
    try:
        success = delete_export_file(filename)
        if success:
            return jsonify({"success": True, "message": "删除成功"})
        else:
            return jsonify({"success": False, "message": "文件不存在"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


if __name__ == "__main__":
    # 启动时清理7天前的导出文件
    clean_old_exports(days=7)

    print("\n" + "="*60)
    print("  A股智能选股系统 v2.2 - Web 服务（单线程稳定版）")
    print("="*60)
    print("  访问地址: http://localhost:5001")
    print("  运行模式: 单线程稳定模式")
    print("  默认最低得分: 40 分（更容易选出股票）")
    print("  新功能: 板块分析 + 数据导出")
    print("="*60 + "\n")
    app.run(host="0.0.0.0", port=5001, debug=True)
