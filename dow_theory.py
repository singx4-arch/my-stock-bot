import yfinance as yf
import pandas as pd
import requests
import os
import numpy as np
from datetime import datetime

token = os.getenv('TELEGRAM_TOKEN')
chat_id = os.getenv('TELEGRAM_CHAT_ID')

def send_message(text):
    if not token or not chat_id: return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    params = {'chat_id': chat_id, 'text': text, 'parse_mode': 'Markdown'}
    requests.get(url, params=params)

def get_structural_pivots(df, lookback=120, filter_size=3, mode='low'):
    pivots = []
    prices = df['Low'] if mode == 'low' else df['High']
    for i in range(len(df) - filter_size - 1, len(df) - lookback, -1):
        if i < filter_size: continue
        is_pivot = True
        for j in range(1, filter_size + 1):
            if mode == 'low':
                if prices.iloc[i] > prices.iloc[i-j] or prices.iloc[i] > prices.iloc[i+j]:
                    is_pivot = False; break
            else:
                if prices.iloc[i] < prices.iloc[i-j] or prices.iloc[i] < prices.iloc[i+j]:
                    is_pivot = False; break
        if is_pivot:
            pivots.append({'val': float(prices.iloc[i]), 'idx': i})
            if len(pivots) == 3: break
    return pivots

def detect_bottom_signal(df, rsi_val):
    lows = df['Low']
    min_60 = lows.iloc[-60:].min()
    is_near_min = (df['Close'].iloc[-1] - min_60) / min_60 < 0.03
    vol_ma = df['Volume'].rolling(window=20).mean()
    vol_spike = any(df['Volume'].iloc[-5:] > vol_ma.iloc[-5:] * 1.5)
    
    pivots = get_structural_pivots(df, lookback=60, filter_size=3, mode='low')
    is_hl = len(pivots) >= 2 and pivots[0]['val'] > pivots[1]['val']
    
    score = 0
    if is_near_min: score += 1
    if rsi_val < 35: score += 1
    if vol_spike: score += 1
    if is_hl: score += 2
    return score >= 3, is_hl

ticker_map = { 
    'NVDA': '엔비디아', 'TSLA': '테슬라', 'AAPL': '애플', 'MSFT': '마이크로소프트', 
    'AMZN': '아마존', 'META': '메타', 'GOOGL': '구글', 'PLTR': '팔란티어', 
    'MSTR': '마이크로스트래티지', 'COIN': '코인베이스', 'AMD': 'AMD', 'NFLX': '넷플릭스', 
    'AVGO': '브로드컴', 'TQQQ': '나스닥3배레버', 'SOXL': '반도체3배레버', 'ARM': 'ARM', 
    'TSM': 'TSMC', 'MU': '마이크론', 'INTC': '인텔', 'SMCI': '슈퍼마이크로', 
    'PYPL': '페이팔', 'COST': '코스트코', 'QCOM': '퀄컴', 'ASML': 'ASML', 
    'MARA': '마라톤디지털', 'VRT': '버티브 홀딩스', 'LLY': '일라이 릴리', 'VST': '비스트라', 
    'GEV': 'GE 베르노바', 'MRVL': '마벨 테크놀로지', 'UBER': '우버', 'APP': '앱러빈'
}

primary_uptrend = []   
secondary_retest = []  
structural_break = []  
bottom_signals = []

for symbol, name in ticker_map.items():
    try:
        df = yf.download(symbol, period='1y', interval='1d', progress=False)
        if len(df) < 120: continue
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

        df['MA20'] = df['Close'].rolling(window=20).mean()
        
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        curr_rsi = float(100 - (100 / (1 + gain / loss)).iloc[-1])
        
        curr_p = float(df['Close'].iloc[-1])
        low_pivots = get_structural_pivots(df, mode='low')
        high_pivots = get_structural_pivots(df, mode='high')

        if len(low_pivots) < 2 or len(high_pivots) < 2: continue

        is_hl = low_pivots[0]['val'] > low_pivots[1]['val']
        is_hh = high_pivots[0]['val'] > high_pivots[1]['val']
        is_gold = curr_p > df['MA20'].iloc[-1]
        
        info = f"[{name} ({symbol})]\n현재가: {curr_p:.2f}$\n직전저점: {low_pivots[0]['val']:.2f}$"

        if is_hh and is_hl and is_gold:
            m = (low_pivots[0]['val'] - low_pivots[1]['val']) / (low_pivots[0]['idx'] - low_pivots[1]['idx'])
            line_val = m * (len(df) - 1 - low_pivots[1]['idx']) + low_pivots[1]['val']
            if (curr_p - line_val) / line_val < 0.025:
                secondary_retest.append("💎 " + info + "\n(리테스트 타점)")
            else:
                primary_uptrend.append("🚀 " + info)
        elif not is_hl and curr_p < low_pivots[0]['val']:
            structural_break.append("🚨 " + info + "\n(지지선 이탈)")

        is_bottom, is_hl_bottom = detect_bottom_signal(df, curr_rsi)
        if is_bottom:
            bottom_signals.append(f"⚓ {name}({symbol}): {'저점 상승 확인' if is_hl_bottom else '매수세 유입'}")

    except: continue

report = f"🏛️ 다우 이론 및 바닥 탐지 통합 리포트\n" + "="*25 + "\n\n"
report += "🚀 제1추세: 상승 확정 (HH+HL)\n" + ("\n\n".join(primary_uptrend) if primary_uptrend else "해당 없음") + "\n\n"
report += "💎 제2반작용: 눌림목 리테스트\n" + ("\n\n".join(secondary_retest) if secondary_retest else "해당 없음") + "\n\n"
report += "⚓ 바닥 포착: 하락 에너지 소멸\n" + ("\n\n".join(bottom_signals) if bottom_signals else "해당 없음") + "\n\n"
report += "🚨 추세 주의: 구조적 이탈\n" + ("\n\n".join(structural_break) if structural_break else "해당 없음") + "\n\n"
report += "="*25

send_message(report)
