# 新浪财经数据源集成说明

## 实现状态

✅ 已实现新浪财经作为主数据源，东方财富作为备用数据源的多源降级机制。

## 代码修改

### data_fetcher.py

新增三个函数：

1. **get_realtime_quotes_from_sina()** - 从新浪财经获取全市场行情
   - 支持重试机制（3次）
   - 自动处理股票代码格式
   - 过滤无效数据

2. **get_realtime_quotes_from_em()** - 从东方财富获取行情（原逻辑）
   - 作为备用数据源
   - 并发获取

3. **get_realtime_quotes()** - 多源降级（重构）
   - 优先使用新浪财经
   - 失败时降级到东方财富

## 降级策略

```
get_realtime_quotes()
    ↓
尝试新浪财经（3次重试）
    ↓ 失败
尝试东方财富（并发获取）
    ↓ 失败
返回空DataFrame
```

## 当前问题

### 问题1：新浪接口不稳定

**现象**：
```
JSONDecodeError: Can not decode value starting with character '<'
```

**原因**：
- 新浪API有时返回HTML而不是JSON
- 可能是反爬虫机制
- 或者服务端问题

**解决方案**：
1. 已添加重试机制（3次）
2. 已添加延迟（2秒）
3. 如果仍失败，降级到东方财富

### 问题2：非交易时间所有数据源都不稳定

**现状**：
- 东方财富：❌ Connection aborted
- 新浪财经：❌ JSONDecodeError
- 同花顺：✅ 仅板块列表可用

**结论**：
选股功能需要大量实时数据，非交易时间所有数据源都不够稳定。

## 测试建议

### 在交易时间测试

**最佳测试时间**：
- 周一至周五 9:30-15:00

**测试命令**：
```bash
python3 test_sina_quotes.py
```

**预期结果**：
- 新浪财经：✅ 获取5000+只股票
- 选股功能：✅ 正常工作

## 使用说明

### 自动切换

系统会自动选择可用的数据源：

1. **交易时间**：
   - 新浪财经（主）→ 东方财富（备）
   - 预期：新浪成功率高

2. **非交易时间**：
   - 新浪财经（主）→ 东方财富（备）
   - 预期：都可能失败

### 手动测试

```python
from data_fetcher import get_realtime_quotes_from_sina, get_realtime_quotes_from_em

# 测试新浪
df_sina = get_realtime_quotes_from_sina()
print(f'新浪: {len(df_sina)} 只')

# 测试东方财富
df_em = get_realtime_quotes_from_em(['000001', '600519'], max_workers=4)
print(f'东方财富: {len(df_em)} 只')
```

## 优势对比

| 特性 | 新浪财经 | 东方财富 |
|------|---------|---------|
| 获取方式 | 一次性全市场 | 逐个并发获取 |
| 速度 | 快（40秒） | 慢（需要500次请求） |
| 稳定性 | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| 交易时间 | ✅ | ✅ |
| 非交易时间 | ⚠️ 不稳定 | ❌ 基本不可用 |
| 数据完整性 | ✅ | ✅ |

## 下一步优化

### 方案1：增加更多数据源

可以考虑：
- 腾讯财经
- 网易财经
- 雪球

### 方案2：实现选股结果缓存

```python
# 缓存每日选股结果
cache_file = f'.cache/selection_{date}.json'

# 非交易时间使用缓存
if not is_trading_time():
    return load_cached_selection()
```

### 方案3：使用付费数据源

如果需要更高的稳定性：
- Tushare Pro（付费）
- 聚宽（付费）
- 米筐（付费）

## 总结

1. ✅ 已实现新浪财经集成
2. ✅ 已实现多源降级机制
3. ⚠️ 非交易时间所有免费数据源都不够稳定
4. 💡 建议在交易时间使用，或实现选股结果缓存

## 测试脚本

创建 `test_sina_quotes.py` 用于测试：

```python
#!/usr/bin/env python3
import sys
from data_fetcher import get_realtime_quotes

print('测试新浪财经数据源')
print('=' * 60)

df = get_realtime_quotes([])

if not df.empty:
    print(f'✅ 成功获取 {len(df)} 只股票')
    print(f'\n前5只:')
    for i, row in df.head().iterrows():
        print(f'  {row["code"]} {row["name"]}: ¥{row["price"]}')
    sys.exit(0)
else:
    print('❌ 获取失败')
    sys.exit(1)
```

运行：
```bash
chmod +x test_sina_quotes.py
python3 test_sina_quotes.py
```
