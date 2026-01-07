import yfinance as yf
import pandas as pd
import requests
import os
import numpy as np
from datetime import datetime

# --- [1. 설정 구간] ---
token = '8160201188:AAELStlMFcTeqpFZYuF-dsvnXWppN7iOHiI' 
chat_id = '-4998189045' 

def send_message(text):
    if not token or not chat_id:
        print("❌ 오류: 토큰이나 채팅방 ID가 없습니다.")
        return

    if len(text) > 4000:
        print(f"⚠️ 메시지가 너무 길어({len(text)}자) 나눠서 보냅니다.")
        for i in range(0, len(text), 4000):
            send_message(text[i:i+4000])
        return

    print(f"🚀 전송 시도... (길이: {len(text)})")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {'chat_id': chat_id, 'text': text}
    
    try:
        resp = requests.post(url, data=data) 
        if resp.status_code == 200:
            print("✅ 전송 성공!")
        else:
            print(f"❌ 전송 실패: {resp.status_code}")
            print(f"이유: {resp.text}") 
    except Exception as e:
        print(f"❌ 에러 발생: {e}")

# --- [2. 분석 로직] ---
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
    'QQQ': '나스닥100', 'TQQQ': '나스닥3배', 'SOXL': '반도체3배', 'SPY': 'S&P500',
    'NVDA': '엔비디아', 'TSM': 'TSMC', 'AVGO': '브로드컴', 'ASML': 'ASML', 'AMD': 'AMD', 'MU': '마이크론', 
    'GLW': '코닝', 'LRCX': '램리서치', 'AMAT': '어플라이드', 'QCOM': '퀄컴', 'ARM': 'ARM', 
    'MSFT': '마이크로소프트', 'GOOGL': '알파벳', 'AMZN': '아마존', 'META': '메타', 'AAPL': '애플', 'TSLA': '테슬라',
    'PLTR': '팔란티어', 'ORCL': '오라클', 'DELL': '델', 'ANET': '아리스타', 
    'CRWD': '크라우드',
    'IONQ': '아이온큐', 'MSTR': 'MSTR', 'COIN': '코인베이스', 'HOOD': '로빈후드', 
    'XOM': '엑슨모빌', 'CVX': '셰브론', 'SHEL': '쉘',
    'VST': '비스트라', 'CEG': '컨스텔레이션', 'TLN': '탈렌에너지', 'CCJ': '카메코', 'GEV': 'GE버노바', 'NEE': '넥스트에라',
    'LLY': '일라이릴리', 'NVO': '노보노디스크'
}

groups = {
    '🚀 슈퍼 종목군 (주도주)': [],
    '💎 눌림 종목군 (매수기회)': [],
    '⏳ 눌림 보류 (몸통 이탈)': [],
    '⚠️ 눌림 주의 (추세둔화)': [],
    '📦 박스권 (상승유지)': [],
    '📉 박스권 (추세둔화)': [],
    '🚨 위험 종목 (지지이탈)': []
}

group_status_labels = {
    '🚀 슈퍼 종목군 (주도주)': '[상승] 🔥',
    '💎 눌림 종목군 (매수기회)': '[상승] 🔥',
    '⏳ 눌림 보류 (몸통 이탈)': '[주의]',
    '⚠️ 눌림 주의 (추세둔화)': '[주의]',
    '📦 박스권 (상승유지)': '[상승]',
    '📉 박스권 (추세둔화)': '[주의]',
    '🚨 위험 종목 (지지이탈)': '[주의]'
}

for symbol, name in ticker_map.items():
    try:
        print(f"..{symbol}", end=" ", flush=True)
        
        df = yf.download(symbol, period='1y', interval='1d', progress=False)
        if len(df) < 120: continue
        
        if isinstance(df.columns, pd.MultiIndex): 
            df.columns = df.columns.get_level_values(0)

        # 현재가(Close)와 시가(Open)를 가져온다이다
        curr_p = float(df['Close'].iloc[-1])
        curr_open = float(df['Open'].iloc[-1])
        
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
        
        info = f"{name}({symbol})  (+{dist_to_sup:.1f}%)"

        if curr_p < support:
            groups['🚨 위험 종목 (지지이탈)'].append(info)
        elif is_hl:
            if is_dead:
                groups['⚠️ 눌림 주의 (추세둔화)'].append(info)
            else:
                # 캔들 몸통의 하단(시가와 종가 중 작은 값)을 구한다이다
                body_bottom = min(curr_open, curr_p)
                
                # 몸통 하단이 20일 이평선보다 크거나 같아야 '성공'이다
                if body_bottom >= curr_ma20:
                    groups['💎 눌림 종목군 (매수기회)'].append(info)
                else:
                    groups['⏳ 눌림 보류 (몸통 이탈)'].append(info)
        elif is_breakout and is_golden:
            groups['🚀 슈퍼 종목군 (주도주)'].append(info)
        else:
            if is_golden:
                groups['📦 박스권 (상승유지)'].append(info)
            else:
                groups['📉 박스권 (추세둔화)'].append(info)

    except Exception as e:
        print(f"Error {symbol}: {e}")
        continue

print("\n분석 완료! 리포트 작성 중...")

report = f"🏛️ 마켓 구조 분석 리포트 (Python v1.3 - 몸통 기준)\n"
report += "(? %)는 추세 전환 전까지의 높이를 말합니다. "  + "\n\n"

order = ['🚀 슈퍼 종목군 (주도주)', '💎 눌림 종목군 (매수기회)', '⏳ 눌림 보류 (몸통 이탈)', 
         '⚠️ 눌림 주의 (추세둔화)', '📦 박스권 (상승유지)', '📉 박스권 (추세둔화)', '🚨 위험 종목 (지지이탈)']

for key in order:
    stocks = groups[key]
    status = group_status_labels[key]
    report += f"■ {key} {status}\n"
    if stocks:
        report += "\n".join([f"  - {s}" for s in stocks])
    else:
        report += "  - 해당 종목 없음"
    report += "\n\n"

report += "-" * 30 + "\n"
report += "분석 종료이다."

send_message(report)
