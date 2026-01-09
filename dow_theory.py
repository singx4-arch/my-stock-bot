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

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    
    if len(text) > 4000:
        for i in range(0, len(text), 4000):
            send_message(text[i:i+4000])
        return

    data = {
        'chat_id': chat_id, 
        'text': text, 
        'parse_mode': 'Markdown',
        'disable_web_page_preview': True
    }
    
    try:
        resp = requests.post(url, data=data) 
        if resp.status_code != 200:
            print(f"❌ 전송 실패: {resp.text}")
    except Exception as e:
        print(f"❌ 에러 발생: {e}")

# --- [2. 보조 분석 함수] ---

def calculate_rsi(series, period=14):
    delta = series.diff()
    up = delta.clip(lower=0)
    down = -delta.clip(upper=0)
    ema_up = up.ewm(com=period-1, adjust=False).mean()
    ema_down = down.ewm(com=period-1, adjust=False).mean()
    rs = ema_up / ema_down
    return 100 - (100 / (1 + rs))

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

# --- [3. 메인 분석 로직] ---

# 전문가 기준: 최근 20일(1개월) 누적 수익률 비교이다
qqq_data = yf.Ticker("QQQ").history(period='30d', interval='1d', prepost=True)
qqq_20d_perf = (qqq_data['Close'].iloc[-1] - qqq_data['Close'].iloc[-21]) / qqq_data['Close'].iloc[-21]

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
    '🚀 골크 + 전고 돌파': [],
    '💎 눌림 종목군 (매수기회)': [],
    '⏳ 눌림 보류 (몸통 이탈)': [],
    '⚠️ 눌림 주의 (추세둔화)': [],
    '🚨 위험 종목 (지지이탈)': []
}

for symbol, name in ticker_map.items():
    try:
        print(f"..{symbol}", end=" ", flush=True)
        ticker_obj = yf.Ticker(symbol)
        df = ticker_obj.history(period='1y', interval='1d', prepost=True)
        if len(df) < 120: continue
        
        curr_p = float(df['Close'].iloc[-1])
        curr_open = float(df['Open'].iloc[-1])
        curr_vol = float(df['Volume'].iloc[-1])
        
        # 20일 누적 수익률 계산이다
        stock_20d_perf = (df['Close'].iloc[-1] - df['Close'].iloc[-21]) / df['Close'].iloc[-21]
        
        # 기술 지표 계산이다
        df['SMMA7'] = df['Close'].ewm(alpha=1/7, adjust=False).mean()
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['VolMA20'] = df['Volume'].rolling(window=20).mean()
        df['RSI'] = calculate_rsi(df['Close'])
        
        # 볼린저 밴드 스퀴즈 계산이다
        std = df['Close'].rolling(window=20).std()
        df['BB_Width'] = (std * 4) / df['MA20']
        is_squeeze = df['BB_Width'].iloc[-1] < df['BB_Width'].rolling(window=120).min().iloc[-2] * 1.1

        curr_rsi = df['RSI'].iloc[-1]
        vol_ratio = curr_vol / df['VolMA20'].iloc[-2]
        
        is_golden = (df['SMMA7'].iloc[-1] > df['MA20'].iloc[-1])
        low_pivots = get_structural_pivots(df, mode='low')
        high_pivots = get_structural_pivots(df, mode='high')
        
        if len(low_pivots) < 1 or len(high_pivots) < 1: continue
        support = low_pivots[0]['val']
        is_breakout = curr_p > high_pivots[0]['val']
        is_hl = low_pivots[0]['val'] > (low_pivots[1]['val'] if len(low_pivots) > 1 else 0)

        # 이모지 태그 생성이다
        tags = ""
        if stock_20d_perf > qqq_20d_perf: tags += "💪"
        if is_squeeze: tags += "⏳"
        
        chart_link = f"[차트](https://finviz.com/chart.ashx?t={symbol})"
        info = f"{name}({symbol}) {chart_link} (+{((curr_p-support)/support)*100:.1f}%)"

        if curr_p < support:
            danger_tag = "💀" if vol_ratio > 1.3 else ""
            groups['🚨 위험 종목 (지지이탈)'].append(f"{info} {tags}{danger_tag}")
            
        elif is_hl:
            if not is_golden:
                danger_tag = "💀" if vol_ratio > 1.3 else ""
                groups['⚠️ 눌림 주의 (추세둔화)'].append(f"{info} {tags}{danger_tag}")
            else:
                body_bottom = min(curr_open, curr_p)
                if body_bottom >= df['MA20'].iloc[-1]:
                    conf_tag = "⭐" if vol_ratio < 0.85 else ""
                    groups['💎 눌림 종목군 (매수기회)'].append(f"{info} {tags}{conf_tag}")
                else:
                    groups['⏳ 눌림 보류 (몸통 이탈)'].append(f"{info} {tags}")
                    
        elif is_breakout and is_golden:
            conf_tag = "⭐" if vol_ratio > 1.3 else ""
            rsi_tag = "⚠️" if curr_rsi > 70 else ""
            groups['🚀 골크 + 전고 돌파'].append(f"{info} {tags}{conf_tag}{rsi_tag}")

    except Exception as e:
        print(f"Error {symbol}: {e}")

print("\n분석 완료! 리포트 작성 중이다.")

report = "🏛️ 마켓 구조 분석 리포트 (v3.2 전문가용 상대 강도)이다\n"
report += "💪지수보다강함(20일) | ⏳에너지응축 | ⚠️과매수주의 | ⭐신뢰도 | 💀아주위험이다\n\n"

order = ['🚀 골크 + 전고 돌파', '💎 눌림 종목군 (매수기회)', '⏳ 눌림 보류 (몸통 이탈)', 
         '⚠️ 눌림 주의 (추세둔화)', '🚨 위험 종목 (지지이탈)']

for key in order:
    stocks = groups[key]
    report += f"■ {key}\n"
    if stocks:
        report += "\n".join([f"  - {s}" for s in stocks])
    else:
        report += "  - 해당 종목 없음이다"
    report += "\n\n"

report += "-" * 30 + "\n분석 종료이다."
send_message(report)
