# API 连接问题说明

## 问题现象

```
⏳ get_board_sentiment 重试 1/3，等待 3s...
⏳ get_board_sentiment 重试 2/3，等待 6s...
⚠️  get_board_sentiment 失败 (重试3次): ('Connection aborted.', RemoteDisconnected...
```

## 原因分析

这是**正常现象**，原因如下：

### 1. 非交易时间限制
- **交易时间**：周一至周五 9:30-15:00
- **非交易时间**：东方财富 API 服务不稳定或部分不可用
- **周末/节假日**：API 响应缓慢或无响应

### 2. API 服务器限制
- 请求频率限制（防止爬虫）
- 服务器负载过高时主动断开连接
- IP 访问频率限制

### 3. 网络环境
- 网络不稳定
- DNS 解析问题
- 防火墙/安全软件拦截

## 解决方案

### 方案1：在交易时间使用（推荐）

**最佳使用时间**：
- 周一至周五 9:30-15:00（交易时间）
- 或 15:00-16:00（盘后数据更新时间）

在交易时间运行以下命令更新缓存：
```bash
python3 update_board_cache.py
```

### 方案2：使用缓存数据

系统已实现多层缓存：
- 板块情绪：6小时短期缓存 + 7天长期缓存
- 板块成分股：7天缓存
- 个股历史：1天缓存

**缓存位置**：
```
.cache/
├── get_board_sentiment.json          # 板块情绪短期缓存
├── board_sentiment_fallback.json     # 板块情绪长期缓存
├── sector_stocks/                     # 板块成分股缓存
│   ├── 人工智能.json
│   └── 半导体.json
└── stock_history/                     # 个股历史缓存
    ├── 600519.json
    └── 000001.json
```

### 方案3：调整重试策略

如果网络环境较差，可以修改 `sentiment.py` 中的重试参数：

```python
@retry_on_failure(max_retries=5, delay=5, backoff=2)  # 增加重试次数和延迟
def get_board_sentiment() -> pd.DataFrame:
    ...
```

### 方案4：检查网络连接

```bash
# 测试是否能访问东方财富
ping push2.eastmoney.com

# 测试 DNS 解析
nslookup push2.eastmoney.com

# 检查代理设置
echo $http_proxy
echo $https_proxy
```

## 系统行为

当 API 失败时，系统会：

1. **自动重试** 3次（指数退避：3s → 6s → 12s）
2. **使用缓存** 如果有可用的缓存数据
3. **返回错误** 如果 API 和缓存都不可用

**前端提示**：
- 板块热度：显示"暂无数据，请检查网络连接或稍后重试"
- 个股分析：显示"无法获取该股票数据，请检查网络连接或在交易时间重试"

## 建议

1. **定期更新缓存**：每周在交易时间运行一次 `update_board_cache.py`
2. **避免频繁请求**：短时间内不要重复刷新
3. **使用缓存数据**：非交易时间依赖缓存即可
4. **耐心等待**：API 重试需要时间（最多约20秒）

## 技术细节

系统已禁用代理，直连 API：
```python
# akshare_config.py
os.environ['NO_PROXY'] = '*'
os.environ.pop('http_proxy', None)
os.environ.pop('https_proxy', None)
```

超时设置：30秒
重试策略：3次，指数退避（3s → 6s → 12s）
