"""
app.py - Flask Web 服务（单线程稳定版）
"""
import json
import os
import subprocess
from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_cors import CORS
from selector import run_selection, set_stop_flag
from stock_analyzer import analyze_stock
from data_fetcher import _STOCK_MAPPING
import pandas as pd
from datetime import datetime

CONFIG_FILE = "config.json"
DATA_DIR = os.path.join(os.path.dirname(__file__), "frontend", "public", "assets")
STOCKS_JSON = os.path.join(DATA_DIR, "stocks.json")


def load_config():
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


app = Flask(__name__)
CORS(app)

# 加载配置
config = load_config()

# 缓存最近一次选股结果
cache = {"data": None, "timestamp": None, "params": None}
stop_selection_flag = False
selection_running = False
selection_thread = None
selection_result_holder = {"result": None, "error": None, "done": False}


def save_stocks_json(data, timestamp):
    """保存选股结果到 JSON 文件"""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(STOCKS_JSON, "w", encoding="utf-8") as f:
        json.dump({"data": data, "timestamp": timestamp}, f, ensure_ascii=False, indent=2)


def save_stocks_csv(data):
    """保存选股结果到 CSV 文件"""
    if not data:
        return
    project_dir = os.path.dirname(__file__)
    
    # 删除旧的 CSV 文件
    for f in os.listdir(project_dir):
        if f.startswith("result_") and f.endswith(".csv"):
            try:
                os.remove(os.path.join(project_dir, f))
            except:
                pass
    
    # 生成新 CSV 文件
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    csv_path = os.path.join(project_dir, f"result_{timestamp}.csv")
    df = pd.DataFrame(data)
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"[INFO] CSV 文件已保存: {csv_path}")


import time
import subprocess


def auto_build_and_deploy():
    """自动构建前端并推送到 GitHub"""
    project_root = os.path.dirname(os.path.abspath(__file__))
    frontend_dir = os.path.join(project_root, "frontend")
    dist_dir = os.path.join(frontend_dir, "dist")
    print(f"[INFO] 开始自动部署")
    try:
        # 尝试直接构建，如果失败再安装依赖
        print("[INFO] 尝试直接构建前端...")
        result = subprocess.run("npm run build", shell=True, capture_output=True, cwd=frontend_dir, timeout=300)
        if result.returncode != 0:
            print("[INFO] 构建失败，尝试安装依赖...")
            subprocess.run("npm install", shell=True, check=True, capture_output=True, cwd=frontend_dir)
            result = subprocess.run("npm run build", shell=True, check=True, capture_output=True, cwd=frontend_dir)
        print("[INFO] 前端构建完成")

        # 检查 dist 目录是否存在
        if not os.path.exists(dist_dir):
            print(f"[ERROR] dist 目录不存在: {dist_dir}")
            return False

        # 强制添加 dist（忽略 .gitignore）
        subprocess.run(f"git add -f {dist_dir}", shell=True, check=True, capture_output=True)
        
        # 也添加 stocks.json
        stocks_json = os.path.join(project_root, "frontend", "public", "assets", "stocks.json")
        if os.path.exists(stocks_json):
            subprocess.run(f'git add -f "{stocks_json}"', shell=True, check=True, capture_output=True)
        
        # 检查是否有变化
        result = subprocess.run("git diff --staged --name-only", shell=True, capture_output=True, text=True, cwd=project_root)
        if not result.stdout.strip():
            print("[INFO] 没有需要推送的内容")
            return True
            
        # 配置 git（如果未配置）
        try:
            subprocess.run("git config user.email", shell=True, capture_output=True, cwd=project_root)
        except:
            subprocess.run('git config --global user.email "ci@local"', shell=True, capture_output=True)
            subprocess.run('git config --global user.name "CI"', shell=True, capture_output=True)
        
        # 提交并推送到 main 分支（由 GitHub Actions 自动部署到 gh-pages）
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        subprocess.run(f'git commit -m "docs: update stock data {timestamp}"', shell=True, check=True, capture_output=True, cwd=project_root)
        print("[INFO] 提交完成，推送到 main 分支...")
        
        # 推送到 main 分支（带重试）
        success = False
        for i in range(3):
            try:
                result = subprocess.run("git push origin main", shell=True, capture_output=True, text=True, cwd=project_root, timeout=60)
                if result.returncode == 0:
                    success = True
                    break
                print(f"[RETRY] 推送失败，尝试 {i+1}/3: {result.stderr}")
            except subprocess.TimeoutExpired:
                print(f"[RETRY] 推送超时，尝试 {i+1}/3")
            time.sleep(10)
        
        if not success:
            print("[ERROR] 推送失败，请检查网络或手动推送")
            return False
            
        print("[INFO] 自动部署完成，GitHub Actions 将自动部署到 gh-pages")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] 自动部署失败: {e}")
        print(f"stdout: {e.stdout}")
        print(f"stderr: {e.stderr}")
        return False
    except Exception as e:
        print(f"[ERROR] 自动部署异常: {e}")
        return False


