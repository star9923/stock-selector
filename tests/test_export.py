"""
测试导出功能
"""
from export_service import export_stock_selection, export_stock_analysis, get_export_files
from stock_analyzer import analyze_stock

# 测试数据
test_selection_data = [
    {
        "code": "600519",
        "name": "贵州茅台",
        "price": 1650.0,
        "pct_change": 2.5,
        "tech_score": 75.0,
        "fund_score": 80.0,
        "sentiment_score": 20.0,
        "total_score": 65.5,
        "board_name": "白酒"
    },
    {
        "code": "600036",
        "name": "招商银行",
        "price": 35.5,
        "pct_change": 1.2,
        "tech_score": 70.0,
        "fund_score": 75.0,
        "sentiment_score": 15.0,
        "total_score": 62.0,
        "board_name": "银行"
    }
]

print("=" * 60)
print("测试导出功能")
print("=" * 60)

# 1. 测试导出选股结果（Excel）
print("\n1. 测试导出选股结果（Excel）...")
try:
    filepath = export_stock_selection(test_selection_data, format='excel')
    print(f"   ✓ 导出成功: {filepath}")
except Exception as e:
    print(f"   ✗ 导出失败: {e}")

# 2. 测试导出选股结果（CSV）
print("\n2. 测试导出选股结果（CSV）...")
try:
    filepath = export_stock_selection(test_selection_data, format='csv')
    print(f"   ✓ 导出成功: {filepath}")
except Exception as e:
    print(f"   ✗ 导出失败: {e}")

# 3. 测试导出股票分析报告
print("\n3. 测试导出股票分析报告...")
try:
    analysis_data = analyze_stock("600519", enable_sentiment=True)
    if analysis_data.get("success"):
        filepath = export_stock_analysis(analysis_data, format='excel')
        print(f"   ✓ 导出成功: {filepath}")
    else:
        print(f"   ✗ 分析失败: {analysis_data.get('error')}")
except Exception as e:
    print(f"   ✗ 导出失败: {e}")

# 4. 查看导出文件列表
print("\n4. 查看导出文件列表...")
try:
    files = get_export_files()
    print(f"   共有 {len(files)} 个导出文件:")
    for file in files[:5]:  # 只显示前5个
        print(f"   - {file['filename']} ({file['size']} bytes, {file['created_at']})")
except Exception as e:
    print(f"   ✗ 获取失败: {e}")

print("\n" + "=" * 60)
print("测试完成！")
print("=" * 60)
