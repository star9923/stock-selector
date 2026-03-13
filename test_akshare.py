"""测试 AkShare 数据获取"""
import akshare as ak
import os

# 清除所有代理设置
for key in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY', 'all_proxy', 'ALL_PROXY']:
    if key in os.environ:
        del os.environ[key]

print("测试 AkShare 数据获取...\n")

# 测试1: 获取股票列表
print("1. 测试获取股票列表...")
try:
    df = ak.stock_info_a_code_name()
    print(f"   ✓ 成功获取 {len(df)} 只股票")
    print(f"   列名: {df.columns.tolist()}")
    print(f"   前3行:\n{df.head(3)}\n")
except Exception as e:
    print(f"   ✗ 失败: {e}\n")

# 测试2: 获取实时行情
print("2. 测试获取实时行情...")
try:
    df = ak.stock_zh_a_spot_em()
    print(f"   ✓ 成功获取 {len(df)} 条行情")
    print(f"   列名: {df.columns.tolist()}")
    print(f"   前3行:\n{df.head(3)}\n")
except Exception as e:
    print(f"   ✗ 失败: {e}\n")

# 测试3: 获取单只股票历史数据
print("3. 测试获取历史数据（平安银行 000001）...")
try:
    df = ak.stock_zh_a_hist(symbol="000001", period="daily", start_date="20240101", end_date="20240131", adjust="qfq")
    print(f"   ✓ 成功获取 {len(df)} 条数据")
    print(f"   列名: {df.columns.tolist()}")
    print(f"   前3行:\n{df.head(3)}\n")
except Exception as e:
    print(f"   ✗ 失败: {e}\n")
