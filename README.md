# A股智能选股系统

基于技术面、基本面和市场情绪的综合评分选股系统，支持多数据源、AI 智能分析、板块热度追踪等功能。

## 功能概览

- **智能选股** — 多维度综合评分，自动筛选优质股票
- **个股分析** — 技术指标、基本面、交易信号深度分析
- **AI 智能分析** — 接入 Claude 大模型，对技术指标进行专业解读
- **板块热度** — 实时追踪行业板块涨跌和资金流向
- **数据导出** — 支持导出选股结果和分析报告
- **多数据源** — 支持新浪财经、东方财富、同花顺、雪球，自动降级

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动服务

```bash
python app.py
```

访问 http://localhost:5001

### 3. 配置 AI 分析（可选）

在 Web 界面的「系统设置 > AI 分析配置」中配置：
- API Base URL
- API Key
- 模型选择

## 项目结构

```
stock_selector/
├── app.py                  # Flask Web 服务入口
├── main.py                 # CLI 命令行入口
├── requirements.txt        # 依赖列表
│
├── core/                   # 核心选股逻辑
│   ├── selector.py         # 智能选股引擎
│   ├── indicators.py       # 技术指标计算（MA/MACD/RSI/KDJ/BOLL）
│   └── fundamental.py      # 基本面评分与过滤
│
├── data/                   # 数据获取与缓存
│   ├── akshare_config.py   # AkShare 统一配置（代理/SSL）
│   ├── data_fetcher.py     # 多源行情数据获取（新浪/东方财富/雪球）
│   ├── board_data_source.py    # 板块数据多源获取（同花顺/东方财富）
│   ├── stock_data_fallback.py  # 个股历史数据缓存
│   ├── sector_data_fallback.py # 板块数据缓存
│   └── sector_fallback.py      # 板块映射备用数据
│
├── services/               # 业务服务
│   ├── stock_analyzer.py   # 个股深度分析
│   ├── sector_analyzer.py  # 板块分析
│   ├── sentiment.py        # 市场情绪分析
│   ├── ai_analyzer.py      # AI 智能分析（Claude）
│   └── export_service.py   # 数据导出服务
│
├── templates/              # 前端页面
│   └── index.html          # 单页应用（侧边栏布局）
│
├── utils/                  # 工具脚本
│   ├── update_board_cache.py   # 手动更新板块缓存
│   └── diagnose_api.py         # API 连接诊断
│
├── tests/                  # 测试文件
│   ├── test_akshare.py
│   ├── test_export.py
│   └── test_sina_quotes.py
│
├── docs/                   # 文档
│   ├── DATA_SOURCE_COMPARISON.md   # 数据源对比
│   ├── MULTI_SOURCE_SUMMARY.md     # 多源集成总结
│   └── ...
│
├── .cache/                 # 缓存目录（自动生成，已 gitignore）
├── stock_mapping.json      # 股票代码-名称映射
└── fetch_stock_mapping.py  # 更新股票映射脚本
```

## 数据源

系统支持 4 个免费数据源，自动降级：

| 数据源 | 用途 | 稳定性 | 非交易时间 |
|--------|------|--------|-----------|
| 新浪财经 | 选股行情（主） | ⭐⭐⭐⭐ | 较稳定 |
| 东方财富 | 选股行情（备）+ 板块行情 | ⭐⭐⭐ | 不稳定 |
| 同花顺 | 板块列表 | ⭐⭐⭐⭐⭐ | 稳定 |
| 雪球 | 社区热度 | ⭐⭐⭐⭐⭐ | 稳定 |

### 降级策略

```
选股行情：新浪财经 → 东方财富
板块列表：同花顺 → 东方财富
板块行情：东方财富 → 缓存
个股历史：东方财富 → 新浪财经 → 缓存
```

## 选股评分体系

### 技术面（默认权重 50%）
- 趋势分析：均线系统（MA5/10/20/60）
- 动量指标：MACD、RSI、KDJ
- 量价分析：成交量变化、换手率
- 风险指标：布林带位置、波动率

### 基本面（默认权重 30%）
- 估值：PE、PB
- 盈利能力：ROE、毛利率
- 成长性：EPS
- 流动性：换手率、市值

### 市场情绪（默认权重 20%）
- 热门股票关注度
- 所属板块涨跌幅
- 板块资金流向

## AI 智能分析

集成 Claude 大模型，对个股技术指标进行专业分析：

- 趋势分析（均线系统）
- 动量分析（MACD/RSI/KDJ）
- 支撑压力位（布林带）
- 量价关系
- 综合操作建议

分析结果支持 Markdown 渲染和导出为图片。

### 配置方法

在 Web 界面「系统设置 > AI 分析配置」中设置：
- API Base URL（支持第三方代理）
- API Key（加密存储在本地）
- 模型选择（Sonnet/Opus/Haiku）

## 缓存机制

系统实现了分层缓存，提高稳定性：

| 数据类型 | 缓存时间 | 说明 |
|---------|---------|------|
| 板块列表 | 30 天 | 板块不常变化 |
| 板块行情 | 24 小时 | 降级使用 |
| 个股历史 | 1 天 | 每日更新 |
| AI 配置 | 永久 | 手动修改 |

### 手动更新缓存

```bash
python utils/update_board_cache.py
```

### 诊断 API 连接

```bash
python utils/diagnose_api.py
```

## 系统设置

Web 界面提供以下设置：

- **数据源选择** — 同花顺 / 东方财富
- **AI 分析配置** — API Key / Base URL / 模型
- **缓存管理** — 查看状态 / 清理缓存

## 使用建议

- **交易时间**（周一至周五 9:30-15:00）：所有功能正常可用
- **非交易时间**：板块列表、个股分析（新浪）、AI 分析可用；选股和板块行情依赖缓存
- **首次使用**：建议在交易时间运行一次，让系统缓存数据

## 技术栈

- **后端**：Python + Flask
- **前端**：原生 HTML/CSS/JS + marked.js + html2canvas
- **数据**：AkShare（新浪/东方财富/同花顺/雪球）
- **AI**：Anthropic Claude API
