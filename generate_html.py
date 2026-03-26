import pandas as pd
import os
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(SCRIPT_DIR)

csv_files = [f for f in os.listdir('.') if f.startswith('result_') and f.endswith('.csv')]
if not csv_files:
    print('No result files found, generating empty page')
    df = pd.DataFrame(columns=['code', 'name', 'price', 'pct_change', 'pe', 'pb', 'turnover_rate', 'tech_score', 'fund_score', 'total_score'])
    latest = None
else:
    latest = sorted(csv_files)[-1]
    df = pd.read_csv(latest)
    print(f"Loaded result file: {latest}")




html = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>A股智能选股系统</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 15px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 25px 20px;
            text-align: center;
        }
        .header h1 { font-size: 24px; margin-bottom: 8px; }
        .header p { opacity: 0.9; font-size: 13px; }
        .header .update-time {
            margin-top: 10px;
            font-size: 12px;
            opacity: 0.8;
        }
        .summary {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            padding: 20px;
            background: #f8f9fa;
            border-bottom: 1px solid #e9ecef;
        }
        .summary-card {
            background: white;
            padding: 15px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }
        .summary-card .label {
            font-size: 12px;
            color: #6c757d;
            margin-bottom: 5px;
        }
        .summary-card .value {
            font-size: 20px;
            font-weight: 700;
            color: #667eea;
        }
        .results { padding: 20px; }
        .results-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            flex-wrap: wrap;
            gap: 10px;
        }
        .results-header h2 { color: #212529; font-size: 18px; }
        .timestamp {
            color: #6c757d;
            font-size: 13px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            background: white;
        }
        thead {
            background: #f8f9fa;
        }
        th, td {
            padding: 12px 10px;
            text-align: left;
            border-bottom: 1px solid #e9ecef;
            font-size: 13px;
        }
        th {
            font-weight: 600;
            color: #495057;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            white-space: nowrap;
        }
        td { color: #212529; }
        tr:hover { background: #f8f9fa; }
        .rank {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 28px;
            height: 28px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 50%;
            font-weight: bold;
            font-size: 12px;
        }
        .rank.top-3 {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        }
        .code {
            background: #e9ecef;
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 11px;
            color: #6c757d;
        }
        .name {
            font-weight: 600;
            max-width: 80px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .price {
            font-weight: 600;
            white-space: nowrap;
        }
        .pct-up { color: #dc3545; font-weight: 600; }
        .pct-down { color: #28a745; font-weight: 600; }
        .score {
            display: inline-block;
            padding: 3px 8px;
            border-radius: 10px;
            font-weight: 600;
            font-size: 11px;
            text-align: center;
            min-width: 32px;
        }
        .score-high { background: #d4edda; color: #155724; }
        .score-mid { background: #fff3cd; color: #856404; }
        .score-low { background: #f8d7da; color: #721c24; }
        .empty {
            text-align: center;
            padding: 60px;
            color: #6c757d;
        }
        .footer {
            text-align: center;
            padding: 20px;
            background: linear-gradient(135deg, #fff3cd 0%, #ffeeba 100%);
            color: #856404;
            font-size: 12px;
            border-top: 3px solid #ffc107;
        }
        .footer-item {
            margin-bottom: 8px;
            padding: 8px 12px;
            background: rgba(255,255,255,0.8);
            border-radius: 8px;
            display: inline-block;
        }
        .footer-item:last-child {
            color: #dc3545;
            font-weight: 600;
            background: rgba(220,53,69,0.1);
            border: 1px solid rgba(220,53,69,0.3);
        }
        .card-list { display: none; }
        .stock-card {
            background: white;
            border-radius: 12px;
            padding: 16px;
            margin-bottom: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }
        .stock-card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }
        .stock-card-left {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .stock-card-code { font-size: 13px; color: #6c757d; }
        .stock-card-name { font-size: 16px; font-weight: 600; }
        .stock-card-price { font-size: 18px; font-weight: 700; }
        .stock-card-pct { font-size: 16px; font-weight: 600; }
        .stock-card-detail {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 8px;
            font-size: 12px;
        }
        .stock-card-item { text-align: center; }
        .stock-card-item .label { color: #6c757d; margin-bottom: 2px; }
        .stock-card-item .val { font-weight: 600; }
        @media (max-width: 768px) {
            body { padding: 10px; }
            .header h1 { font-size: 20px; }
            .summary { grid-template-columns: repeat(2, 1fr); padding: 15px; gap: 10px; }
            .summary-card { padding: 12px; }
            .summary-card .value { font-size: 18px; }
            .results { padding: 15px; }
            .results-header h2 { font-size: 16px; }
            table { display: none; }
            .card-list { display: block !important; }
        }
        @media (max-width: 480px) {
            .header { padding: 20px 15px; }
            .header h1 { font-size: 18px; display: none; }
            .summary { grid-template-columns: 1fr 1fr; }
            .hide-small { display: none; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>A股智能选股系统</h1>
            <p>技术面 + 基本面综合评分</p>
            <p class="update-time">更新时间: ''' + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '''</p>
        </div>

        <div class="summary">
            <div class="summary-card">
                <div class="label">选出股票</div>
                <div class="value">''' + str(len(df)) + ''' 只</div>
            </div>
            <div class="summary-card">
                <div class="label">平均涨幅</div>
                <div class="value">''' + f"{(df['pct_change'].mean() if 'pct_change' in df.columns else 0):.2f}%" + '''</div>
            </div>
            <div class="summary-card">
                <div class="label">最高涨幅</div>
                <div class="value">''' + f"{(df['pct_change'].max() if 'pct_change' in df.columns else 0):.2f}%" + '''</div>
            </div>
            <div class="summary-card">
                <div class="label">平均综合分</div>
                <div class="value">''' + f"{(df['total_score'].mean() if 'total_score' in df.columns else 0):.1f}" + '''</div>
            </div>
        </div>

        <div class="results">
            <div class="results-header">
                <h2>选股结果</h2>
                <div class="timestamp">共 ''' + str(len(df)) + ''' 只股票</div>
            </div>
            <table>
                <thead>
                    <tr>
                        <th>排名</th>
                        <th>代码</th>
                        <th>名称</th>
                        <th>价格</th>
                        <th>涨跌幅</th>
                        <th class="hide-mobile">市盈率</th>
                        <th class="hide-small hide-mobile">市净率</th>
                        <th class="hide-small">市值(亿)</th>
                        <th class="hide-small">收益率</th>
                        <th class="hide-small">流动性</th>
                        <th>技术分</th>
                        <th>基本分</th>
                        <th>综合分</th>
                    </tr>
                </thead>
                <tbody>
'''

for idx, row in df.iterrows():
    if pd.isna(row.get('code')):
        continue
    rank_class = 'top-3' if idx < 3 else ''
    pct = row.get('pct_change', 0)
    pct_class = 'pct-up' if pct > 0 else 'pct-down'
    pct_str = f'+{pct:.2f}%' if pct >= 0 else f'{pct:.2f}%'
    
    tech_score = row.get('tech_score', 0)
    fund_score = row.get('fund_score', 0)
    total_score = row.get('total_score', 0)
    
    tech_cls = 'score-high' if tech_score >= 70 else 'score-mid' if tech_score >= 50 else 'score-low'
    fund_cls = 'score-high' if fund_score >= 70 else 'score-mid' if fund_score >= 50 else 'score-low'
    total_cls = 'score-high' if total_score >= 70 else 'score-mid' if total_score >= 50 else 'score-low'
    
    pe_val = row.get('pe')
    pb_val = row.get('pb')
    market_cap_val = row.get('market_cap', 0)
    fund_liquidity = row.get('fund_liquidity', 0)
    pe_str = f"{pe_val:.2f}" if isinstance(pe_val, (int, float)) and not pd.isna(pe_val) and pe_val > 0 else '-'
    pb_str = f"{pb_val:.2f}" if isinstance(pb_val, (int, float)) and not pd.isna(pb_val) and pb_val > 0 else '-'
    market_cap_str = f"{market_cap_val/1e8:.1f}" if isinstance(market_cap_val, (int, float)) and not pd.isna(market_cap_val) and market_cap_val > 0 else '-'
    
    html += f'''
                    <tr>
                        <td><span class="rank {rank_class}">{idx + 1}</span></td>
                        <td><span class="code">{row.get('code', '')}</span></td>
                        <td><span class="name">{row.get('name', '')}</span></td>
                        <td class="price">¥{row.get('price', 0):.2f}</td>
                        <td class="{pct_class}">{pct_str}</td>
                        <td class="hide-mobile">{pe_str}</td>
                        <td class="hide-small hide-mobile">{pb_str}</td>
                        <td class="hide-small">{market_cap_str}</td>
                        <td class="hide-small">{pct_str}</td>
                        <td class="hide-small">{fund_liquidity}</td>
                        <td><span class="score {tech_cls}">{tech_score:.0f}</span></td>
                        <td><span class="score {fund_cls}">{fund_score:.0f}</span></td>
                        <td><span class="score {total_cls}">{total_score:.1f}</span></td>
                    </tr>
'''

html += '''
                </tbody>
            </table>
            <div class="card-list">
'''

for idx, row in df.iterrows():
    if pd.isna(row.get('code')):
        continue
    rank_class = 'top-3' if idx < 3 else ''
    pct = row.get('pct_change', 0)
    pct_class = 'pct-up' if pct > 0 else 'pct-down'
    pct_str = f'+{pct:.2f}%' if pct >= 0 else f'{pct:.2f}%'
    
    tech_score = row.get('tech_score', 0)
    fund_score = row.get('fund_score', 0)
    total_score = row.get('total_score', 0)
    fund_liquidity = row.get('fund_liquidity', 0)
    
    pe_val = row.get('pe')
    pb_val = row.get('pb')
    market_cap_val = row.get('market_cap', 0)
    turnover_rate_val = row.get('turnover_rate', 0)
    pe_str = f"{pe_val:.2f}" if isinstance(pe_val, (int, float)) and not pd.isna(pe_val) and pe_val > 0 else '-'
    pb_str = f"{pb_val:.2f}" if isinstance(pb_val, (int, float)) and not pd.isna(pb_val) and pb_val > 0 else '-'
    market_cap_str = f"{market_cap_val/1e8:.1f}" if isinstance(market_cap_val, (int, float)) and not pd.isna(market_cap_val) and market_cap_val > 0 else '-'
    turnover_rate_str = f"{turnover_rate_val:.1f}%" if isinstance(turnover_rate_val, (int, float)) and not pd.isna(turnover_rate_val) and turnover_rate_val > 0 else '-'
    
    html += f'''
                <div class="stock-card">
                    <div class="stock-card-header">
                        <div class="stock-card-left">
                            <span class="rank {rank_class}">{idx + 1}</span>
                            <div>
                                <div class="stock-card-code">{row.get('code', '')}</div>
                                <div class="stock-card-name">{row.get('name', '')}</div>
                            </div>
                        </div>
                        <div style="text-align:right">
                            <div class="stock-card-price">¥{row.get('price', 0):.2f}</div>
                            <div class="stock-card-pct {pct_class}">{pct_str}</div>
                        </div>
                    </div>
                    <div class="stock-card-detail">
                        <div class="stock-card-item">
                            <div class="label">市盈率</div>
                            <div class="val">{pe_str}</div>
                        </div>
                        <div class="stock-card-item">
                            <div class="label">市净率</div>
                            <div class="val">{pb_str}</div>
                        </div>
                        <div class="stock-card-item">
                            <div class="label">市值(亿)</div>
                            <div class="val">{market_cap_str}</div>
                        </div>
                        <div class="stock-card-item">
                            <div class="label">换手率</div>
                            <div class="val">{turnover_rate_str}</div>
                        </div>
                        <div class="stock-card-item">
                            <div class="label">收益率</div>
                            <div class="val">{pct_str}</div>
                        </div>
                        <div class="stock-card-item">
                            <div class="label">流动性</div>
                            <div class="val">{fund_liquidity}</div>
                        </div>
                        <div class="stock-card-item">
                            <div class="label">技术分</div>
                            <div class="val">{tech_score:.0f}</div>
                        </div>
                        <div class="stock-card-item">
                            <div class="label">基本面</div>
                            <div class="val">{fund_score:.0f}</div>
                        </div>
                        <div class="stock-card-item">
                            <div class="label">综合分</div>
                            <div class="val" style="color:#667eea">{total_score:.1f}</div>
                        </div>
                    </div>
                </div>
'''

html += f'''</div>
        </div>

        <div class="footer">
            <div class="footer-item">
            评分标准：根据估值、盈利能力（净资产收益率、毛利率、每股收益）、成长性（近期涨幅，市值规模）、流动性（换手率）、去掉 ST / *ST / 退市、去掉涨停/跌停（避免追高杀跌）、价格 > 1 元（去仙股）、去掉停牌股（成交量为 0）、成交额 > 1000万（过滤成交不活跃股票）
            </div>
            <div class="footer-item">
            提示：智能选股仅供学习、参考，请勿用于实盘交易
            </div>
        </div>
    </div>
</body>
</html>'''


with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print(f'HTML generated: {len(df)} stocks')
