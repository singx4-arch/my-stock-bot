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
    # 마크다운 대신 일반 텍스트 모드로 가독성을 조절한다이다
    params = {'chat_id': chat_id, 'text': text}
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
    'QQQ': '나스닥100', 'TQQQ': '나스닥3배', 'SOXL': '반도체3배',
    'NVDA': '엔비디아', 'TSM': 'TSMC', 'AVGO': '브로드컴', 'ASML': 'ASML', 
    'AMD': 'AMD', 'MU': '마이크론', 'GLW': '코닝', 'LRCX': '램리서치', 'AMAT': '어플라이드',
    'MSFT': '마이크로소프트', 'GOOGL': '알파벳', 'AMZN': '아마존', 'META': '메타', 
    'AAPL': '애플', 'PLTR': '팔란티어', 'ORCL': '오라클',
    'IONQ': '아이온큐', 'TSLA': '테슬라', 'MSTR': 'MSTR', 'COIN': '코인베이스',
    'VST': '비스트라', 'CEG': '컨스텔레이션', 'ENPH': '엔페이즈'
}

groups = {
    '🚀 슈퍼 종목군': [],
    '💎 눌림 종목군': [],
    '⚠️ 눌림(주의)': [],
    '📦 박스권/대기': [],
    '🚨 위험 종목군': []
}

for symbol, name in ticker_map.items():
    try:
        df = yf.download(symbol, period='1y', interval='1d', progress=False)
        if len(df) < 120: continue
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

        curr_p = float(df['Close'].iloc[-1])
        df['SMMA7'] = df['Close'].ewm(alpha=1/7, adjust=False).mean()
        df['MA20'] = df['Close'].rolling(window=20).mean()
        
        curr_smma7 = float(df['SMMA7'].iloc[-1])
        curr_ma20 = float(df['MA20'].iloc[-1])
        
        gap_ratio = (curr_smma7 - curr_ma20) / curr_ma20
        is_golden = (curr_smma7 > curr_ma20) and (gap_ratio > 0.0015)
        is_dead = (curr_smma7 < curr_ma20) or (0 <= gap_ratio <= 0.0015)
        
        low_pivots = get_structural_pivots(df, mode='low')
        high_pivots = get_structural_pivots(df, mode='high')
        if len(low_pivots) < 2 or len(high_pivots) < 1: continue

        support = low_pivots[0]['val']
        dist_to_sup = ((curr_p - support) / support) * 100
        is_breakout = curr_p > high_pivots[0]['val']
        is_hl = low_pivots[0]['val'] > low_pivots[1]['val']
        
        # 가독성을 위해 상태를 이모지로 직관화한다이다
        trend_icon = "🟢" if is_golden else "🔴"
        status_text = f"{trend_icon} {name}({symbol})"
        price_text = f"{curr_p:.1f}$ (+{dist_to_sup:.1f}%)"
        
        full_info = f"{status_text} | {price_text}"

        if curr_p < support:
            groups['🚨 위험 종목군'].append(full_info)
        elif is_hl:
            if is_dead:
                groups['⚠️ 눌림(주의)'].append(full_info)
            else:
                groups['💎 눌림 종목군'].append(full_info + " 🔥")
        elif is_breakout and is_golden:
            groups['🚀 슈퍼 종목군'].append(full_info + " 🔥")
        else:
            groups['📦 박스권/대기'].append(full_info)

    except: continue

# 리포트 레이아웃 구성이다
report = f"🏛️ 마켓 구조 분석 리포트 (v121)\n"
report += f"일시: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
report += "─" * 15 + "\n"
report += "💡 🟢골든 / 🔴데드(근접) / 🔥정배열\n"
report += "─" * 15 + "\n\n"

order = ['🚀 슈퍼 종목군', '💎 눌림 종목군', '⚠️ 눌림(주의)', '📦 박스권/대기', '🚨 위험 종목군']

for key in order:
    stocks = groups[key]
    report += f"{key}\n"
    if stocks:
        # 각 종목 앞에 불렛 포인트를 넣어 구분한다이다
        report += "\n".join([f"• {s}" for s in stocks])
    else:
        report += "• 해당 종목 없음"
    report += "\n\n"

report += "─" * 15 + "\n"
report += "분석 종료이다."

send_message(report)
