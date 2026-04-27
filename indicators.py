"""
indicators.py - 技术指标计算模块（优化版）
"""
import pandas as pd
import numpy as np


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """在日线 DataFrame 上计算常用技术指标"""
    if df.empty or len(df) < 30:
        return df

    # 转换为数值类型
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df["high"] = pd.to_numeric(df["high"], errors="coerce")
    df["low"] = pd.to_numeric(df["low"], errors="coerce")
    df["open"] = pd.to_numeric(df["open"], errors="coerce")
    df["volume"] = pd.to_numeric(df["volume"], errors="coerce")
    
    # 删除无效行
    df = df.dropna(subset=["close", "high", "low", "volume"])
    if len(df) < 30:
        return df
    
    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]

    # 均线
    df["ma5"]  = close.rolling(5).mean()
    df["ma10"] = close.rolling(10).mean()
    df["ma20"] = close.rolling(20).mean()
    df["ma60"] = close.rolling(60).mean()

    # MACD
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    df["macd_dif"] = ema12 - ema26
    df["macd_dea"] = df["macd_dif"].ewm(span=9, adjust=False).mean()
    df["macd_bar"] = (df["macd_dif"] - df["macd_dea"]) * 2

    # RSI (14)
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    df["rsi14"] = 100 - (100 / (1 + rs))

    # KDJ
    low_min  = low.rolling(9).min()
    high_max = high.rolling(9).max()
    rsv = (close - low_min) / (high_max - low_min + 1e-9) * 100
    df["kdj_k"] = rsv.ewm(com=2, adjust=False).mean()
    df["kdj_d"] = df["kdj_k"].ewm(com=2, adjust=False).mean()
    df["kdj_j"] = 3 * df["kdj_k"] - 2 * df["kdj_d"]

    # 布林带 (20, 2)
    df["boll_mid"]   = close.rolling(20).mean()
    boll_std         = close.rolling(20).std()
    df["boll_upper"] = df["boll_mid"] + 2 * boll_std
    df["boll_lower"] = df["boll_mid"] - 2 * boll_std

    # 成交量均线
    df["vol_ma5"]  = volume.rolling(5).mean()
    df["vol_ma20"] = volume.rolling(20).mean()

    # 涨跌幅
    df["pct_change"] = close.pct_change() * 100

    # ATR (波动率)
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df["atr14"] = tr.rolling(14).mean()

    # 动量指标
    df["momentum_5"]  = close.pct_change(5) * 100
    df["momentum_10"] = close.pct_change(10) * 100
    df["momentum_20"] = close.pct_change(20) * 100

    df = df.reset_index(drop=True)
    return df


def score_technical(df: pd.DataFrame) -> dict:
    """
    对单只股票技术面打分，返回详细得分字典
    """
    if df.empty or len(df) < 30:
        return {"total": 0.0, "trend": 0, "momentum": 0, "volume": 0, "risk": 0}

    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else latest
    
    trend_score = 0
    momentum_score = 0
    volume_score = 0
    risk_score = 0

    # ========== 趋势得分 (25分) ==========
    close = latest["close"]
    mas = [latest.get("ma5"), latest.get("ma10"), latest.get("ma20"), latest.get("ma60")]
    
    if all(pd.notna(m) for m in mas):
        # 多头排列
        if mas[0] > mas[1] > mas[2] > mas[3]:
            trend_score += 12
        elif mas[0] > mas[1] > mas[2]:
            trend_score += 8
        elif mas[0] > mas[2]:
            trend_score += 4
        
        # 价格在均线之上
        if close > mas[2]:  # 在 MA20 之上
            trend_score += 6
        
        # 均线发散度（趋势强度）
        if mas[0] > 0:
            divergence = (mas[0] - mas[3]) / mas[0] * 100
            if divergence > 5:
                trend_score += 5
            elif divergence > 2:
                trend_score += 2

    # ========== 动量得分 (25分) ==========
    # MACD 金叉且柱状图放大
    macd_bar = latest.get("macd_bar")
    macd_bar_prev = prev.get("macd_bar")
    macd_dif = latest.get("macd_dif")
    
    if pd.notna(macd_bar) and pd.notna(macd_dif):
        if macd_bar > 0 and macd_dif > 0:
            momentum_score += 8
            # 柱状图放大
            if pd.notna(macd_bar_prev) and macd_bar > macd_bar_prev:
                momentum_score += 3
    
    # RSI 健康区间
    rsi = latest.get("rsi14")
    if pd.notna(rsi):
        if 30 <= rsi <= 70:  # 正常区间
            momentum_score += 8
        elif rsi > 80:  # 严重超买，扣分
            momentum_score -= 3
    
    # 多周期动量一致性
    mom5 = latest.get("momentum_5")
    mom10 = latest.get("momentum_10")
    mom20 = latest.get("momentum_20")
    
    if all(pd.notna(m) for m in [mom5, mom10, mom20]):
        if mom5 > 0 and mom10 > 0 and mom20 > 0:  # 多周期向上
            momentum_score += 4

    # ========== 量能得分 (20分) ==========
    vol = latest.get("volume")
    vol_ma5 = latest.get("vol_ma5")
    vol_ma20 = latest.get("vol_ma20")
    pct_change = latest.get("pct_change")
    
    if pd.notna(vol) and pd.notna(vol_ma5) and vol_ma5 > 0:
        vol_ratio = vol / vol_ma5
        
        # 放量上涨
        if pd.notna(pct_change) and pct_change > 0:
            if vol_ratio >= 2.0:
                volume_score += 10
            elif vol_ratio >= 1.5:
                volume_score += 6
            elif vol_ratio >= 1.0:
                volume_score += 3
        
        # 缩量下跌（健康调整）
        elif pd.notna(pct_change) and pct_change < 0:
            if vol_ratio < 0.8:
                volume_score += 3
    
    # 量能趋势
    if pd.notna(vol_ma5) and pd.notna(vol_ma20) and vol_ma20 > 0:
        if vol_ma5 > vol_ma20:  # 量能放大趋势
            volume_score += 3

    # ========== 风险控制 (10分) ==========
    # 波动率适中
    atr = latest.get("atr14")
    if pd.notna(atr) and close > 0:
        atr_pct = (atr / close) * 100
        if 1 <= atr_pct <= 5:  # 波动适中
            risk_score += 5
        elif atr_pct > 10:  # 波动过大
            risk_score -= 3
    
    # 布林带位置
    boll_upper = latest.get("boll_upper")
    boll_lower = latest.get("boll_lower")
    if pd.notna(boll_upper) and pd.notna(boll_lower):
        if close < boll_upper and close > boll_lower:  # 在轨道内
            risk_score += 5

    total = trend_score + momentum_score + volume_score + risk_score
    
    return {
        "total": min(total, 100.0),
        "trend": trend_score,
        "momentum": momentum_score,
        "volume": volume_score,
        "risk": risk_score,
    }
