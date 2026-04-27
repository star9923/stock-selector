#!/usr/bin/env python3
"""
自动打包前端并推送到 GitHub
用法: python deploy.py [--skip-build]
"""
import os
import sys
import json
import subprocess
from datetime import datetime

def run_cmd(cmd, cwd=None):
    """执行命令"""
    print(f"\n> {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        return False
    print(result.stdout)
    return True

def main():
    print("=" * 60)
    print("  自动打包前端并推送到 GitHub")
    print("=" * 60)

    # 检查 stocks.json 是否存在
    json_path = "frontend/public/assets/stocks.json"
    if not os.path.exists(json_path):
        print(f"错误: {json_path} 不存在，请先运行 python main.py")
        sys.exit(1)

    # 读取时间戳
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        timestamp = data.get("timestamp", "unknown")
    print(f"数据时间: {timestamp}")

    # 检查是否跳过构建
    skip_build = "--skip-build" in sys.argv

    if not skip_build:
        # 检查 node/npm
        if not run_cmd("node --version"):
            print("错误: Node.js 未安装")
            sys.exit(1)

        # 安装依赖
        print("\n[1/3] 安装前端依赖...")
        if not run_cmd("cd frontend && npm install", cwd=os.path.dirname(os.path.abspath(__file__))):
            sys.exit(1)

        # 构建
        print("\n[2/3] 构建前端...")
        if not run_cmd("cd frontend && npm run build", cwd=os.path.dirname(os.path.abspath(__file__))):
            sys.exit(1)
    else:
        print("\n跳过构建步骤")

    # 推送
    print("\n[3/3] 推送 dist 到 GitHub...")
    
    # 添加 dist 到 git
    run_cmd("git add frontend/dist/")
    
    # 检查是否有changes
    result = subprocess.run("git diff --staged --name-only", shell=True, capture_output=True, text=True)
    if not result.stdout.strip():
        print("没有需要推送的内容")
        return

    # 提交
    commit_msg = f"docs: update stock data {timestamp}"
    run_cmd(f'git commit -m "{commit_msg}"')
    
    # 推送
    if not run_cmd("git push"):
        print("推送失败，尝试强制推送...")
        run_cmd("git push -f")

    print("\n" + "=" * 60)
    print("  推送完成!")
    print("=" * 60)

if __name__ == "__main__":
    main()