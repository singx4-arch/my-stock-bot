import yfinance as yf
import pandas as pd
import requests
import os
import numpy as np
from datetime import datetime

# 텔레그램 설정이다
token = os.getenv('TELEGRAM_TOKEN') or '8160201188:AAELStlMFcTeqpFZYuF-dsvnXWppN7iOHiI'
chat_id = os.getenv('TELEGRAM_CHAT_ID')

def send_message(text):
    if not token or not chat_id: return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
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
    # --- [지수/ETF] ---
    'QQQ': '나스닥100', 'TQQQ': '나스닥3배', 'SOXL': '반도체3배',
    'SPY': 'S&P500', 'TLT': '미국채20년', 'JEPI': 'JEPI',
    
    # --- [반도체 핵심] ---
    'NVDA': '엔비디아', 'TSM': 'TSMC', 'AVGO': '브로드컴', 'ASML': 'ASML', 
    'AMD': 'AMD', 'MU': '마이크론', 'GLW': '코닝', 'LRCX': '램리서치', 'AMAT': '어플라이드',
    'QCOM': '퀄컴', 'INTC': '인텔', 'ARM': 'ARM', 'TXN': '텍사스인스트루먼트',
    
    # --- [빅테크/플랫폼] ---
    'MSFT': '마이크로소프트', 'GOOGL': '알파벳', 'AMZN': '아마존', 'META': '메타', 
    'AAPL': '애플', 'NFLX': '넷플릭스', 'TSLA': '테슬라',
    
    # --- [AI 하드웨어/서버/네트워크] ---
    'PLTR': '팔란티어', 'ORCL': '오라클',
    'SMCI': '슈퍼마이크로', 'DELL': '델', 'ANET': '아리스타', 'HPE': 'HPE',
    
    # --- [소프트웨어/보안] ---
    'ADBE': '어도비', 'CRM': '세일즈포스', 'NOW': '서비스나우',
    'CRWD': '크라우드스트라이크', 'PANW': '팔로알토', 'APP': '앱러빈',
    
    # --- [미래기술/크립토/고변동성] ---
    'IONQ': '아이온큐', 'MSTR': 'MSTR', 'COIN': '코인베이스',
    'HOOD': '로빈후드', 'RIVN': '리비안', 'OKLO': '오클로',
    
    # --- [에너지 (전통 오일/가스) ★추가됨] ---
    'XOM': '엑슨모빌', 'CVX': '셰브론', 
    'OXY': '옥시덴탈', 'SHEL': '쉘', 'COP': '코노코필립스',
    
    # --- [에너지 (AI 전력/원전/유틸리티)] ---
    'VST': '비스트라', 'CEG': '컨스텔레이션', 'TLN': '탈렌에너지',
    'CCJ': '카메코', 'GEV': 'GE버노바', 'ENPH': '엔페이즈', 'NEE': '넥스트에라',

    # --- [바이오/헬스케어 (시총상위) ★추가됨] ---
    'LLY': '일라이릴리', 'NVO': '노보노디스크'
}

groups = {
    '🚀 슈퍼 종목군 (주도주)': [],
    '💎 눌림 종목군 (매수기회)': [],
    '⚠️ 눌림 주의 (추세둔화)': [],
    '📦 박스권 (상승유지)': [],
    '📉 박스권 (추세둔화)': [],
    '🚨 위험 종목 (지지이탈)': []
}

# 그룹별 헤더 라벨 정의다
group_status_labels = {
    '🚀 슈퍼 종목군 (주도주)': '[상승] 🔥',
    '💎 눌림 종목군 (매수기회)': '[상승] 🔥',
    '⚠️ 눌림 주의 (추세둔화)': '[주의]',
    '📦 박스권 (상승유지)': '[상승]',
    '📉 박스권 (추세둔화)': '[주의]',
    '🚨 위험 종목 (지지이탈)': '[주의]'
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
        
        # 종목 정보에서 라벨을 제거하고 깔끔하게 이름과 수치만 남겼다이다
        info = f"{name}({symbol})  (+{dist_to_sup:.1f}%)"

        if curr_p < support:
            groups['🚨 위험 종목 (지지이탈)'].append(info)
        elif is_hl:
            if is_dead:
                groups['⚠️ 눌림 주의 (추세둔화)'].append(info)
            else:
                groups['💎 눌림 종목군 (매수기회)'].append(info)
        elif is_breakout and is_golden:
            groups['🚀 슈퍼 종목군 (주도주)'].append(info)
        else:
            if is_golden:
                groups['📦 박스권 (상승유지)'].append(info)
            else:
                groups['📉 박스권 (추세둔화)'].append(info)

    except: continue

report = f"🏛️ 마켓 구조 분석 리포트 (v125)\n"
report += "(? %)는 추세 전환 전까지의 높이를 말합니다. "  + "\n\n"

order = ['🚀 슈퍼 종목군 (주도주)', '💎 눌림 종목군 (매수기회)', '⚠️ 눌림 주의 (추세둔화)', 
         '📦 박스권 (상승유지)', '📉 박스권 (추세둔화)', '🚨 위험 종목 (지지이탈)']

for key in order:
    stocks = groups[key]
    status = group_status_labels[key]
    # 헤더 부분에만 상태 라벨을 붙인다이다
    report += f"■ {key} {status}\n"
    if stocks:
        report += "\n".join([f"  - {s}" for s in stocks])
    else:
        report += "  - 해당 종목 없음"
    report += "\n\n"

report += "-" * 30 + "\n"
report += "분석 종료이다."

send_message(report)
