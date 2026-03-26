"""
本地运行脚本 - 读取配置，按间隔执行并自动推送到 Git
用法：python run_local.py [--once]
       --once 只运行一次，不循环
"""
import json
import os
import sys
import time
import subprocess
from datetime import datetime

CONFIG_FILE = "config.json"


def load_config():
    default_config = {
        "top": 20,
        "min_score": 0,
        "tech_weight": 0.6,
        "fund_weight": 0.4,
        "interval_minutes": 60,
        "github": {"auto_commit": True, "commit_message": "Auto update stock selection results"}
    }
    if not os.path.exists(CONFIG_FILE):
        return default_config
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        cfg = json.load(f)
        # 合并默认配置，确保所有键都存在
        for key, value in default_config.items():
            if key not in cfg:
                cfg[key] = value
        if "github" not in cfg:
            cfg["github"] = default_config["github"]
        return cfg


def run_selection(cfg):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    cmd = [
        "python", "main.py",
        "--top", str(cfg.get("top", 20)),
        "--min-score", str(cfg.get("min_score", 0)),
        "--tech-weight", str(cfg.get("tech_weight", 0.6)),
        "--fund-weight", str(cfg.get("fund_weight", 0.4)),
    ]
    print(f"\n{'='*60}")
    print(f"  Executing stock selection  |  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    result = subprocess.run(cmd, capture_output=True, text=True, env=env, encoding="utf-8", errors="replace", cwd=script_dir)
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    print("Return code:", result.returncode)
    return result.returncode == 0


def generate_html():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    result = subprocess.run(
        ["python", "generate_html.py"], 
        capture_output=True, text=True, env=env, encoding="utf-8", errors="replace",
        cwd=script_dir
    )
    print(result.stdout)
    if result.stderr:
        print(result.stderr)
    return result.returncode == 0


def git_push(cfg):
    if not cfg.get("github", {}).get("auto_commit", True):
        return
    msg = cfg.get("github", {}).get("commit_message", "Auto update stock selection results")
    try:
        html_file = "index.html"
        
        if os.path.exists(html_file):
            subprocess.run(["git", "add", html_file], check=False)
            
        status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
        if status.stdout.strip():
            subprocess.run(["git", "commit", "-m", f"{msg} {datetime.now().strftime('%Y-%m-%d %H:%M')}"], check=False)
            
            # Retry push up to 5 times
            for attempt in range(5):
                result = subprocess.run(["git", "push"], capture_output=True, text=True)
                if result.returncode == 0:
                    print("Pushed to GitHub")
                    break
                print(f"Push failed, retrying ({attempt + 1}/5)...")
                time.sleep(5)
            else:
                print("Push failed after 5 attempts")
        else:
            print("No changes to push")
    except Exception as e:
        print(f"Git error: {e}")


UPDATE_TIMES = ["09:40", "11:30", "14:55"]


def should_run():
    """检查当前时间是否在更新列表中"""
    now = datetime.now()
    current_time = now.strftime("%H:%M")
    return current_time in UPDATE_TIMES


def wait_until_next_run():
    """等待到下一个更新时间"""
    now = datetime.now()
    current_time = now.strftime("%H:%M")
    
    if current_time in UPDATE_TIMES:
        return 60
    
    for target_time in UPDATE_TIMES:
        target_hour, target_minute = map(int, target_time.split(":"))
        target = now.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
        if target > now:
            wait_seconds = (target - now).total_seconds()
            return wait_seconds
    
    next_day = now.replace(hour=9, minute=30, second=0, microsecond=0)
    if now.hour >= 14 or (now.hour == 14 and now.minute >= 55):
        from datetime import timedelta
        next_day += timedelta(days=1)
    wait_seconds = (next_day - now).total_seconds()
    return wait_seconds


def main():
    cfg = load_config()
    
    print(f"Config loaded")
    print(f"   Update times: {', '.join(UPDATE_TIMES)}")
    print(f"   Auto push: {cfg.get('github', {}).get('auto_commit', True)}")
    print(f"   Press Ctrl+C to stop\n")

    # 立即执行一次
    success = run_selection(cfg)
    if success:
        generate_html()
        git_push(cfg)
    else:
        print("No stocks selected, skipping update")
    
    # 等待下一个时间点
    while True:
        wait_seconds = wait_until_next_run()
        print(f"Next update in {int(wait_seconds//3600)}h {int((wait_seconds%3600)//60)}m...")
        time.sleep(wait_seconds)
        
        if should_run():
            success = run_selection(cfg)
            if success:
                generate_html()
                git_push(cfg)
            else:
                print("No stocks selected, skipping update")
            
            time.sleep(120)


if __name__ == "__main__":
    main()
