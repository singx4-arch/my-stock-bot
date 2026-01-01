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

# 전문가 방식: 9일 Wilder's RSI 적용이다 (이미지 참조)
def calculate_rsi_9(data, window=9):
    delta = data.diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    avg_gain = up.ewm(com=window-1, min_periods=window).mean()
    avg_loss = down.ewm(com=window-1, min_periods=window).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# 히든 및 일반 다이버전스 통합 탐지 로직이다
def detect_all_divergences(df):
    # RSI가 30 이하 혹은 70 이상인 '우물'과 '산' 구간을 정의한다이다
    df['in_low'] = df['RSI_9'] < 35
    df['in_high'] = df['RSI_9'] > 65
    
    df['low_group'] = (df['in_low'] != df['in_low'].shift()).cumsum()
    df['high_group'] = (df['in_high'] != df['in_high'].shift()).cumsum()
    
    valleys = []
    peaks = []
    
    # 저점 구간(우물) 추출이다
    for g_id, group in df[df['in_low']].groupby('low_group'):
        if len(group) > 0:
            m_idx = group['RSI_9'].idxmin()
            valleys.append({'idx': m_idx, 'rsi': group['RSI_9'].min(), 'price': df['Low'].loc[m_idx]})
            
    # 고점 구간(산) 추출이다
    for g_id, group in df[df['in_high']].groupby('high_group'):
        if len(group) > 0:
            m_idx = group['RSI_9'].idxmax()
            peaks.append({'idx': m_idx, 'rsi': group['RSI_9'].max(), 'price': df['High'].loc[m_idx]})

    status = None
    # 저점 비교 (상승 계열)이다
    if len(valleys) >= 2:
        v1, v2 = valleys[-2], valleys[-1]
        # 일반 상승 (Regular Bullish): 가격 하락, RSI 상승이다
        if v2['price'] < v1['price'] and v2['rsi'] > v1['rsi']:
            status = '일반 상승 (반전)'
        # 히든 상승 (Hidden Bullish): 가격 상승, RSI 하락이다
        elif v2['price'] > v1['price'] and v2['rsi'] < v1['rsi']:
            status = '히든 상승 (지속)'

    # 고점 비교 (하락 계열)이다
    if len(peaks) >= 2:
        p1, p2 = peaks[-2], peaks[-1]
        # 일반 하락 (Regular Bearish): 가격 상승, RSI 하락이다
        if p2['price'] > p1['price'] and p2['rsi'] < p1['rsi']:
            status = '일반 하락 (반전)'
        # 히든 하락 (Hidden Bearish): 가격 하락, RSI 상승이다
        elif p2['price'] < p1['price'] and p2['rsi'] > p1['rsi']:
            status = '히든 하락 (지속)'
            
    return status

def run_v138():
    ticker_map = {
        'QQQ': '나스닥100', 'TQQQ': '나스닥3배', 'SOXL': '반도체3배', 'NVDA': '엔비디아',
        'TSLA': '테슬라', 'AAPL': '애플', 'MSFT': '마이크로소프트', 'AMZN': '아마존',
        'META': '메타', 'GOOGL': '구글', 'PLTR': '팔란티어', 'AMD': 'AMD',
        'TSM': 'TSMC', 'AVGO': '브로드컴', 'MSTR': '마스텍', 'COIN': '코인베이스',
        'IONQ': '아이온큐', 'VST': '비스트라', 'OKLO': '오클로', 'SMR': '뉴스케일'
    }

    report_sections = {
        '일반 상승 (반전)': [], '히든 상승 (지속)': [],
        '일반 하락 (반전)': [], '히든 하락 (지속)': []
    }

    for symbol, name in ticker_map.items():
        try:
            df = yf.download(symbol, period='1y', interval='1d', progress=False)
            if len(df) < 50: continue
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            
            df['RSI_9'] = calculate_rsi_9(df['Close'], window=9)
            res = detect_all_divergences(df)
            
            if res:
                report_sections[res].append(f"- {name}({symbol})")
        except: continue

    report = "🏛️ 히든 다이버전스 통합 리포트 (v138)\n"
    report += f"분석 일시: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
    report += "-" * 35 + "\n\n"

    for title, stocks in report_sections.items():
        if stocks:
            report += f"■ {title}\n"
            report += "\n".join(stocks) + "\n\n"

    report += "-" * 35 + "\n우물과 산의 극점을 비교하여 지속과 반전을 구분했다이다."
    send_message(report)

if __name__ == "__main__":
    run_v138()
