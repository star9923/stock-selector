"""
main.py - 入口文件（单线程稳定版）
用法：python main.py [--mode fast|balanced|deep] [--top N] [--min-score S]
"""
import argparse
import pandas as pd
from datetime import datetime
from core.selector import run_selection


MODE_PRESETS = {
    "fast": {
        "min_score": 45.0,
        "tech_weight": 0.7,
        "fund_weight": 0.3,
        "sentiment_weight": 0.0,
        "volume_top_n": 200,
        "max_workers": 8,
        "enable_sentiment": False,
        "enable_financial": False,
        "prefer_history_cache": True,
    },
    "balanced": {
        "min_score": 45.0,
        "tech_weight": 0.5,
        "fund_weight": 0.3,
        "sentiment_weight": 0.2,
        "volume_top_n": 500,
        "max_workers": 8,
        "enable_sentiment": True,
        "enable_financial": True,
        "prefer_history_cache": False,
    },
    "deep": {
        "min_score": 40.0,
        "tech_weight": 0.45,
        "fund_weight": 0.3,
        "sentiment_weight": 0.25,
        "volume_top_n": 1000,
        "max_workers": 6,
        "enable_sentiment": True,
        "enable_financial": True,
        "prefer_history_cache": False,
    },
}


def main():
    parser = argparse.ArgumentParser(description="A股智能选股系统（单线程稳定版）")
    parser.add_argument("--mode", choices=MODE_PRESETS.keys(), default="fast", help="选股模式：fast/balanced/deep (默认fast)")
    parser.add_argument("--top", type=int, default=20, help="返回前N只股票 (默认20)")
    parser.add_argument("--min-score", type=float, default=None, help="最低综合得分，默认跟随模式")
    parser.add_argument("--tech-weight", type=float, default=None, help="技术面权重，默认跟随模式")
    parser.add_argument("--fund-weight", type=float, default=None, help="基本面权重，默认跟随模式")
    parser.add_argument("--sentiment-weight", type=float, default=None, help="情绪面权重，默认跟随模式")
    parser.add_argument("--quote-source", choices=["auto", "sina", "em", "xueqiu"], default="auto", help="行情数据源 (默认auto)")
    parser.add_argument("--volume-top-n", type=int, default=None, help="只分析成交量前N只股票，0表示不限，默认跟随模式")
    parser.add_argument("--max-workers", type=int, default=None, help="并发线程数，默认跟随模式，最高8")
    parser.add_argument("--enable-sentiment", action="store_true", help="强制开启情绪分析")
    parser.add_argument("--disable-sentiment", action="store_true", help="强制关闭情绪分析")
    parser.add_argument("--enable-financial", action="store_true", help="强制逐股拉取财报指标")
    parser.add_argument("--disable-financial", action="store_true", help="强制跳过逐股财报指标")
    parser.add_argument("--prefer-history-cache", action="store_true", help="强制优先使用1天内历史K线缓存")
    parser.add_argument("--no-history-cache", action="store_true", help="强制实时获取历史K线")
    args = parser.parse_args()

    config = MODE_PRESETS[args.mode].copy()
    for key in ("min_score", "tech_weight", "fund_weight", "sentiment_weight", "volume_top_n", "max_workers"):
        value = getattr(args, key)
        if value is not None:
            config[key] = value
    if args.enable_sentiment:
        config["enable_sentiment"] = True
    if args.disable_sentiment:
        config["enable_sentiment"] = False
    if args.enable_financial:
        config["enable_financial"] = True
    if args.disable_financial:
        config["enable_financial"] = False
    if args.prefer_history_cache:
        config["prefer_history_cache"] = True
    if args.no_history_cache:
        config["prefer_history_cache"] = False
    config["max_workers"] = min(int(config["max_workers"]), 8)

    print(f"\n{'='*60}")
    print(f"  A股智能选股系统 v2.1  |  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*60}")
    print(f"  模式: {args.mode}  |  数据源: {args.quote_source}  |  返回前 {args.top} 只")
    print(f"  技术/基本/情绪权重: {config['tech_weight']} / {config['fund_weight']} / {config['sentiment_weight']}")
    print(f"  最低得分: {config['min_score']}  |  成交量TopN: {config['volume_top_n']}  |  并发: {config['max_workers']}")
    print(f"  情绪分析: {'开启' if config['enable_sentiment'] else '关闭'}  |  财报指标: {'逐股拉取' if config['enable_financial'] else '跳过'}")
    print(f"  历史K线: {'优先缓存' if config['prefer_history_cache'] else '实时获取'}")
    print(f"{'='*60}\n")

    df = run_selection(
        top_n=args.top,
        tech_weight=config["tech_weight"],
        fund_weight=config["fund_weight"],
        sentiment_weight=config["sentiment_weight"],
        min_score=config["min_score"],
        max_workers=config["max_workers"],
        enable_sentiment=config["enable_sentiment"],
        enable_financial=config["enable_financial"],
        prefer_history_cache=config["prefer_history_cache"],
        quote_source=args.quote_source,
        volume_top_n=config["volume_top_n"],
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
