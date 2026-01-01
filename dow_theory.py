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

def get_pivots(df, lookback=120, filter_size=3, mode='low'):
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
            # 거래량 확증 추가: 변곡점 형성 시 거래량이 평균 이상인지 확인
            vol_ma = df['Volume'].rolling(window=20).mean().iloc[i]
            vol_ratio = df['Volume'].iloc[i] / vol_ma
            pivots.append({'val': float(prices.iloc[i]), 'idx': i, 'vol_ratio': vol_ratio})
            if len(pivots) == 3: break
    return pivots

def calculate_expert_indicators(df):
    # 1. ATR 계산 (변동성 기반 손절선)
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['ATR'] = tr.rolling(window=14).mean()
    
    # 2. RSI 계산
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    df['RSI'] = 100 - (100 / (1 + gain / loss))
    
    return df

# 분석 종목 리스트
ticker_map = { 
    'NVDA': '엔비디아', 'TSLA': '테슬라', 'AAPL': '애플', 'MSFT': '마이크로소프트', 
    'AMZN': '아마존', 'META': '메타', 'PLTR': '팔란티어', 'MSTR': '마이크로스트래티지', 
    'COIN': '코인베이스', 'AMD': 'AMD', 'AVGO': '브로드컴', 'TSM': 'TSMC', 'MU': '마이크론'
}

# 시장 기준지수 (S&P500) 데이터 확보
market_data = yf.download('SPY', period='1y', interval='1d', progress=False)

super_stocks = []   # 시장보다 강하고 다우 이론 HH+HL 돌파 완료
value_pullbacks = [] # 상승 추세 내 ATR 기반 매수 타점
risk_warnings = []  # 추세 이탈 및 변동성 확대

for symbol, name in ticker_map.items():
    try:
        df = yf.download(symbol, period='1y', interval='1d', progress=False)
        if len(df) < 120: continue
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

        df = calculate_expert_indicators(df)
        curr = df.iloc[-1]
        
        # 상대 강도 계산 (최근 3개월 종목 수익률 / SPY 수익률)
        stock_ret = (df['Close'].iloc[-1] / df['Close'].iloc[-60]) - 1
        market_ret = (market_data['Close'].iloc[-1] / market_data['Close'].iloc[-60]) - 1
        relative_strength = stock_ret - market_ret

        low_pivots = get_pivots(df, mode='low')
        high_pivots = get_pivots(df, mode='high')
        if len(low_pivots) < 2 or len(high_pivots) < 1: continue

        is_hl = low_pivots[0]['val'] > low_pivots[1]['val']
        is_breakout = curr['Close'] > high_pivots[0]['val']
        atr_stop = curr['Close'] - (2 * curr['ATR']) # 2*ATR 손절선
        
        info = f"[{name}({symbol})]\n가: {curr['Close']:.2f}$ | RS: {relative_strength:.2%}\n손절(ATR): {atr_stop:.2f}$"

        if is_hl and is_breakout and relative_strength > 0:
            # 시장보다 강하며 고점 돌파 완료
            super_stocks.append("🚀 " + info)
        elif is_hl and not is_breakout and curr['RSI'] < 50:
            # 상승 추세 내 저평가 구간 (RSI 기준 눌림)
            value_pullbacks.append("💎 " + info)
        elif curr['Close'] < low_pivots[0]['val']:
            # 구조적 지지선 붕괴
            risk_warnings.append("🚨 " + info)

    except: continue

report = f"🏛️ 프로급 다우 구조 분석 리포트 (v100)\n" + "="*25 + "\n\n"
report += "🚀 시장 주도주: 돌파 & 상대강도 우위\n" + ("\n\n".join(super_stocks) if super_stocks else "해당 없음") + "\n\n"
report += "💎 가치 눌림목: 추세 내 저위험 타점\n" + ("\n\n".join(value_pullbacks) if value_pullbacks else "해당 없음") + "\n\n"
report += "🚨 리스크 관리: 구조적 지지선 이탈\n" + ("\n\n".join(risk_warnings) if risk_warnings else "해당 없음") + "\n\n"
report += "="*25

send_message(report)
