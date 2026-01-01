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

uptrend_stocks = []   # 🚀 주도주: HH + HL + 20일선 위
pullback_stocks = []  # 💎 기회주: 조정 중이나 20일선/지지선 방어
risk_stocks = []      # 🚨 위험주: 지지선 완전 붕괴 (MSTR 같은 케이스)

for symbol, name in ticker_map.items():
    try:
        df = yf.download(symbol, period='1y', interval='1d', progress=False)
        if len(df) < 100: continue
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

        curr_p = float(df['Close'].iloc[-1])
        df['MA20'] = df['Close'].rolling(window=20).mean()
        curr_ma20 = float(df['MA20'].iloc[-1])
        
        low_pivots = get_structural_pivots(df, mode='low')
        high_pivots = get_structural_pivots(df, mode='high')

        if len(low_pivots) < 2 or len(high_pivots) < 1: continue

        # 봇의 핵심 로직: 지지선 붕괴 여부와 이평선 위치를 동시에 판단한다
        # 1. 최악의 상황: 직전 저점 마디를 실시간으로 뚫고 내려감 (MSTR 케이스)
        is_structural_break = curr_p < low_pivots[0]['val']
        # 2. 상승 구조 확인 (저점 상승)
        is_hl = low_pivots[0]['val'] > low_pivots[1]['val']
        # 3. 고점 돌파 확인 (전고점 갱신)
        is_hh = curr_p > high_pivots[0]['val']
        # 4. 이평선 지지 (추세 방패)
        is_above_ma20 = curr_p > curr_ma20

        info = f"[{name}({symbol})]\n가: {curr_p:.2f}$ | 지지: {low_pivots[0]['val']:.2f}$"

        if is_structural_break:
            # 추세가 완전히 박살 난 경우이다
            risk_stocks.append("🚨 " + info)
        elif is_above_ma20:
            # 주가가 20일선 위에 있으면 구조적 우위를 인정한다
            if is_hh:
                uptrend_stocks.append("🚀 " + info)
            else:
                pullback_stocks.append("💎 " + info)
        elif is_hl:
            # 20일선 아래지만 저점 마디는 지키고 있는 중이다
            pullback_stocks.append("📦 " + info + "\n(20일선 회복 대기)")
        else:
            # 저점이 낮아지고 있고 20일선도 아래에 있다
            risk_stocks.append("🚨 " + info)

    except: continue

report = f"🏛️ 다우 추세 분석 리포트 (v103)\n" + "="*25 + "\n\n"
report += "🚀 상승 확정: 주도주 그룹\n" + ("\n\n".join(uptrend_stocks) if uptrend_stocks else "해당 없음") + "\n\n"
report += "💎 조정/기회: 눌림목 및 박스권\n" + ("\n\n".join(pullback_stocks) if pullback_stocks else "해당 없음") + "\n\n"
report += "🚨 추세 이탈: 위험/관망\n" + ("\n\n".join(risk_stocks) if risk_stocks else "해당 없음") + "\n\n"
report += "="*25

send_message(report)
