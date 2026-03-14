# AkShare 板块数据接口说明

## 问题

之前使用的 `ak.stock_board_industry_spot_em()` 在非交易时间连接不稳定，导致板块数据获取失败。

## AkShare 提供的板块接口

### 1. 东方财富（EM）接口

**行业板块**：
- `stock_board_industry_name_em()` - 获取行业板块名称列表
- `stock_board_industry_spot_em()` - 获取行业板块实时行情（含涨跌幅、上涨下跌家数）⭐
- `stock_board_industry_cons_em()` - 获取行业板块成分股
- `stock_board_industry_hist_em()` - 获取行业板块历史行情

**概念板块**：
- `stock_board_concept_name_em()` - 获取概念板块名称列表
- `stock_board_concept_spot_em()` - 获取概念板块实时行情
- `stock_board_concept_cons_em()` - 获取概念板块成分股

**特点**：
- ✅ 数据完整（涨跌幅、上涨下跌家数、成交额等）
- ❌ 非交易时间连接不稳定
- ❌ 周末/节假日经常失败

### 2. 同花顺（THS）接口

**行业板块**：
- `stock_board_industry_name_ths()` - 获取行业板块名称列表 ⭐
- `stock_board_industry_index_ths()` - 获取行业板块指数数据
- `stock_board_industry_info_ths()` - 获取行业板块简介

**概念板块**：
- `stock_board_concept_name_ths()` - 获取概念板块名称列表
- `stock_board_concept_index_ths()` - 获取概念板块指数数据

**特点**：
- ✅ 连接稳定，非交易时间也可用
- ✅ 板块分类详细（90个行业板块，375个概念板块）
- ❌ 缺少实时涨跌幅和上涨下跌家数数据

## 解决方案

### 实现多源数据获取

创建 `board_data_source.py` 模块，实现：

1. **板块列表获取**：
   - 优先：东方财富 `stock_board_industry_name_em()`
   - 备用：同花顺 `stock_board_industry_name_ths()` ✅ 稳定可用

2. **板块情绪数据**：
   - 仅东方财富提供完整数据（涨跌幅+上涨下跌家数）
   - 失败时使用缓存

### 数据对比

| 数据源 | 板块数量 | 实时行情 | 涨跌幅 | 上涨下跌家数 | 稳定性 |
|--------|---------|---------|--------|-------------|--------|
| 东方财富 | ~100 | ✅ | ✅ | ✅ | ⚠️ 非交易时间不稳定 |
| 同花顺 | 90 | ❌ | ❌ | ❌ | ✅ 稳定 |

## 使用建议

1. **板块列表**：使用多源获取，同花顺作为备用
2. **板块行情**：依赖东方财富 + 缓存机制
3. **交易时间**：在交易时间更新缓存，非交易时间使用缓存

## 代码示例

```python
from board_data_source import get_board_list_multi_source, get_board_sentiment_multi_source

# 获取板块列表（多源）
boards = get_board_list_multi_source()  # 东方财富失败时自动切换到同花顺

# 获取板块情绪（仅东方财富）
sentiment = get_board_sentiment_multi_source()  # 失败时返回空DataFrame
```

## 测试结果

```bash
# 周六非交易时间测试
东方财富接口: ❌ Connection aborted
同花顺接口:   ✅ 成功获取 90 个板块
```

## 总结

- AkShare **有**获取板块数据的接口，且有多个数据源
- 东方财富接口功能最完整，但非交易时间不稳定
- 同花顺接口稳定可用，但数据不够完整
- 系统已实现多源获取 + 缓存机制，确保可用性
