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
# 지수 및 레버리지
    'QQQ': '나스닥100', 'TQQQ': '나스닥3배', 'SOXL': '반도체3배',
    # 반도체 및 장비/소재 (코닝 추가됨)
    'NVDA': '엔비디아', 'TSM': 'TSMC', 'AVGO': '브로드컴', 'ASML': 'ASML', 
    'AMD': 'AMD', 'MU': '마이크론', 'GLW': '코닝', 'LRCX': '램리서치', 'AMAT': '어플라이드',
    # AI 및 빅테크
    'MSFT': '마이크로소프트', 'GOOGL': '알파벳', 'AMZN': '아마존', 'META': '메타', 
    'AAPL': '애플', 'PLTR': '팔란티어', 'ORCL': '오라클',
    # 유망 기술 및 인프라
    'IONQ': '아이온큐', 'TSLA': '테슬라', 'MSTR': 'MSTR', 'COIN': '코인베이스',
    'VST': '비스트라', 'CEG': '컨스텔레이션', 'ENPH': '엔페이즈'
}

# 종목군 정의 (키 이름을 박스권으로 통일했다이다)
groups = {
    '🚀슈퍼': [],
    '💎눌림': [],
    '⚠️눌림(하락추세)': [],
    '📦박스권': [],
    '🚨위험': []
}

for symbol, name in ticker_map.items():
    try:
        df = yf.download(symbol, period='1y', interval='1d', progress=False)
        if len(df) < 120: continue
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

        curr_p = float(df['Close'].iloc[-1])
        
        df['SMMA7'] = df['Close'].ewm(alpha=1/7, adjust=False).mean()
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['MA60'] = df['Close'].rolling(window=60).mean()
        
        curr_smma7 = float(df['SMMA7'].iloc[-1])
        curr_ma20 = float(df['MA20'].iloc[-1])
        
        # 크로스 판정 로직이다
        gap_ratio = (curr_smma7 - curr_ma20) / curr_ma20
        
        # 골든크로스: 7SMMA가 20MA보다 높고 이격률이 0.15%를 초과할 때이다
        is_golden_cross = (curr_smma7 > curr_ma20) and (gap_ratio > 0.0015)
        # 데드크로스: 7SMMA가 아래에 있거나 이격률이 0.15% 이내로 좁혀졌을 때이다
        is_dead_cross = (curr_smma7 < curr_ma20) or (0 <= gap_ratio <= 0.0015)
        
        low_pivots = get_structural_pivots(df, mode='low')
        high_pivots = get_structural_pivots(df, mode='high')
        if len(low_pivots) < 2 or len(high_pivots) < 1: continue

        support = low_pivots[0]['val']
        dist_to_sup = ((curr_p - support) / support) * 100
        
        is_breakout = curr_p > high_pivots[0]['val']
        is_hl = low_pivots[0]['val'] > low_pivots[1]['val']
        
        # 기본 정보 구성이다
        info = f"{name}({symbol}): {curr_p:.1f}$ (+{dist_to_sup:.1f}%)"
        
        # 크로스 상태 메시지 추가이다
        if is_golden_cross:
            info += " (골든크로스/상승 추세)"
        elif is_dead_cross:
            info += " (데드크로스/하락 가능성 큼)"

        # 판별 로직(v117)이다
        if curr_p < support:
            groups['🚨위험'].append(info)
        elif is_hl:
            if is_dead_cross:
                groups['⚠️눌림(하락추세)'].append(info + " (주의)")
            else:
                groups['💎눌림'].append(info + " 🔥")
        elif is_breakout and is_golden_cross:
            groups['🚀슈퍼'].append(info + " 🔥")
        else:
            # 박스권/대기 종목군으로 분류한다이다
            groups['📦박스권'].append(info)

    except: continue

report = f"🏛️ 다우 구조 및 데드크로스 분석 리포트 (v117)\n" + "="*25 + "\n\n"
report += "💡 가이드: 🔥는 정배열 상태, ⚠️눌림(하락추세)는 구조는 살아있으나 지표가 둔화된 상태이다.\n\n"

order = ['🚀슈퍼', '💎눌림', '⚠️눌림(하락추세)', '📦박스권', '🚨위험']
for key in order:
    stocks = groups[key]
    report += f"{key} 종목군\n"
    report += "\n".join(stocks) if stocks else "해당 없음"
    report += "\n\n" + "-"*20 + "\n\n"

report += "="*25
send_message(report)
