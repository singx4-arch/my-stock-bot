import yfinance as yf
import pandas as pd
import requests
import os
import numpy as np
from datetime import datetime

# 1. 환경 설정 및 통신 함수이다
token = os.getenv('TELEGRAM_TOKEN') or '7971022798:AAFGQR1zxdCq1urZKgdRzjjsvr3Lt6T9y1I'
chat_id = os.getenv('TELEGRAM_CHAT_ID')

def send_message(text):
    if not token or not chat_id: return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    params = {'chat_id': chat_id, 'text': text}
    try:
        requests.get(url, params=params, timeout=10)
    except: pass

# 전문가용 와일더 RSI 계산식이다
def calculate_rsi_wilder(data, window=14):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0))
    loss = (-delta.where(delta < 0, 0))
    
    avg_gain = gain.ewm(alpha=1/window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/window, adjust=False).mean()
    
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# 블로그 전략: 유의미한 피크와 트러프를 찾아 다이버전스를 판별한다이다
def detect_divergence_v137(df):
    # 좌우 5개 캔들 중 최댓값/최솟값을 피벗으로 정의한다이다
    window = 5
    df['peak'] = df['High'][(df['High'] == df['High'].rolling(window=window*2+1, center=True).max())]
    df['trough'] = df['Low'][(df['Low'] == df['Low'].rolling(window=window*2+1, center=True).min())]
    
    # 피벗 지점의 인덱스를 추출한다이다
    peaks = df.dropna(subset=['peak'])
    troughs = df.dropna(subset=['trough'])
    
    sig = None
    # 1. 일반 상승 다이버전스 (Regular Bullish): 가격 저점 하락 & RSI 저점 상승이다
    if len(troughs) >= 2:
        p1, p2 = troughs.iloc[-2], troughs.iloc[-1]
        if p2['Low'] < p1['Low'] and p2['RSI'] > p1['RSI']:
            # 현재 RSI가 과매도(30) 구간을 탈출하려 할 때 신뢰도가 높다이다
            if p1['RSI'] < 35:
                sig = 'REG_BULL'

    # 2. 일반 하락 다이버전스 (Regular Bearish): 가격 고점 상승 & RSI 고점 하락이다
    if len(peaks) >= 2:
        p1, p2 = peaks.iloc[-2], peaks.iloc[-1]
        if p2['High'] > p1['High'] and p2['RSI'] < p1['RSI']:
            # 현재 RSI가 과매수(70) 구간에서 꺾일 때 신뢰도가 높다이다
            if p1['RSI'] > 65:
                sig = 'REG_BEAR'

    # 3. 히든 다이버전스 (추세 지속) 분석이다
    if not sig:
        if len(troughs) >= 2:
            p1, p2 = troughs.iloc[-2], troughs.iloc[-1]
            if p2['Low'] > p1['Low'] and p2['RSI'] < p1['RSI']:
                sig = 'HID_BULL'
        elif len(peaks) >= 2:
            p1, p2 = peaks.iloc[-2], peaks.iloc[-1]
            if p2['High'] < p1['High'] and p2['RSI'] > p1['RSI']:
                sig = 'HID_BEAR'
                
    return sig

# 2. 메인 분석 엔진이다
def run_analysis_v137():
    ticker_map = {
        'TQQQ': '나스닥3배', 'SOXL': '반도체3배', 'NVDA': '엔비디아', 'TSLA': '테슬라',
        'AAPL': '애플', 'MSFT': '마이크로소프트', 'AMZN': '아마존', 'META': '메타', 
        'GOOGL': '구글', 'PLTR': '팔란티어', 'AMD': 'AMD', 'MU': '마이크론',
        'TSM': 'TSMC', 'AVGO': '브로드컴', 'MSTR': '마스텍', 'IONQ': '아이온큐',
        'VST': '비스트라', 'OKLO': '오클로', 'SMR': '뉴스케일', 'GLW': '코닝'
    }

    report_groups = {
        '🆘 진바닥 신호 (Regular Bullish)': [],
        '🚨 고점 경고 (Regular Bearish)': [],
        '📈 상승 지속 (Hidden Bullish)': [],
        '📉 하락 지속 (Hidden Bearish)': []
    }

    for symbol, name in ticker_map.items():
        try:
            df = yf.download(symbol, period='1y', interval='1d', progress=False)
            if len(df) < 100: continue
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            
            df['RSI'] = calculate_rsi_wilder(df['Close'], window=14)
            sig = detect_divergence_v137(df)
            
            info = f"- {name}({symbol})"
            if sig == 'REG_BULL': report_groups['🆘 진바닥 신호 (Regular Bullish)'].append(info)
            elif sig == 'REG_BEAR': report_groups['🚨 고점 경고 (Regular Bearish)'].append(info)
            elif sig == 'HID_BULL': report_groups['📈 상승 지속 (Hidden Bullish)'].append(info)
            elif sig == 'HID_BEAR': report_groups['📉 하락 지속 (Hidden Bearish)'].append(info)
        except: continue

    report = "🏛️ 블로그 전략 기반 정밀 다이버전스 리포트 (v137)\n"
    report += f"분석 일시: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
    report += "-" * 35 + "\n\n"

    for title, stocks in report_groups.items():
        if stocks:
            report += f"■ {title}\n"
            report += "\n".join(stocks) + "\n\n"

    report += "-" * 35 + "\n피크와 트러프의 실패 스윙 구조를 분석했다이다."
    send_message(report)

if __name__ == "__main__":
    run_analysis_v137()
