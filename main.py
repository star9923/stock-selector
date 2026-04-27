"""
main.py - 入口文件（单线程稳定版）
用法：python main.py [--top N] [--min-score S]
配置文件: config.json
"""
import argparse
import json
import os
import pandas as pd
import traceback
import sys
from datetime import datetime
from selector import run_selection

CONFIG_FILE = "config.json"


def load_config():
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    config = load_config()
    
    parser = argparse.ArgumentParser(description="Stock Selector")
    parser.add_argument("--top", type=int, default=config.get("top", 20), help="Top N stocks")
    parser.add_argument("--min-score", type=float, default=config.get("min_score", 0), help="Min score")
    parser.add_argument("--tech-weight", type=float, default=config.get("tech_weight", 0.6), help="Tech weight")
    parser.add_argument("--fund-weight", type=float, default=config.get("fund_weight", 0.4), help="Fund weight")
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"  Stock Selector v2.1  |  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*60}")
    print(f"  Tech weight: {args.tech_weight}  |  Fund weight: {args.fund_weight}")
    print(f"  Min score: {args.min_score}  |  Top {args.top} stocks")
    
    try:
        df = run_selection(
            top_n=args.top,
            tech_weight=args.tech_weight,
            fund_weight=args.fund_weight,
            min_score=args.min_score,
        )
    except Exception as e:
        print(f"[ERROR] {e}")
        traceback.print_exc()
        df = pd.DataFrame()

    if df.empty:
        print("No stocks found. Try lowering --min-score.")
        sys.exit(1)

    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 150)
    pd.set_option("display.float_format", "{:.2f}".format)

    print(f"\n=== Results ({len(df)} stocks) ===\n")
    
    print("=" * 150)
    print(df[[
        "code", "name", "price", "pct_change",
        "pe", "pb", "turnover_rate",
        "tech_score", "fund_score", "total_score"
    ]].to_string())
    
    print(f"\n=== Score Details ===\n")
    print("=" * 150)
    print(df[[
        "code", "name",
        "tech_trend", "tech_momentum", "tech_volume",
        "fund_valuation", "fund_profit", "fund_growth"
    ]].to_string())

    out_file = f"result_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    
    # Delete old result files
    import glob
    import os
    for f in glob.glob("result_*.csv"):
        try:
            os.remove(f)
        except:
            pass
    
    df.to_csv(out_file, index=True, encoding="utf-8-sig")
    print(f"\nResult saved to {out_file}")
    
    print(f"\n=== Statistics ===")
    print(f"   Avg tech score: {df['tech_score'].mean():.1f}")
    print(f"   Avg fund score: {df['fund_score'].mean():.1f}")
    print(f"   Avg total score: {df['total_score'].mean():.1f}")
    print(f"   Avg PE: {df['pe'].mean():.1f}")
    print(f"   Avg PB: {df['pb'].mean():.2f}")


if __name__ == "__main__":
    main()
