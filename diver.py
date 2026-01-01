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
    params = {'chat_id': chat_id, 'text': text}
    requests.get(url, params=params)

def calculate_rsi(data, window=14):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# 전문가 방식: 스윙 로우/하이 피벗 감지 함수이다
def find_swings(series, window=5, mode='low'):
    swings = []
    for i in range(window, len(series) - window):
        is_swing = True
        for j in range(1, window + 1):
            if mode == 'low':
                if series.iloc[i] > series.iloc[i-j] or series.iloc[i] > series.iloc[i+j]:
                    is_swing = False; break
            else:
                if series.iloc[i] < series.iloc[i-j] or series.iloc[i] < series.iloc[i+j]:
                    is_swing = False; break
        if is_swing:
            swings.append(i)
    return swings

def analyze_divergence(symbol, name):
    try:
        # 데이터는 최근 6개월치면 충분하다이다
        df = yf.download(symbol, period='6m', interval='1d', progress=False)
        if len(df) < 50: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

        df['RSI'] = calculate_rsi(df['Close'])
        df = df.dropna()

        # 최근 2개의 스윙 포인트를 추출한다이다
        low_indices = find_swings(df['Low'], window=4, mode='low')
        high_indices = find_swings(df['High'], window=4, mode='high')

        result = ""

        # 1. 상승 다이버전스 체크 (가격 저점 하락 + RSI 저점 상승)이다
        if len(low_indices) >= 2:
            i1, i2 = low_indices[-2], low_indices[-1]
            # 최근 저점이 과거 저점보다 낮지만, RSI는 높은 경우이다
            if df['Low'].iloc[i2] < df['Low'].iloc[i1] and df['RSI'].iloc[i2] > df['RSI'].iloc[i1]:
                result = "📈 상승 다이버전스 (바닥 신호)"

        # 2. 하락 다이버전스 체크 (가격 고점 상승 + RSI 고점 하락)이다
        if len(high_indices) >= 2:
            i1, i2 = high_indices[-2], high_indices[-1]
            # 최근 고점이 과거 고점보다 높지만, RSI는 낮은 경우이다
            if df['High'].iloc[i2] > df['High'].iloc[i1] and df['RSI'].iloc[i2] < df['RSI'].iloc[i1]:
                result = "📉 하락 다이버전스 (천장 신호)"

        if result:
            return f"{name}({symbol}): {result}"
        return None

    except: return None

# 분석할 핵심 종목 리스트이다
ticker_map = {
    'NVDA': '엔비디아', 'TSLA': '테슬라', 'AAPL': '애플', 'MSFT': '마이크로소프트',
    'AMZN': '아마존', 'META': '메타', 'GOOGL': '구글', 'PLTR': '팔란티어',
    'TQQQ': '나스닥3배', 'SOXL': '반도체3배', 'TSM': 'TSMC', 'MU': '마이크론'
}

print("다이버전스 정밀 분석 시작한다이다...")
final_results = []

for symbol, name in ticker_map.items():
    res = analyze_divergence(symbol, name)
    if res:
        final_results.append(res)

if final_results:
    report = "🔍 전문가급 RSI 다이버전스 포착 리포트\n"
    report += "------------------------------\n\n"
    report += "\n\n".join(final_results)
    report += "\n\n------------------------------\n"
    report += "위 신호는 추세 반전의 강력한 힌트가 된다이다."
    send_message(report)
else:
    print("현재 포착된 다이버전스 종목이 없다이다.")
