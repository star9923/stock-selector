# 导出功能 API 文档

## 概述
系统提供完整的数据导出功能，支持Excel和CSV格式。

## API 接口

### 1. 导出选股结果
**接口**: `POST /api/export/selection`

**请求参数**:
```json
{
  "data": [  // 可选，不传则使用缓存数据
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
    }
  ],
  "format": "excel"  // 可选: "excel" 或 "csv"，默认 "excel"
}
```

**响应**:
```json
{
  "success": true,
  "filename": "选股结果_20260314_151630.xlsx",
  "message": "导出成功：选股结果_20260314_151630.xlsx"
}
```

### 2. 导出股票分析报告
**接口**: `GET /api/export/analysis/<code>?format=excel`

**参数**:
- `code`: 股票代码（路径参数）
- `format`: 导出格式，可选 "excel" 或 "csv"（查询参数，默认 "excel"）

**示例**: `GET /api/export/analysis/600519?format=excel`

**响应**:
```json
{
  "success": true,
  "filename": "股票分析_贵州茅台_600519_20260314_151711.xlsx",
  "message": "导出成功：股票分析_贵州茅台_600519_20260314_151711.xlsx"
}
```

### 3. 导出板块分析
**接口**: `GET /api/export/sector/<sector_name>?format=excel`

**参数**:
- `sector_name`: 板块名称（路径参数）
- `format`: 导出格式（查询参数，默认 "excel"）

**示例**: `GET /api/export/sector/白酒?format=excel`

### 4. 获取导出文件列表
**接口**: `GET /api/export/files`

**响应**:
```json
{
  "success": true,
  "count": 3,
  "data": [
    {
      "filename": "股票分析_贵州茅台_600519_20260314_151711.xlsx",
      "size": 11738,
      "created_at": "2026-03-14 15:17:11"
    }
  ]
}
```

### 5. 下载导出文件
**接口**: `GET /api/export/download/<filename>`

**参数**:
- `filename`: 文件名（从文件列表获取）

**示例**: `GET /api/export/download/选股结果_20260314_151630.xlsx`

**响应**: 文件下载

### 6. 删除导出文件
**接口**: `DELETE /api/export/delete/<filename>`

**参数**:
- `filename`: 文件名

**响应**:
```json
{
  "success": true,
  "message": "删除成功"
}
```

## Excel 导出内容

### 选股结果 Excel
- 单个工作表，包含所有选股数据

### 股票分析报告 Excel
包含多个工作表：
1. **基本信息**: 价格、涨跌幅、成交量等
2. **技术分析**: MA、MACD、RSI、KDJ、布林带等指标
3. **基本面分析**: ROE、EPS、毛利率等
4. **情绪分析**: 热度得分、板块得分、所属板块
5. **历史价格**: 最近60天的价格数据
6. **交易信号**: 买卖信号列表

### 板块分析 Excel
包含多个工作表：
1. **板块概览**: 总股票数、涨跌家数、平均涨跌幅等
2. **板块情绪**: 板块涨跌幅、情绪得分
3. **涨幅榜**: 板块内涨幅前10的股票
4. **跌幅榜**: 板块内跌幅前10的股票

## 文件管理
- 导出文件保存在 `exports/` 目录
- 文件名自动添加时间戳，避免覆盖
- 系统启动时自动清理7天前的文件
- 支持手动删除文件

## 使用示例

### JavaScript 示例
```javascript
// 1. 导出选股结果
async function exportSelection() {
  const response = await fetch('/api/export/selection', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ format: 'excel' })
  });
  const result = await response.json();
  if (result.success) {
    // 下载文件
    window.location.href = `/api/export/download/${result.filename}`;
  }
}

// 2. 导出股票分析
async function exportStockAnalysis(code) {
  const response = await fetch(`/api/export/analysis/${code}?format=excel`);
  const result = await response.json();
  if (result.success) {
    window.location.href = `/api/export/download/${result.filename}`;
  }
}

// 3. 获取导出文件列表
async function getExportFiles() {
  const response = await fetch('/api/export/files');
  const result = await response.json();
  console.log(result.data);
}
```

### Python 示例
```python
import requests

# 导出选股结果
response = requests.post('http://localhost:5001/api/export/selection',
    json={'format': 'excel'})
result = response.json()
print(result['filename'])

# 下载文件
if result['success']:
    file_response = requests.get(
        f"http://localhost:5001/api/export/download/{result['filename']}")
    with open(result['filename'], 'wb') as f:
        f.write(file_response.content)
```
