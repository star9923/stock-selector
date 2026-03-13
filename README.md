# A股智能选股系统

基于 AkShare 的 A 股智能选股工具，综合技术面和基本面多维度评分。

## 功能特性

- **技术面分析**：均线、MACD、RSI、KDJ、布林带、量能
- **基本面分析**：PE/PB 估值、ROE、毛利率、换手率
- **智能打分**：可自定义技术面/基本面权重
- **Web 界面**：实时选股、结果可视化
- **命令行模式**：支持批量筛选和导出

## 安装

```bash
pip install -r requirements.txt
```

## 使用方式

### 1. Web 界面（推荐）

```bash
python app.py
```

访问 http://localhost:5000

### 2. 命令行

```bash
# 默认参数（返回前20只，最低50分）
python main.py

# 自定义参数
python main.py --top 30 --min-score 60 --tech-weight 0.7 --fund-weight 0.3
```

## 评分规则

### 技术面（默认权重 0.6）
- **趋势**（40分）：多头排列、均线系统
- **动量**（40分）：MACD、RSI 健康度
- **量能**（20分）：成交量放大

### 基本面（默认权重 0.4）
- **估值**（40分）：PE < 30、PB < 3 优先
- **盈利**（40分）：ROE > 15%、毛利率 > 30%
- **流动性**（20分）：换手率 1-5% 适中

## 过滤条件

- 剔除 ST、*ST 股票
- 流通市值 > 20亿
- 股价 > 1元（去仙股）

## 注意事项

- AkShare 数据有延迟，仅供参考
- 首次运行会遍历全市场，耗时较长（约 5-10 分钟）
- 建议在交易时间外运行，避免数据不稳定
- 选股结果不构成投资建议

## 项目结构

```
stock_selector/
├── app.py              # Flask Web 服务
├── main.py             # 命令行入口
├── data_fetcher.py     # AkShare 数据获取
├── indicators.py       # 技术指标计算
├── fundamental.py      # 基本面筛选
├── selector.py         # 选股核心逻辑
├── templates/
│   └── index.html      # Web 前端
└── requirements.txt
```

## License

MIT
