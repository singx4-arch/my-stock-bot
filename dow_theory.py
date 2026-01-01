import yfinance as yf
import pandas as pd
import requests
import os
import numpy as np
from datetime import datetime

token = os.getenv('TELEGRAM_TOKEN') or '7971022798:AAFGQR1zxdCq1urZKgdRzjjsvr3Lt6T9y1I'
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

ticker_map = { 
    'NVDA': '엔비디아', 'TSLA': '테슬라', 'AAPL': '애플', 'MSFT': '마이크로소프트', 
    'AMZN': '아마존', 'META': '메타', 'PLTR': '팔란티어', 'MSTR': '마이크로스트래티지', 
    'COIN': '코인베이스', 'AMD': 'AMD', 'AVGO': '브로드컴', 'TSM': 'TSMC', 'MU': '마이크론'
}

uptrend_stocks = []   # 🚀 찐 상승 (HH + HL + 현재가 전고 돌파)
pullback_stocks = []  # 💎 진짜 눌림 (HL 유지 + 현재가 지지선 위)
break_stocks = []     # 🚨 구조적 붕괴 (현재가 < 직전저점 OR 저점 하락)

for symbol, name in ticker_map.items():
    try:
        df = yf.download(symbol, period='1y', interval='1d', progress=False)
        if len(df) < 100: continue
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

        curr_p = float(df['Close'].iloc[-1])
        low_pivots = get_structural_pivots(df, mode='low')
        high_pivots = get_structural_pivots(df, mode='high')

        if len(low_pivots) < 2 or len(high_pivots) < 1: continue

        # 전문가 필터 1: 현재 가격이 직전 지지선을 깼는가? (가장 중요)
        is_immediate_break = curr_p < low_pivots[0]['val']
        # 전문가 필터 2: 저점이 낮아지고 있는가? (LL - Lower Low)
        is_ll = low_pivots[0]['val'] < low_pivots[1]['val']
        
        # 상승/눌림 조건
        is_hl = low_pivots[0]['val'] > low_pivots[1]['val']
        is_hh = curr_p > high_pivots[0]['val']
        
        info = f"[{name}({symbol})]\n현재가: {curr_p:.2f}$\n직전저점: {low_pivots[0]['val']:.2f}$"

        # 판별 순서 조정: 이탈을 가장 먼저 확인함
        if is_immediate_break or is_ll:
            # MSTR처럼 꼬라박는 상황을 여기서 잡아냄
            break_stocks.append("🚨 " + info)
        elif is_hl and is_hh:
            uptrend_stocks.append("🚀 " + info)
        elif is_hl and not is_hh:
            pullback_stocks.append("💎 " + info)

    except: continue

report = f"🏛️ 다우 구조 분석 리포트 (v102)\n" + "="*25 + "\n\n"
report += "🚀 상승 확정: 강한 추세\n" + ("\n\n".join(uptrend_stocks) if uptrend_stocks else "해당 없음") + "\n\n"
report += "💎 눌림목: 지지선 위 조정\n" + ("\n\n".join(pullback_stocks) if pullback_stocks else "해당 없음") + "\n\n"
report += "🚨 추세 이탈: 지지선 붕괴/하락세\n" + ("\n\n".join(break_stocks) if break_stocks else "해당 없음") + "\n\n"
report += "="*25

send_message(report)
