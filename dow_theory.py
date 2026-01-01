import yfinance as yf
import pandas as pd
import requests
import os
import numpy as np
from datetime import datetime

# 텔레그램 설정이다
# 환경 변수 대신 직접 입력하려면 '' 사이에 값을 넣으면 된다
token = os.getenv('TELEGRAM_TOKEN') or '7971022798:AAFGQR1zxdCq1urZKgdRzjjsvr3Lt6T9y1I'
chat_id = os.getenv('TELEGRAM_CHAT_ID')

def send_message(text):
    if not token or not chat_id: return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    params = {'chat_id': chat_id, 'text': text, 'parse_mode': 'Markdown'}
    requests.get(url, params=params)

def get_structural_pivots(df, lookback=120, filter_size=3, mode='low'):
    # 전문가들이 사용하는 구조적 마디 찾기 로직이다
    pivots = []
    prices = df['Low'] if mode == 'low' else df['High']
    # 최신 데이터부터 역순으로 탐색한다
    for i in range(len(df) - filter_size - 1, len(df) - lookback, -1):
        if i < filter_size: continue
        is_pivot = True
        # 좌우 filter_size만큼의 캔들보다 높거나 낮은지 확인한다
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

# 분석할 종목 리스트이다
ticker_map = { 
    'NVDA': '엔비디아', 'TSLA': '테슬라', 'AAPL': '애플', 'MSFT': '마이크로소프트', 
    'AMZN': '아마존', 'META': '메타', 'PLTR': '팔란티어', 'MSTR': '마이크로스트래티지', 
    'COIN': '코인베이스', 'AMD': 'AMD', 'AVGO': '브로드컴', 'TSM': 'TSMC', 'MU': '마이크론'
}

uptrend_stocks = []   # 다우 이론상 상승 확정 (HH+HL)
pullback_stocks = []  # 상승 추세 내 눌림목 (Secondary Reaction)
break_stocks = []     # 추세 훼손 (지지선 이탈)

for symbol, name in ticker_map.items():
    try:
        df = yf.download(symbol, period='1y', interval='1d', progress=False)
        if len(df) < 100: continue
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

        curr_p = float(df['Close'].iloc[-1])
        
        # 1. 다우 이론 마디 추출이다
        low_pivots = get_structural_pivots(df, mode='low')
        high_pivots = get_structural_pivots(df, mode='high')

        if len(low_pivots) < 2 or len(high_pivots) < 1: continue

        # 2. 추세 판별 로직이다
        # 저점이 높아지고 있는가 (Higher Low)
        is_hl = low_pivots[0]['val'] > low_pivots[1]['val']
        # 현재가가 전고점을 돌파했는가 (Higher High)
        is_hh = curr_p > high_pivots[0]['val']
        
        info = f"[{name}({symbol})]\n현재가: {curr_p:.2f}$\n직전저점: {low_pivots[0]['val']:.2f}$"

        if is_hl and is_hh:
            uptrend_stocks.append("🚀 " + info)
        elif is_hl and not is_hh:
            # 저점은 높였으나 아직 고점을 못 뚫은 눌림목 구간이다
            pullback_stocks.append("💎 " + info)
        elif curr_p < low_pivots[0]['val']:
            # 가장 최근의 지지선을 깨고 내려간 상태이다
            break_stocks.append("🚨 " + info)

    except: continue

# 리포트 생성 및 전송이다
report = f"🏛️ 다우 이론 기반 구조 분석 리포트\n" + "="*25 + "\n\n"
report += "🚀 상승 확정: 고점 및 저점 동시 상승\n" + ("\n\n".join(uptrend_stocks) if uptrend_stocks else "해당 없음") + "\n\n"
report += "💎 눌림목: 저점 상승 중 고점 돌파 대기\n" + ("\n\n".join(pullback_stocks) if pullback_stocks else "해당 없음") + "\n\n"
report += "🚨 추세 이탈: 직전 저점 붕괴 주의\n" + ("\n\n".join(break_stocks) if break_stocks else "해당 없음") + "\n\n"
report += "="*25

send_message(report)
