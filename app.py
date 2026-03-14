"""
app.py - Flask Web 服务（单线程稳定版）
"""
from dotenv import load_dotenv
load_dotenv()

from flask import Flask, render_template, jsonify, request, send_file
from flask_cors import CORS
from core.selector import run_selection
from services.stock_analyzer import analyze_stock
from services.sector_analyzer import analyze_sector, get_all_sectors, get_hot_sectors
from services.export_service import (
    export_stock_selection, export_stock_analysis, export_sector_analysis,
    get_export_files, delete_export_file, clean_old_exports
)
from data.data_fetcher import _STOCK_MAPPING
import pandas as pd
from datetime import datetime
import os
import json

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
    quote_source = params.get("quote_source", "auto")

    try:
        df = run_selection(
            top_n=top_n,
            tech_weight=tech_weight,
            fund_weight=fund_weight,
            sentiment_weight=sentiment_weight,
            min_score=min_score,
            max_workers=max_workers,
            enable_sentiment=enable_sentiment,
            quote_source=quote_source,
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
        hist_source = request.args.get("hist_source", "auto")
        result = analyze_stock(code, hist_source=hist_source)
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/ai-analyze/<code>", methods=["POST"])
def ai_analyze(code):
    """AI 智能分析"""
    try:
        from services.ai_analyzer import analyze_with_ai

        # 先获取股票数据
        hist_source = request.json.get("hist_source", "auto") if request.json else "auto"
        stock_data = analyze_stock(code, hist_source=hist_source)

        if not stock_data.get("success"):
            return jsonify({"success": False, "error": stock_data.get("error", "获取股票数据失败")})

        # 调用 AI 分析
        ai_result = analyze_with_ai(stock_data)

        return jsonify({
            "success": True,
            "analysis": ai_result,
        })
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


# ========== 缓存管理 API ==========

CACHE_DIR = os.path.join(os.path.dirname(__file__), '.cache')
SETTINGS_FILE = os.path.join(os.path.dirname(__file__), '.cache', 'settings.json')


def load_settings() -> dict:
    """加载系统设置"""
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {"data_source": "ths"}  # 默认使用同花顺


def save_settings(settings: dict):
    """保存系统设置"""
    os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
    with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)


