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

def get_structural_pivots(df, lookback=60, filter_size=5, mode='low'):
    # 봇의 로직: 고정 기간이 아닌 좌우 가격 비교를 통한 구조적 마디 찾기
    pivots = []
    prices = df['Low'] if mode == 'low' else df['High']
    for i in range(len(df) - filter_size - 1, len(df) - lookback, -1):
        is_pivot = True
        for j in range(1, filter_size + 1):
            if mode == 'low':
                if prices.iloc[i] > prices.iloc[i-j] or prices.iloc[i] > prices.iloc[i+j]:
                    is_pivot = False; break
            else:
                if prices.iloc[i] < prices.iloc[i-j] or prices.iloc[i] < prices.iloc[i+j]:
                    is_pivot = False; break
        if is_pivot:
            pivots.append({'val': float(prices.iloc[i]), 'idx': i, 'date': df.index[i]})
            if len(pivots) == 3: break
    return pivots

ticker_map = { 
    'NVDA': '엔비디아', 'TSLA': '테슬라', 'AAPL': '애플', 'MSFT': '마이크로소프트', 
    'AMZN': '아마존', 'META': '메타', 'GOOGL': '구글', 'PLTR': '팔란티어', 
    'MSTR': '마이크로스트래티지', 'COIN': '코인베이스', 'AMD': 'AMD', 'NFLX': '넷플릭스', 
    'AVGO': '브로드컴', 'TQQQ': '나스닥3배레버', 'SOXL': '반도체3배레버', 'ARM': 'ARM', 
    'TSM': 'TSMC', 'MU': '마이크론', 'INTC': '인텔', 'SMCI': '슈퍼마이크로', 
    'PYPL': '페이팔', 'SQQQ': '나스닥3배인버스', 'SOXS': '반도체3배인버스', 'PANW': '팔로알토', 
    'COST': '코스트코', 'QCOM': '퀄컴', 'ASML': 'ASML', 'SNOW': '스노우플레이크', 
    'MARA': '마라톤디지털', 'RIOT': '라이엇플랫폼', 'VRT': '버티브 홀딩스', 
    'ANET': '아리스타 네트웍스', 'LLY': '일라이 릴리', 'NVO': '노보 노디스크', 'VST': '비스트라', 
    'GEV': 'GE 베르노바', 'MRVL': '마벨 테크놀로지', 'LRCX': '램리서치', 'AUR': '오로라 이노베이션', 
    'UBER': '우버', 'APP': '앱러빈', 'SAP': 'SAP', 'SOFI': '소파이', 'LMND': '레모네이드', 'ISRG': '인튜이티브 서지컬', 
    'VRTX': '버텍스 파마슈티컬스', 'REGN': '리제네론', 'CLSK': '클린스파크', 'HOOD': '로빈후드'
}

primary_uptrend = []   # 다우 이론상 확정적 상승 추세 (HH + HL)
secondary_retest = []  # 추세 내 눌림목/리테스트 구간
structural_break = []  # 추세 훼손 주의 종목

for symbol, name in ticker_map.items():
    try:
        df = yf.download(symbol, period='1y', interval='1d', progress=False)
        if len(df) < 100: continue
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

        # 1. 지표 계산
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['SMMA7'] = df['Close'].ewm(alpha=1/7, adjust=False).mean()
        curr_p = float(df['Close'].iloc[-1])
        vol_ma = df['Volume'].rolling(window=20).mean().iloc[-1]
        curr_vol = df['Volume'].iloc[-1]

        # 2. 다우 이론 구조 분석 (최신 마디 2개 추출)
        low_pivots = get_structural_pivots(df, mode='low')
        high_pivots = get_structural_pivots(df, mode='high')

        if len(low_pivots) < 2 or len(high_pivots) < 2: continue

        # 다우 이론 조건 검증
        is_hl = low_pivots[0]['val'] > low_pivots[1]['val'] # 최신 저점이 이전 저점보다 높음
        is_hh = high_pivots[0]['val'] > high_pivots[1]['val'] # 최신 고점이 이전 고점보다 높음
        is_gold = curr_p > df['MA20'].iloc[-1] and df['SMMA7'].iloc[-1] > df['MA20'].iloc[-1]
        vol_confirmation = curr_vol > vol_ma # 거래량 동반 확인

        info = f"[{name} ({symbol})]\n현재가: {curr_p:.2f}$\n단기지지: {low_pivots[0]['val']:.2f}$\n장기지지: {low_pivots[1]['val']:.2f}$"

        # 3. 전문가 등급별 분류
        if is_hh and is_hl and is_gold:
            # 주 추세 상승 확정
            m = (low_pivots[0]['val'] - low_pivots[1]['val']) / (low_pivots[0]['idx'] - low_pivots[1]['idx'])
            line_val = m * (len(df) - 1 - low_pivots[1]['idx']) + low_pivots[1]['val']
            
            if (curr_p - line_val) / line_now < 0.02:
                secondary_retest.append("💎 " + info + "\n(리테스트 매수 타점)")
            else:
                primary_uptrend.append("🚀 " + info)
        elif not is_hl and curr_p < low_pivots[0]['val']:
            structural_break.append("🚨 " + info + "\n(구조적 지지선 이탈)")

    except: continue

# 리포트 생성
report = f"🏛️ 다우 이론 기반 전문가 추세 분석 리포트\n기준일: {datetime.now().strftime('%Y-%m-%d')}\n" + "="*25 + "\n\n"
report += "🚀 제1추세: 상승 확정 (HH+HL 달성)\n"
report += "\n\n".join(primary_uptrend) if primary_uptrend else "해당 없음"
report += "\n\n" + "-"*25 + "\n\n"
report += "💎 제2반작용: 눌림목 리테스트 (매수 기회)\n"
report += "\n\n".join(secondary_retest) if secondary_retest else "해당 없음"
report += "\n\n" + "-"*25 + "\n\n"
report += "🚨 추세 주의: 구조적 이탈 발생\n"
report += "\n\n".join(structural_break) if structural_break else "해당 없음"
report += "\n\n" + "="*25 + "\n"
report += "💡 전문가 가이드\n1. 🚀 그룹은 추세가 강력하므로 7선 눌림목에서 분할 매수합니다.\n2. 💎 그룹은 다우 이론상 'Secondary Reaction' 구간으로 손익비가 가장 좋은 타점입니다."

send_message(report)
