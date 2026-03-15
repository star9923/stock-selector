#!/usr/bin/env python3
"""
测试股吧信息功能
"""
from services.stock_analyzer import analyze_stock
from services.ai_analyzer import analyze_with_ai


def test_stock_with_guba(code: str):
    """测试带股吧信息的个股分析"""
    print(f"\n{'='*60}")
    print(f"分析股票: {code}")
    print('='*60)

    # 1. 基础分析
    result = analyze_stock(code, enable_sentiment=True)

    if not result["success"]:
        print(f"❌ 分析失败: {result['error']}")
        return

    # 2. 显示分析结果
    print(f"\n【{result['name']} ({result['code']})】")

    basic = result["basic_info"]
    print(f"\n价格: {basic['price']:.2f} 元 ({basic['pct_change']:+.2f}%)")

    tech = result["technical"]
    print(f"\n技术得分: {tech['score']['total']:.1f}/100")

    fund = result["fundamental"]
    print(f"基本面得分: {fund['score']['total']:.1f}/100")

    sentiment = result["sentiment"]
    print(f"\n市场情绪: {sentiment['score']}/80")
    print(f"  - 热度: {sentiment['hot_score']}/30")
    print(f"  - 板块: {sentiment['board_score']}/30")
    print(f"  - 股吧: {sentiment['guba_score']}/20")
    print(f"  - 板块: {sentiment['board_name']}")

    if "guba_info" in sentiment:
        guba = sentiment["guba_info"]
        print(f"\n股吧热度:")
        print(f"  关注指数: {guba['attention_index']:.1f}/100")
        print(f"  综合得分: {guba['comprehensive_score']:.1f}/100")
        print(f"  机构参与度: {guba['institution_participation']:.2f}%")
        print(f"  排名: 第 {guba['current_rank']} 名 ({'↑' if guba['rank_change'] > 0 else '↓'}{abs(guba['rank_change'])})")

    print(f"\n投资建议: {result['recommendation']}")

    # 3. AI 分析（可选）
    print(f"\n{'='*60}")
    print("AI 深度分析")
    print('='*60)
    ai_analysis = analyze_with_ai(result)
    print(ai_analysis)


if __name__ == "__main__":
    # 测试几只热门股票
    test_codes = ["600519", "000001", "600036"]

    for code in test_codes:
        try:
            test_stock_with_guba(code)
        except KeyboardInterrupt:
            print("\n\n用户中断")
            break
        except Exception as e:
            print(f"\n❌ 测试失败: {e}")
            import traceback
            traceback.print_exc()
