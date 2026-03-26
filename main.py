"""
main.py - 入口文件（单线程稳定版）
用法：python main.py [--top N] [--min-score S]
"""
import argparse
import pandas as pd
from datetime import datetime
from core.selector import run_selection


def main():
    parser = argparse.ArgumentParser(description="A股智能选股系统（单线程稳定版）")
    parser.add_argument("--top",        type=int,   default=20,   help="返回前N只股票 (默认20)")
    parser.add_argument("--min-score",  type=float, default=40.0, help="最低综合得分 (默认40)")
    parser.add_argument("--tech-weight", type=float, default=0.6, help="技术面权重 (默认0.6)")
    parser.add_argument("--fund-weight", type=float, default=0.4, help="基本面权重 (默认0.4)")
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"  A股智能选股系统 v2.1  |  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*60}")
    print(f"  技术面权重: {args.tech_weight}  |  基本面权重: {args.fund_weight}")
    print(f"  最低得分: {args.min_score}  |  返回前 {args.top} 只")
    print(f"  运行模式: 单线程稳定模式")
    print(f"{'='*60}\n")

    df = run_selection(
        top_n=args.top,
        tech_weight=args.tech_weight,
        fund_weight=args.fund_weight,
        min_score=args.min_score,
    )

    if df.empty:
        print("未找到符合条件的股票。尝试降低 --min-score 参数。")
        return

    # 格式化输出
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 150)
    pd.set_option("display.float_format", "{:.2f}".format)

    print(f"\n📈 选股结果（共 {len(df)} 只）\n")
    
    # 主要指标
    print("=" * 150)
    print(df[[
        "code", "name", "price", "pct_change",
        "pe", "pb", "turnover_rate",
        "tech_score", "fund_score", "total_score"
    ]].to_string())
    
    # 详细得分
    print(f"\n\n📊 详细得分分析\n")
    print("=" * 150)
    print(df[[
        "code", "name",
        "tech_trend", "tech_momentum", "tech_volume",
        "fund_valuation", "fund_profit", "fund_growth"
    ]].to_string())

    # 保存结果
    out_file = f"result_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    df.to_csv(out_file, index=True, encoding="utf-8-sig")
    print(f"\n✅ 结果已保存至 {out_file}")
    
    # 统计信息
    print(f"\n📊 统计信息")
    print(f"   平均技术面得分: {df['tech_score'].mean():.1f}")
    print(f"   平均基本面得分: {df['fund_score'].mean():.1f}")
    print(f"   平均综合得分:   {df['total_score'].mean():.1f}")
    print(f"   平均 PE:        {df['pe'].mean():.1f}")
    print(f"   平均 PB:        {df['pb'].mean():.2f}")


if __name__ == "__main__":
    main()
