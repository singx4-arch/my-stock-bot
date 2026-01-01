import yfinance as yf
import pandas as pd
import requests
import os
import numpy as np
from datetime import datetime

# 텔레그램 설정이다
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

groups = {'🚀슈퍼': [], '💎눌림': [], '📦대기': [], '🚨위험': []}

for symbol, name in ticker_map.items():
    try:
        df = yf.download(symbol, period='1y', interval='1d', progress=False)
        if len(df) < 120: continue
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

        curr_p = float(df['Close'].iloc[-1])
        
        # 이동평균선 계산 (7SMMA, 20MA, 60MA)이다
        df['SMMA7'] = df['Close'].ewm(alpha=1/7, adjust=False).mean()
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['MA60'] = df['Close'].rolling(window=60).mean()
        
        curr_smma7 = float(df['SMMA7'].iloc[-1])
        curr_ma20 = float(df['MA20'].iloc[-1])
        curr_ma60 = float(df['MA60'].iloc[-1])
        
        # 완전 정배열 여부 확인이다
        is_bullish_alignment = curr_smma7 > curr_ma20 > curr_ma60
        # 데드크로스 여부 확인이다
        is_dead_cross = curr_smma7 < curr_ma20
        
        low_pivots = get_structural_pivots(df, mode='low')
        high_pivots = get_structural_pivots(df, mode='high')
        if len(low_pivots) < 2 or len(high_pivots) < 1: continue

        support = low_pivots[0]['val']
        dist_to_sup = ((curr_p - support) / support) * 100
        
        is_breakout = curr_p > high_pivots[0]['val']
        is_hl = low_pivots[0]['val'] > low_pivots[1]['val']
        
        # 정보 텍스트 구성이다
        info = f"{name}({symbol}): {curr_p:.1f}$ (+{dist_to_sup:.1f}%)"
        if is_bullish_alignment:
            info += " 🔥" # 상승 에너지가 아주 강함이다

        # 판별 로직 (v111)이다
        if curr_p < support:
            groups['🚨위험'].append(info)
        elif is_breakout:
            groups['🚀슈퍼'].append(info)
        elif is_hl:
            if is_dead_cross:
                info += " (하락 가능성 큼)"
            groups['💎눌림'].append(info)
        else:
            groups['📦대기'].append(info)

    except: continue

report = f"🏛️ 다우 구조 및 상승 에너지 분석 리포트 (v111)\n" + "="*25 + "\n\n"
report += "💡 가이드: 🔥 표시는 7/20/60일 이평선이 완전 정배열인 종목이다.\n\n"

for key, stocks in groups.items():
    report += f"{key} 종목군\n"
    report += "\n".join(stocks) if stocks else "해당 없음"
    report += "\n\n" + "-"*20 + "\n\n"

report += "="*25
send_message(report)
