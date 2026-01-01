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
    except:
        pass

def calculate_rsi(data, window=14):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def find_swings(series, window=4, mode='low'):
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

# 2. 다이버전스 전용 분석 엔진이다
def run_divergence_only():
    ticker_map = {
        'QQQ': '나스닥100', 'TQQQ': '나스닥3배', 'SOXL': '반도체3배',
        'NVDA': '엔비디아', 'TSLA': '테슬라', 'AAPL': '애플', 'MSFT': '마이크로소프트',
        'AMZN': '아마존', 'META': '메타', 'GOOGL': '구글', 'PLTR': '팔란티어',
        'TSM': 'TSMC', 'MU': '마이크론', 'GLW': '코닝', 'IONQ': '아이온큐'
    }

    results = {
        '일반 상승 (바닥 반전)': [],
        '히든 상승 (추세 지속)': [],
        '일반 하락 (고점 반전)': [],
        '히든 하락 (추세 하락)': []
    }

    for symbol, name in ticker_map.items():
        try:
            df = yf.download(symbol, period='1y', interval='1d', progress=False)
            if len(df) < 50: continue
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            
            df['RSI'] = calculate_rsi(df['Close'])
            df = df.dropna()

            low_idx = find_swings(df['Low'], window=4, mode='low')
            high_idx = find_swings(df['High'], window=4, mode='high')
            
            # 상승 계열 (저점 분석)이다
            if len(low_idx) >= 2:
                i1, i2 = low_idx[-2], low_idx[-1]
                p1, p2, r1, r2 = df['Low'].iloc[i1], df['Low'].iloc[i2], df['RSI'].iloc[i1], df['RSI'].iloc[i2]
                
                # 일반 상승: 가격 저점 하락 + RSI 저점 상승 (RSI 35 이하 필터)이다
                if p2 < p1 and r2 > r1 and r1 <= 35:
                    results['일반 상승 (바닥 반전)'].append(f"- {name}({symbol})")
                # 히든 상승: 가격 저점 상승 + RSI 저점 하락이다
                elif p2 > p1 and r2 < r1:
                    results['히든 상승 (추세 지속)'].append(f"- {name}({symbol})")

            # 하락 계열 (고점 분석)이다
            if len(high_idx) >= 2:
                i1, i2 = high_idx[-2], high_idx[-1]
                p1, p2, r1, r2 = df['High'].iloc[i1], df['High'].iloc[i2], df['RSI'].iloc[i1], df['RSI'].iloc[i2]
                
                # 일반 하락: 가격 고점 상승 + RSI 고점 하락 (RSI 65 이상 필터)이다
                if p2 > p1 and r2 < r1 and r1 >= 65:
                    results['일반 하락 (고점 반전)'].append(f"- {name}({symbol})")
                # 히든 하락: 가격 고점 하락 + RSI 고점 상승이다
                elif p2 < p1 and r2 > r1:
                    results['히든 하락 (추세 하락)'].append(f"- {name}({symbol})")

        except: continue

    report = "🔍 다이버전스 유형별 분석 리포트\n"
    report += f"분석 일시: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
    report += "------------------------------\n\n"

    for title, stocks in results.items():
        report += f"■ {title}\n"
        report += "\n".join(stocks) if stocks else "- 해당 없음"
        report += "\n\n"

    report += "------------------------------\n"
    report += "분석을 종료한다이다."
    send_message(report)

if __name__ == "__main__":
    run_divergence_only()
