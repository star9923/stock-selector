# 股吧信息功能说明

## 功能概述

新增股吧信息获取和分析功能，通过东方财富股吧数据评估个股的市场关注度和散户情绪。

## 数据来源

- **数据源**: 东方财富股吧 (akshare `stock_comment_em`)
- **更新频率**: 实时数据
- **覆盖范围**: 全市场 5000+ 只股票

## 股吧指标说明

### 1. 关注指数 (0-100)
- 反映股票在股吧的关注热度
- **评分标准**:
  - ≥90: 极高关注 (+10分)
  - ≥80: 高关注 (+8分)
  - ≥70: 中等关注 (+6分)
  - ≥60: 一般关注 (+4分)

### 2. 综合得分 (0-100)
- 东方财富综合评分，包含多个维度
- **评分标准**:
  - ≥70: 优秀 (+5分)
  - ≥60: 良好 (+3分)

### 3. 机构参与度 (%)
- 机构投资者的参与程度
- 数值越高，机构关注度越高

### 4. 排名变化
- 股吧热度排名的变化情况
- **评分标准**:
  - 上升 >1000: 快速上升 (+5分)
  - 上升 >500: 稳步上升 (+3分)
  - 上升 >0: 小幅上升 (+1分)

### 5. 当前排名
- 在全市场的热度排名
- 排名越靠前，关注度越高

## 评分体系

### 股吧得分 (0-20分)
- 关注指数: 0-10分
- 综合得分: 0-5分
- 排名变化: 0-5分

### 市场情绪总分 (0-80分)
- 热度得分: 0-30分 (热门股票榜)
- 板块得分: 0-30分 (板块情绪)
- **股吧得分: 0-20分** (新增)

## 使用方法

### 1. 在个股分析中使用

```python
from services.stock_analyzer import analyze_stock

# 启用情绪分析（包含股吧信息）
result = analyze_stock("600519", enable_sentiment=True)

# 获取股吧信息
sentiment = result["sentiment"]
print(f"股吧得分: {sentiment['guba_score']}/20")

if "guba_info" in sentiment:
    guba = sentiment["guba_info"]
    print(f"关注指数: {guba['attention_index']}")
    print(f"综合得分: {guba['comprehensive_score']}")
    print(f"机构参与度: {guba['institution_participation']}")
    print(f"当前排名: {guba['current_rank']}")
    print(f"排名变化: {guba['rank_change']}")
```

### 2. 直接获取股吧数据

```python
from services.sentiment import get_stock_guba_data

# 获取全市场股吧数据
guba_data = get_stock_guba_data()

# 查询特定股票
stock_guba = guba_data[guba_data["code"] == "600519"]
```

### 3. AI 分析集成

AI 分析会自动包含股吧信息维度：

```python
from services.ai_analyzer import analyze_with_ai

result = analyze_stock("600519", enable_sentiment=True)
ai_analysis = analyze_with_ai(result)
```

AI 会从以下角度分析股吧数据：
- 市场关注度趋势
- 散户情绪判断
- 机构参与度评估
- 与技术面、基本面的综合判断

## 应用场景

### 1. 热点追踪
- 关注指数高 + 排名快速上升 → 可能是市场热点
- 适合短线交易者关注

### 2. 情绪判断
- 综合得分高 + 机构参与度高 → 市场认可度高
- 可作为中长期投资参考

### 3. 风险提示
- 关注指数极高但技术面走弱 → 可能过度炒作
- 排名快速下降 → 市场热度消退

## 注意事项

1. **数据时效性**: 股吧数据实时更新，建议配合缓存机制使用
2. **情绪波动**: 股吧热度波动较大，不宜作为唯一决策依据
3. **综合判断**: 应结合技术面、基本面、新闻面综合分析
4. **风险控制**: 高关注度不等于高收益，注意风险管理

## 测试脚本

运行测试脚本查看完整功能：

```bash
python test_guba.py
```

## 更新日志

- **2026-03-14**: 新增股吧信息获取和分析功能
  - 添加 `get_stock_guba_data()` 函数
  - 更新 `score_sentiment()` 增加股吧评分维度
  - AI 分析 prompt 集成股吧信息
  - 市场情绪总分从 60 分调整为 80 分
  - 新闻时间范围从1个月扩大到3个月
  - 最大新闻条数从20条增加到30条
