import yfinance as yf
import pandas as pd
import requests
import os
import json
import numpy as np
from datetime import datetime

token = os.getenv('TELEGRAM_TOKEN') or '7971022798:AAFGQR1zxdCq1urZKgdRzjjsvr3Lt6T9y1I'
chat_id = os.getenv('TELEGRAM_CHAT_ID')

def send_message(text):
    if not token or not chat_id: return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    params = {'chat_id': chat_id, 'text': text, 'disable_notification': 'true'}
    try: requests.get(url, params=params, timeout=10)
    except: pass

def calculate_wilder_rsi(series, period=14):
    delta = series.diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    avg_gain = up.ewm(com=period-1, min_periods=period).mean()
    avg_loss = down.ewm(com=period-1, min_periods=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def detect_divergence_only(df, rsi):
    lows = df['Low'].values
    highs = df['High'].values
    volumes = df['Volume'].values
    length = len(df)
    
    valleys, peaks = [], []
    in_low, in_high = False, False
    curr_v, curr_p = None, None

    for i in range(max(0, length - 120), length):
        r = rsi.iloc[i]
        if r < 35:
            if not in_low:
                in_low = True
                curr_v = {'idx': i, 'rsi': r, 'price': lows[i], 'vol': volumes[i]}
            elif r < curr_v['rsi']:
                curr_v = {'idx': i, 'rsi': r, 'price': lows[i], 'vol': volumes[i]}
        else:
            if in_low: valleys.append(curr_v); in_low = False
            
        if r > 65:
            if not in_high:
                in_high = True
                curr_p = {'idx': i, 'rsi': r, 'price': highs[i], 'vol': volumes[i]}
            elif r > curr_p['rsi']:
                curr_p = {'idx': i, 'rsi': r, 'price': highs[i], 'vol': volumes[i]}
        else:
            if in_high: peaks.append(curr_p); in_high = False

    msg = ""
    bull_score, bear_score = 0, 0

    if len(valleys) >= 2:
        v1, v2 = valleys[-2], valleys[-1]
        if (v2['idx'] - v1['idx']) < 60:
            is_conf = v2['vol'] < v1['vol']
            icon = "⭐" if is_conf else "⚠️"
            txt = "(신뢰: 매도 소진)" if is_conf else "(거짓 신호임)"
            if v2['price'] < v1['price'] and v2['rsi'] > v1['rsi']:
                msg += f"{icon} 일반 상승 다이버전스 {txt}\n"
                bull_score += 2 if is_conf else 1
            elif v2['price'] > v1['price'] and v2['rsi'] < v1['rsi']:
                msg += f"{icon} 히든 상승 다이버전스 {txt}\n"
                bull_score += 2 if is_conf else 1

    if len(peaks) >= 2:
        p1, p2 = peaks[-2], peaks[-1]
        if (p2['idx'] - p1['idx']) < 60:
            is_conf = p2['vol'] < p1['vol']
            icon = "⭐" if is_conf else "⚠️"
            txt = "(신뢰: 매수 약화)" if is_conf else "(거짓 신호임)"
            if p2['price'] > p1['price'] and p2['rsi'] < p1['rsi']:
                msg += f"{icon} 일반 하락 다이버전스 {txt}\n"
                bear_score += 2 if is_conf else 1
            elif p2['price'] < p1['price'] and p2['rsi'] > p1['rsi']:
                msg += f"{icon} 히든 하락 다이버전스 {txt}\n"
                bear_score += 2 if is_conf else 1

    verdict = ""
    if bull_score > bear_score:
        verdict = "✅ [상승 우위] 바닥 매수 에너지가 강력하다이다." if bull_score >= 2 else "🤔 [상승 관망] 힘이 부족하다이다."
    elif bear_score > bull_score:
        verdict = "🚨 [하락 우위] 천장 매도 압력이 강력하다이다." if bear_score >= 2 else "⚠️ [하락 주의] 조정 가능성이 높다이다."
    elif bull_score > 0 and bull_score == bear_score:
        verdict = "⚖️ [중립/혼조] 상승과 하락 신호 대립 중이다이다."

    return msg, verdict

def analyze_ticker(ticker):
    try:
        df = yf.download(ticker, period='1y', interval='1d', progress=False)
        if len(df) < 100: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

        cp = df['Close'].iloc[-1]
        rsi9 = calculate_wilder_rsi(df['Close'], 9)
        div_msg, verdict = detect_divergence_only(df, rsi9)
        
        if not div_msg: return None

        res = f"🏛️ [{ticker} 다이버전스 리포트]이다\n현재가: {cp:.2f}$\n--------------------\n"
        res += f"📢 판정: {verdict}\n\n🔍 상세 신호:\n{div_msg}--------------------\n"
        res += f"RSI(9d): {rsi9.iloc[-1]:.2f}\n※ ⭐는 확증 신호, ⚠️는 거짓 신호이다."
        return res
    except: return None

def main():
    # 섹터별 강화된 티커 리스트이다
    tickers = [
        # 지수 및 레버리지
        'QQQ', 'TQQQ', 'SOXL', 'SPY',
        # 반도체 및 장비 (재혁이 전공 관련)
        'NVDA', 'TSM', 'AVGO', 'ASML', 'AMD', 'MU', 'AMAT', 'LRCX', 'QCOM', 'ARM', 'SMCI', 'INTC', 'KLAC',
        # 빅테크 및 AI 소프트웨어
        'MSFT', 'AAPL', 'AMZN', 'META', 'GOOGL', 'TSLA', 'PLTR', 'ORCL', 'NOW', 'CRM', 'ADBE', 'IBM', 'PANW', 'SNPS',
        # 에너지 및 차세대 인프라
        'VST', 'CEG', 'GEV', 'OKLO', 'SMR', 'XLE', 'NLR', 'NEE', 'DUK',
        # 소재 및 기타 기술주
        'ALB', 'SQM', 'GLW', 'NFLX', 'UBER', 'SHOP', 'COIN', 'MSTR'
    ]
    
    for t in tickers:
        report = analyze_ticker(t)
        if report:
            send_message(report)

if __name__ == "__main__":
    main()
