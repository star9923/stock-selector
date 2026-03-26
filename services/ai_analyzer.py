"""
ai_analyzer.py - AI 智能分析模块
使用 Claude API 对股票技术指标进行深度分析
"""
import os
import json
import data.akshare_config
import akshare as ak
from anthropic import Anthropic
from datetime import datetime, timedelta
from utils.network_helper import retry_on_connection_error


AI_CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.cache', 'ai_config.json')


def load_ai_config() -> dict:
    """加载 AI 配置"""
    if os.path.exists(AI_CONFIG_FILE):
        try:
            with open(AI_CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    # 默认配置（从环境变量读取，用于向后兼容）
    return {
        "api_key": os.environ.get("ANTHROPIC_API_KEY", ""),
        "base_url": os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com"),
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 2000,
    }


def save_ai_config(config: dict):
    """保存 AI 配置"""
    os.makedirs(os.path.dirname(AI_CONFIG_FILE), exist_ok=True)
    with open(AI_CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def get_client() -> Anthropic:
    """获取 Anthropic 客户端"""
    config = load_ai_config()
    return Anthropic(
        api_key=config.get("api_key", ""),
        base_url=config.get("base_url", "https://api.anthropic.com"),
    )


@retry_on_connection_error(max_retries=3, delay=2)
def get_stock_news(code: str, max_count: int = 30) -> list:
    """
    获取个股近期新闻
    :param code: 股票代码
    :param max_count: 最大新闻条数
    :return: 新闻列表 [{"title": ..., "time": ..., "content": ...}]
    """
    try:
        df = ak.stock_news_em(symbol=code)
        if df.empty:
            return []

        # 只取近3个月的新闻
        three_months_ago = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
        if '发布时间' in df.columns:
            df = df[df['发布时间'] >= three_months_ago]

        news_list = []
        for _, row in df.head(max_count).iterrows():
            content = str(row.get('新闻内容', ''))
            # 截取前200字，避免 prompt 过长
            if len(content) > 200:
                content = content[:200] + '...'
            news_list.append({
                "title": str(row.get('新闻标题', '')),
                "time": str(row.get('发布时间', '')),
                "content": content,
                "source": str(row.get('文章来源', '')),
            })

        print(f"   ✅ 获取到 {len(news_list)} 条近期新闻")
        return news_list
    except Exception as e:
        print(f"   ⚠️  获取新闻失败: {str(e)[:50]}")
        return []


def analyze_with_ai(stock_data: dict) -> str:
    """
    使用 Claude 对股票技术指标进行智能分析
    :param stock_data: 股票分析数据（来自 analyze_stock）
    :return: AI 分析文本
    """
    client = get_client()

    # 构建分析提示
    code = stock_data.get("code", "")
    name = stock_data.get("name", "")
    basic = stock_data.get("basic_info", {})
    tech = stock_data.get("technical", {})
    fund = stock_data.get("fundamental", {})
    sentiment = stock_data.get("sentiment", {})
    signals = stock_data.get("signals", [])

    signals_text = ""
    for s in signals:
        tag = "看多" if s["type"] == "bullish" else ("看空" if s["type"] == "bearish" else "中性")
        signals_text += f"- [{tag}] {s['signal']}: {s['desc']}\n"

    if not signals_text:
        signals_text = "- 暂无明显信号\n"

    # 获取近期新闻
    news_list = get_stock_news(code)
    news_text = ""
    if news_list:
        for n in news_list:
            news_text += f"- [{n['time']}] {n['title']}\n  {n['content']}\n"
    else:
        news_text = "- 暂无近期新闻\n"

    # 构建股吧信息文本
    guba_text = ""
    guba_info = sentiment.get("guba_info", {})
    if guba_info:
        guba_text = f"""## 股吧热度
- 关注指数: {guba_info.get('attention_index', 0):.1f}/100
- 综合得分: {guba_info.get('comprehensive_score', 0):.1f}/100
- 机构参与度: {guba_info.get('institution_participation', 0):.1f}%
- 当前排名: 第 {guba_info.get('current_rank', 0)} 名
- 排名变化: {'↑' if guba_info.get('rank_change', 0) > 0 else '↓'} {abs(guba_info.get('rank_change', 0))} 位

"""

    prompt = f"""请对以下股票进行综合深度分析，结合技术指标、近期新闻和股吧热度，给出买入/持有/卖出建议。

## 股票信息
- 代码: {code}
- 名称: {name}
- 当前价格: {basic.get('price', 0)}
- 涨跌幅: {basic.get('pct_change', 0):.2f}%
- 52周最高: {basic.get('high_52w', 0)}
- 52周最低: {basic.get('low_52w', 0)}

## 技术指标
- 技术得分: {tech.get('score', {}).get('total', 0)}/100
  - 趋势: {tech.get('score', {}).get('trend', 0)} | 动量: {tech.get('score', {}).get('momentum', 0)} | 量能: {tech.get('score', {}).get('volume', 0)}
- MA5: {tech.get('ma5', 0):.2f} | MA10: {tech.get('ma10', 0):.2f} | MA20: {tech.get('ma20', 0):.2f} | MA60: {tech.get('ma60', 0):.2f}
- MACD: DIF={tech.get('macd_dif', 0):.4f}, DEA={tech.get('macd_dea', 0):.4f}, BAR={tech.get('macd_bar', 0):.4f}
- RSI(14): {tech.get('rsi', 0):.2f}
- KDJ: K={tech.get('kdj_k', 0):.2f}, D={tech.get('kdj_d', 0):.2f}, J={tech.get('kdj_j', 0):.2f}
- 布林带: 上轨={tech.get('boll_upper', 0):.2f}, 中轨={tech.get('boll_mid', 0):.2f}, 下轨={tech.get('boll_lower', 0):.2f}

## 基本面
- 基本面得分: {fund.get('score', {}).get('total', 0)}/100
- ROE: {fund.get('roe', 0)}%
- EPS: {fund.get('eps', 0)}
- 毛利率: {fund.get('gross_margin', 0)}%

## 市场情绪
- 情绪得分: {sentiment.get('score', 0)}/80
- 热度得分: {sentiment.get('hot_score', 0)}/30
- 板块得分: {sentiment.get('board_score', 0)}/30
- 股吧得分: {sentiment.get('guba_score', 0)}/20
- 所属板块: {sentiment.get('board_name', '未知')}

{guba_text}## 交易信号
{signals_text}

## 近3个月新闻动态
{news_text}

请从以下几个维度进行分析：
1. **趋势分析**：根据均线系统判断当前趋势
2. **动量分析**：根据 MACD、RSI、KDJ 判断动量强弱
3. **支撑压力**：根据布林带和关键价位判断支撑压力
4. **量价关系**：分析成交量与价格的配合情况
5. **新闻面分析**：结合近期新闻评估对股价的潜在影响（利好/利空/中性）
6. **股吧热度分析**：根据关注指数、综合得分、机构参与度等评估市场关注度和资金流向
7. **综合建议**：综合技术面、新闻面和市场情绪，给出明确的操作建议（买入/持有/卖出）和理由

注意：
- 请用中文回答
- 分析要专业但易懂
- 给出具体的支撑位和压力位
- 新闻面分析要客观，区分短期影响和长期影响
- 股吧热度可以反映散户情绪和市场关注度
- 风险提示不可少
"""

    try:
        config = load_ai_config()

        @retry_on_connection_error(max_retries=3, delay=3, timeout=60)
        def call_api():
            return client.messages.create(
                model=config.get("model", "claude-sonnet-4-20250514"),
                max_tokens=config.get("max_tokens", 2000),
                messages=[
                    {"role": "user", "content": prompt}
                ],
            )

        response = call_api()
        return response.content[0].text
    except Exception as e:
        return f"AI 分析失败: {str(e)}"