@app.route("/api/settings/data-source", methods=["GET"])
def get_data_source():
    """获取数据源设置"""
    try:
        settings = load_settings()
        return jsonify({
            "success": True,
            "data": {"source": settings.get("data_source", "ths")}
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/settings/data-source", methods=["POST"])
def set_data_source():
    """设置数据源"""
    try:
        source = request.json.get("source", "ths")
        if source not in ["ths", "em"]:
            return jsonify({"success": False, "message": "无效的数据源"})

        settings = load_settings()
        settings["data_source"] = source
        save_settings(settings)

        source_name = "同花顺" if source == "ths" else "东方财富"
        return jsonify({
            "success": True,
            "message": f"数据源已设置为: {source_name}"
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})


@app.route("/api/settings/ai", methods=["GET"])
def get_ai_config():
    """获取 AI 配置（隐藏 API Key）"""
    try:
        from services.ai_analyzer import load_ai_config
        config = load_ai_config()
        # 隐藏 API Key，只显示前8位和后4位
        api_key = config.get("api_key", "")
        if len(api_key) > 12:
            masked_key = api_key[:8] + "****" + api_key[-4:]
        elif api_key:
            masked_key = "****"
        else:
            masked_key = ""

        return jsonify({
            "success": True,
            "data": {
                "api_key_masked": masked_key,
                "has_key": bool(api_key),
                "base_url": config.get("base_url", ""),
                "model": config.get("model", "claude-sonnet-4-20250514"),
                "max_tokens": config.get("max_tokens", 2000),
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/settings/ai", methods=["POST"])
def set_ai_config():
    """保存 AI 配置"""
    try:
        from services.ai_analyzer import load_ai_config, save_ai_config
        data = request.json or {}

        config = load_ai_config()

        # 只更新提供的字段
        if "api_key" in data and data["api_key"]:
            config["api_key"] = data["api_key"]
        if "base_url" in data:
            config["base_url"] = data["base_url"] or "https://api.anthropic.com"
        if "model" in data and data["model"]:
            config["model"] = data["model"]
        if "max_tokens" in data:
            config["max_tokens"] = int(data["max_tokens"]) if data["max_tokens"] else 2000

        save_ai_config(config)
        return jsonify({"success": True, "message": "AI 配置已保存"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})


@app.route("/api/settings/ai/test", methods=["POST"])
def test_ai_config():
    """测试 AI 连接"""
    try:
        from services.ai_analyzer import get_client, load_ai_config
        config = load_ai_config()

        if not config.get("api_key"):
            return jsonify({"success": False, "message": "请先配置 API Key"})

        client = get_client()
        response = client.messages.create(
            model=config.get("model", "claude-sonnet-4-20250514"),
            max_tokens=50,
            messages=[{"role": "user", "content": "回复OK两个字"}],
        )
        reply = response.content[0].text
        return jsonify({"success": True, "message": f"连接成功: {reply[:20]}"})
    except Exception as e:
        return jsonify({"success": False, "message": f"连接失败: {str(e)[:80]}"})


@app.route("/api/cache/info", methods=["GET"])
def cache_info():
    """获取缓存信息"""
    try:
        total_size = 0
        total_files = 0
        last_update = None

        for root, dirs, files in os.walk(CACHE_DIR):
            for f in files:
                filepath = os.path.join(root, f)
                size = os.path.getsize(filepath)
                mtime = os.path.getmtime(filepath)
                total_size += size
                total_files += 1
                if last_update is None or mtime > last_update:
                    last_update = mtime

        # 格式化大小
        if total_size < 1024:
            size_str = f"{total_size} B"
        elif total_size < 1024 * 1024:
            size_str = f"{total_size / 1024:.1f} KB"
        else:
            size_str = f"{total_size / (1024 * 1024):.2f} MB"

        last_update_str = ""
        if last_update:
            last_update_str = datetime.fromtimestamp(last_update).strftime("%Y-%m-%d %H:%M:%S")

        return jsonify({
            "success": True,
            "data": {
                "total_size": size_str,
                "total_files": total_files,
                "last_update": last_update_str,
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/cache/clear", methods=["POST"])
def clear_cache():
    """清理缓存"""
    try:
        cache_type = request.args.get("type", "all")
        removed = 0

        if cache_type in ("all", "board"):
            # 清理板块情绪缓存
            for name in ("get_board_sentiment.json", "board_sentiment_fallback.json"):
                path = os.path.join(CACHE_DIR, name)
                if os.path.exists(path):
                    os.remove(path)
                    removed += 1

        if cache_type in ("all", "sector"):
            # 清理板块成分股缓存
            sector_dir = os.path.join(CACHE_DIR, "sector_stocks")
            if os.path.isdir(sector_dir):
                for f in os.listdir(sector_dir):
                    os.remove(os.path.join(sector_dir, f))
                    removed += 1

        if cache_type in ("all", "stock"):
            # 清理个股历史数据缓存
            stock_dir = os.path.join(CACHE_DIR, "stock_history")
            if os.path.isdir(stock_dir):
                for f in os.listdir(stock_dir):
                    os.remove(os.path.join(stock_dir, f))
                    removed += 1

        if cache_type == "all":
            # 清理其他缓存
            for f in os.listdir(CACHE_DIR):
                path = os.path.join(CACHE_DIR, f)
                if os.path.isfile(path):
                    os.remove(path)
                    removed += 1

        labels = {"all": "所有缓存", "board": "板块缓存", "sector": "成分股缓存", "stock": "个股缓存"}
        return jsonify({
            "success": True,
            "message": f"已清理{labels.get(cache_type, '缓存')}，共删除 {removed} 个文件"
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})


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
