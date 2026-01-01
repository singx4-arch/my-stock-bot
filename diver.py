import yfinance as yf
import pandas as pd
import requests
import os
import numpy as np
from datetime import datetime

# 1. 환경 설정 및 텔레그램 연결이다
token = os.getenv('TELEGRAM_TOKEN') or '7971022798:AAFGQR1zxdCq1urZKgdRzjjsvr3Lt6T9y1I'
chat_id = os.getenv('TELEGRAM_CHAT_ID')

def send_message(text):
    if not token or not chat_id: return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    params = {'chat_id': chat_id, 'text': text}
    try:
        requests.get(url, params=params, timeout=10)
    except: pass

# 전문가용 와일더 RSI 9일선 계산이다
def calculate_rsi_9_wilder(data, window=9):
    delta = data.diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    # Wilder's Smoothing 적용이다
    avg_gain = up.ewm(com=window-1, min_periods=window).mean()
    avg_loss = down.ewm(com=window-1, min_periods=window).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# 우물(Valley)과 산(Peak) 극점 기반 다이버전스 탐지이다
def detect_divergence_1d(df):
    # 과매수/과매도 필터링 구간이다
    df['in_low'] = df['RSI_9'] < 35
    df['in_high'] = df['RSI_9'] > 65
    
    df['low_group'] = (df['in_low'] != df['in_low'].shift()).cumsum()
    df['high_group'] = (df['in_high'] != df['in_high'].shift()).cumsum()
    
    valleys = []
    peaks = []
    
    # 저점 구간(우물) 분석이다
    for g_id, group in df[df['in_low']].groupby('low_group'):
        if len(group) > 0:
            m_idx = group['RSI_9'].idxmin()
            valleys.append({'idx': m_idx, 'rsi': group['RSI_9'].min(), 'price': df['Low'].loc[m_idx]})
            
    # 고점 구간(산) 분석이다
    for g_id, group in df[df['in_high']].groupby('high_group'):
        if len(group) > 0:
            m_idx = group['RSI_9'].idxmax()
            peaks.append({'idx': m_idx, 'rsi': group['RSI_9'].max(), 'price': df['High'].loc[m_idx]})

    status = None
    # 저점 비교 (상승 계열)이다
    if len(valleys) >= 2:
        v1, v2 = valleys[-2], valleys[-1]
        if (v2['idx'] - v1['idx']).days < 60: # 60일 이내의 인접한 우물만 비교한다이다
            if v2['price'] < v1['price'] and v2['rsi'] > v1['rsi']:
                status = '일반 상승 (바닥 반전)'
            elif v2['price'] > v1['price'] and v2['rsi'] < v1['rsi']:
                status = '히든 상승 (추세 지속)'

    # 고점 비교 (하락 계열)이다
    if len(peaks) >= 2:
        p1, p2 = peaks[-2], peaks[-1]
        if (p2['idx'] - p1['idx']).days < 60:
            if p2['price'] > p1['price'] and p2['rsi'] < p1['rsi']:
                status = '일반 하락 (천장 반전)'
            elif p2['price'] < p1['price'] and p2['rsi'] > p1['rsi']:
                status = '히든 하락 (추세 하락)'
            
    return status

def run_expert_1d_analysis():
    ticker_map = {
        'QQQ': '나스닥100', 'TQQQ': '나스닥3배', 'SOXL': '반도체3배', 'NVDA': '엔비디아',
        'TSLA': '테슬라', 'AAPL': '애플', 'MSFT': '마이크로소프트', 'AMZN': '아마존',
        'META': '메타', 'GOOGL': '구글', 'PLTR': '팔란티어', 'AMD': 'AMD',
        'TSM': 'TSMC', 'AVGO': '브로드컴', 'MSTR': '마스텍', 'COIN': '코인베이스',
        'IONQ': '아이온큐', 'VST': '비스트라', 'OKLO': '오클로', 'SMR': '뉴스케일',
        'ANET': '아리스타', 'VRT': '버티브', 'DELL': '델', 'NFLX': '넷플릭스'
    }

    report_sections = {
        '일반 상승 (바닥 반전)': [], '히든 상승 (추세 지속)': [],
        '일반 하락 (천장 반전)': [], '히든 하락 (추세 하락)': []
    }

    for symbol, name in ticker_map.items():
        try:
            # 일봉(1d) 데이터를 1년치 가져온다이다
            df = yf.download(symbol, period='1y', interval='1d', progress=False)
            if len(df) < 50: continue
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            
            df['RSI_9'] = calculate_rsi_9_wilder(df['Close'])
            res = detect_divergence_1d(df)
            
            if res:
                report_sections[res].append(f"- {name}({symbol})")
        except: continue

    report = "🏛️ 일봉 전용 전문가 다이버전스 리포트 (v139)\n"
    report += f"분석 일시: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
    report += "-" * 35 + "\n\n"

    for title, stocks in report_sections.items():
        if stocks:
            report += f"■ {title}\n"
            report += "\n".join(stocks) + "\n\n"

    report += "-" * 35 + "\n노이즈를 제거한 일봉 변곡점 분석을 마친다이다."
    send_message(report)

if __name__ == "__main__":
    run_expert_1d_analysis()
