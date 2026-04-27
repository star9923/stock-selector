"""
fundamental.py - 基本面筛选模块（优化版）
"""
import pandas as pd
import numpy as np


def score_fundamental(realtime: dict, financial: dict) -> dict:
    """
    基本面打分，返回详细得分字典
    :param realtime: 实时行情字段 (pe, pb, market_cap, turnover_rate, pct_change)
    :param financial: 财务指标字段 (roe, debt_ratio)
    """
    valuation_score = 0
    profitability_score = 0
    growth_score = 0
    liquidity_score = 0

    # ========== 估值得分 (30分) ==========
    pe = _safe_float(realtime.get("pe"))
    pb = _safe_float(realtime.get("pb"))

    # PE 估值
    if pe > 0:
        if pe <= 15:
            valuation_score += 15
        elif pe <= 25:
            valuation_score += 10
        elif pe <= 40:
            valuation_score += 5
        elif pe > 80:
            valuation_score -= 5

    # PB 估值
    if pb > 0:
        if pb <= 1.5:
            valuation_score += 15
        elif pb <= 2.5:
            valuation_score += 10
        elif pb <= 4:
            valuation_score += 5

    # ========== 盈利能力得分 (30分) ==========
    roe = _safe_float(financial.get("roe"))
    debt_ratio = _safe_float(financial.get("debt_ratio"))

    # ROE（净资产收益率）
    if roe >= 20:
        profitability_score += 15
    elif roe >= 15:
        profitability_score += 12
    elif roe >= 10:
        profitability_score += 8
    elif roe >= 5:
        profitability_score += 4
    elif roe < 0:
        profitability_score -= 10

    # 资产负债率（越低越好）
    if debt_ratio > 0:
        if debt_ratio <= 30:
            profitability_score += 15
        elif debt_ratio <= 50:
            profitability_score += 10
        elif debt_ratio <= 70:
            profitability_score += 5

    # ========== 成长性得分 (20分) ==========
    # 近期涨幅（短期动量）
    pct_change = _safe_float(realtime.get("pct_change"))
    if -2 <= pct_change <= 5:
        growth_score += 10
    elif 5 < pct_change <= 9:
        growth_score += 7
    elif pct_change < -5:
        growth_score -= 5

    # 市值规模（偏好中大盘）
    market_cap = _safe_float(realtime.get("market_cap"))
    if market_cap > 0:
        if 50e9 <= market_cap <= 500e9:
            growth_score += 10
        elif 20e9 <= market_cap < 50e9:
            growth_score += 6
        elif market_cap >= 500e9:
            growth_score += 4

    # ========== 流动性得分 (20分) ==========
    turnover_rate = _safe_float(realtime.get("turnover_rate"))
    
    # 换手率适中
    if 1 <= turnover_rate <= 5:
        liquidity_score += 12
    elif 5 < turnover_rate <= 10:
        liquidity_score += 8
    elif 0.5 <= turnover_rate < 1:
        liquidity_score += 4
    elif turnover_rate > 20:
        liquidity_score -= 5

    # 市值流动性（大市值 + 适中换手）
    if market_cap > 50e9 and 1 <= turnover_rate <= 8:
        liquidity_score += 8

    total = valuation_score + profitability_score + growth_score + liquidity_score

    return {
        "total": min(total, 100.0),
        "valuation": valuation_score,
        "profitability": profitability_score,
        "growth": growth_score,
        "liquidity": liquidity_score,
    }


def filter_basic(df_realtime: pd.DataFrame) -> pd.DataFrame:
    """
    基础过滤：去掉 ST、退市风险、市值过小、异常股票
    """
    if df_realtime.empty:
        return df_realtime

    # 去掉 ST / *ST / 退市
    if "name" in df_realtime.columns:
        df_realtime = df_realtime[
            ~df_realtime["name"].str.contains("ST|退", na=False, regex=True)
        ]

    # 流通市值 > 20亿（如果没有市值数据，用成交额估算）
    if "float_cap" in df_realtime.columns:
        float_cap = pd.to_numeric(df_realtime["float_cap"], errors="coerce").fillna(0)
        turnover = pd.to_numeric(df_realtime["turnover"], errors="coerce").fillna(0)
        estimated_cap = float_cap.where(float_cap > 0, turnover * 100)
        df_realtime = df_realtime[estimated_cap >= 2e9]

    # 价格 > 1 元（去仙股）
    if "price" in df_realtime.columns:
        df_realtime = df_realtime[
            pd.to_numeric(df_realtime["price"], errors="coerce").fillna(0) >= 1.0
        ]

    # 去掉涨停/跌停（避免追高杀跌）
    if "pct_change" in df_realtime.columns:
        pct = pd.to_numeric(df_realtime["pct_change"], errors="coerce").fillna(0)
        df_realtime = df_realtime[(pct > -9.5) & (pct < 9.5)]

    # 去掉停牌股（成交量为 0）
    if "volume" in df_realtime.columns:
        df_realtime = df_realtime[
            pd.to_numeric(df_realtime["volume"], errors="coerce").fillna(0) > 0
        ]

    # 成交额 > 0 且 > 1000万（非交易时段成交额可能为0，需要特殊处理）
    if "turnover" in df_realtime.columns:
        turnover = pd.to_numeric(df_realtime["turnover"], errors="coerce").fillna(0)
        df_realtime = df_realtime[(turnover > 0) & (turnover > 1e7)]

    return df_realtime.reset_index(drop=True)


def _safe_float(val) -> float:
    """安全转换为 float"""
    try:
        if val is None or val == "" or pd.isna(val):
            return 0.0
        return float(val)
    except (TypeError, ValueError):
        return 0.0
