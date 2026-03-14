#!/usr/bin/env python3
"""
test_sina_quotes.py - 测试新浪财经数据源
"""
import sys
from data_fetcher import get_realtime_quotes, get_realtime_quotes_from_sina, get_realtime_quotes_from_em

print('=' * 60)
print('新浪财经数据源测试')
print('=' * 60)

# 测试1：新浪财经
print('\n测试1: 新浪财经全市场行情')
print('-' * 60)
df_sina = get_realtime_quotes_from_sina()

if not df_sina.empty:
    print(f'✅ 成功获取 {len(df_sina)} 只股票')
    print(f'\n列名: {list(df_sina.columns)}')
    print(f'\n前5只股票:')
    for i, row in df_sina.head().iterrows():
        print(f'  {row["code"]} {row["name"]}: ¥{row.get("price", "N/A")} ({row.get("pct_change", "N/A")}%)')
    sina_success = True
else:
    print('❌ 新浪财经获取失败')
    sina_success = False

# 测试2：多源降级
print('\n\n测试2: 多源降级机制')
print('-' * 60)
test_codes = ['000001', '000002', '600000', '600519', '000858']
df_multi = get_realtime_quotes(test_codes)

if not df_multi.empty:
    print(f'✅ 成功获取 {len(df_multi)} 只股票')
    print(f'\n股票列表:')
    for i, row in df_multi.iterrows():
        print(f'  {row["code"]} {row["name"]}: ¥{row.get("price", "N/A")}')
    multi_success = True
else:
    print('❌ 多源降级也失败')
    multi_success = False

# 总结
print('\n\n' + '=' * 60)
print('测试总结')
print('=' * 60)
print(f'新浪财经: {"✅ 成功" if sina_success else "❌ 失败"}')
print(f'多源降级: {"✅ 成功" if multi_success else "❌ 失败"}')

if sina_success or multi_success:
    print('\n✅ 数据源可用，选股功能应该能正常工作')
    sys.exit(0)
else:
    print('\n❌ 所有数据源都失败，可能是非交易时间或网络问题')
    print('建议：在交易时间（周一至周五 9:30-15:00）重试')
    sys.exit(1)