import threading

def auto_build_and_deploy_async():
    """异步执行自动部署"""
    thread = threading.Thread(target=auto_build_and_deploy, daemon=True)
    thread.start()


def run_selection_threaded(top_n, tech_weight, fund_weight, min_score, max_workers):
    """在线程中执行选股"""
    global selection_running, stop_selection_flag, selection_result_holder
    selection_result_holder = {"result": None, "error": None, "done": False}
    
    try:
        df = run_selection(
            top_n=top_n,
            tech_weight=tech_weight,
            fund_weight=fund_weight,
            min_score=min_score,
            max_workers=max_workers,
        )
        selection_result_holder["result"] = df
    except Exception as e:
        selection_result_holder["error"] = str(e)
    finally:
        selection_result_holder["done"] = True
        selection_running = False


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/select", methods=["POST"])
def select_stocks():
    """执行选股"""
    global selection_running
    global selection_thread
    if selection_running:
        return jsonify({"success": False, "message": "选股任务正在进行中，请勿重复提交"})
    
    stop_selection_flag = False
    selection_running = True
    params = request.json or {}
    top_n = params.get("top", config.get("top", 20))
    min_score = params.get("min_score", config.get("min_score", 20))
    tech_weight = params.get("tech_weight", config.get("tech_weight", 0.6))
    fund_weight = params.get("fund_weight", config.get("fund_weight", 0.4))
    max_workers = min(int(params.get("max_workers", 8)), 16)

    selection_thread = threading.Thread(
        target=run_selection_threaded,
        args=(top_n, tech_weight, fund_weight, min_score, max_workers)
    )
    selection_thread.start()

    return jsonify({"success": True, "message": "选股已开始", "running": True})


@app.route("/api/result", methods=["GET"])
def get_result():
    """获取选股结果（轮询）"""
    global selection_running, selection_result_holder
    
    if selection_running and not selection_result_holder["done"]:
        return jsonify({"success": True, "running": True, "done": False})
    
    selection_running = False
    
    if selection_result_holder["error"]:
        return jsonify({"success": False, "message": selection_result_holder["error"]})
    
    df = selection_result_holder["result"]
    if df is None or df.empty:
        return jsonify({"success": False, "message": "未找到符合条件的股票，尝试降低最低得分"})

    cache["data"] = df.to_dict(orient="records")
    cache["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    save_stocks_json(cache["data"], cache["timestamp"])
    save_stocks_csv(cache["data"])
    auto_build_and_deploy_async()

    stats = {
        "avg_tech": round(df["tech_score"].mean(), 1),
        "avg_fund": round(df["fund_score"].mean(), 1),
        "avg_total": round(df["total_score"].mean(), 1),
        "avg_pe": round(df["pe"].mean(), 1),
        "avg_pb": round(df["pb"].mean(), 2),
    }

    return jsonify({
        "success": True,
        "running": False,
        "done": True,
        "data": cache["data"],
        "timestamp": cache["timestamp"],
        "count": len(df),
        "stats": stats,
    })


@app.route("/api/stop", methods=["POST"])
def stop_selection():
    """停止选股"""
    global stop_selection_flag, selection_running
    stop_selection_flag = True
    set_stop_flag()
    selection_running = False
    return jsonify({"success": True, "message": "选股已停止", "running": False})


@app.route("/api/status", methods=["GET"])
def get_status():
    """获取选股状态"""
    return jsonify({
        "success": True,
        "running": selection_running,
        "stopped": stop_selection_flag
    })


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


@app.route("/data/<path:filename>")
def serve_data(filename):
    """提供前端静态数据文件"""
    return send_from_directory(DATA_DIR, filename)


if __name__ == "__main__":
    print("\n" + "="*60)
    print("  A股智能选股系统 v2.1 - Web 服务")
    print("="*60)
    print(f"  访问地址: http://localhost:5001")
    print(f"  默认配置: top={config.get('top')}, min_score={config.get('min_score')}")
    print(f"  权重: tech={config.get('tech_weight')}, fund={config.get('fund_weight')}")
    print("="*60 + "\n")
    app.run(host="0.0.0.0", port=5001, debug=True)
