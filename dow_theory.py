import yfinance as yf
import pandas as pd
import requests
import os
import numpy as np
from datetime import datetime

# 텔레그램 설정
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
        if len(df) < 100: continue
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

        curr_p = float(df['Close'].iloc[-1])
        low_pivots = get_structural_pivots(df, mode='low')
        high_pivots = get_structural_pivots(df, mode='high')
        if len(low_pivots) < 2 or len(high_pivots) < 1: continue

        support = low_pivots[0]['val']
        dist_to_sup = ((curr_p - support) / support) * 100
        
        is_breakout = curr_p > high_pivots[0]['val'] # 실시간 신고가 갱신 중
        is_hl = low_pivots[0]['val'] > low_pivots[1]['val'] # 저점 마디 상승
        
        info = f"{name}({symbol}): {curr_p:.1f}$ (지지선대비 +{dist_to_sup:.1f}%)"

        # 판별 로직 순서 최적화 (v108)
        if curr_p < support:
            # 1순위: 실시간 지지선 이탈은 예외 없이 위험
            groups['🚨위험'].append(info)
        elif is_breakout:
            # 2순위: 신고가를 뚫고 나가는 종목은 슈퍼 주도주로 인정 (MU 구제 로직)
            groups['🚀슈퍼'].append(info)
        elif is_hl:
            # 3순위: 전고점 아래지만 저점 상승 구조가 유지되면 눌림목
            groups['💎눌림'].append(info)
        else:
            # 4순위: 저점이 낮아졌거나 지지력이 약해진 상태
            groups['🚨위험'].append(info)

    except: continue

report = f"🏛️ 다우 구조 분석 리포트 (v108)\n" + "="*25 + "\n\n"
for key, stocks in groups.items():
    report += f"{key} 종목군\n"
    report += "\n".join(stocks) if stocks else "해당 없음"
    report += "\n\n" + "-"*20 + "\n\n"
report += "="*25

send_message(report)
