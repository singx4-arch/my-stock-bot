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

# OBV(온밸런스 볼륨) 계산 함수이다
def calculate_obv(df):
    obv = [0]
    for i in range(1, len(df)):
        if df['Close'].iloc[i] > df['Close'].iloc[i-1]:
            obv.append(obv[-1] + df['Volume'].iloc[i])
        elif df['Close'].iloc[i] < df['Close'].iloc[i-1]:
            obv.append(obv[-1] - df['Volume'].iloc[i])
        else:
            obv.append(obv[-1])
    return pd.Series(obv, index=df.index)

def find_swings(series, window=3, mode='low'): # 감도를 window=3으로 높였다이다
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

# 2. 거래량 기반 신호 보정 엔진이다
def run_divergence_v132():
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
            df['OBV'] = calculate_obv(df)
            df = df.dropna()

            low_idx = find_swings(df['Low'], window=3, mode='low')
            high_idx = find_swings(df['High'], window=3, mode='high')
            
            # 거래량 에너지 확인 (최근 5일 평균 거래량 vs 20일 평균)이다
            avg_vol_20 = df['Volume'].rolling(window=20).mean().iloc[-1]
            curr_vol_5 = df['Volume'].rolling(window=5).mean().iloc[-1]
            vol_power = " (거래량 동반)" if curr_vol_5 > avg_vol_20 else ""

            # 상승 계열 분석이다
            if len(low_idx) >= 2:
                i1, i2 = low_idx[-2], low_idx[-1]
                p1, p2, r1, r2 = df['Low'].iloc[i1], df['Low'].iloc[i2], df['RSI'].iloc[i1], df['RSI'].iloc[i2]
                
                if p2 < p1 and r2 > r1 and r1 <= 35:
                    results['일반 상승 (바닥 반전)'].append(f"- {name}({symbol}){vol_power}")
                elif p2 > p1 and r2 < r1:
                    results['히든 상승 (추세 지속)'].append(f"- {name}({symbol}){vol_power}")

            # 하락 계열 분석이다
            if len(high_idx) >= 2:
                i1, i2 = high_idx[-2], high_idx[-1]
                p1, p2, r1, r2 = df['High'].iloc[i1], df['High'].iloc[i2], df['RSI'].iloc[i1], df['RSI'].iloc[i2]
                
                if p2 > p1 and r2 < r1 and r1 >= 65:
                    results['일반 하락 (고점 반전)'].append(f"- {name}({symbol}){vol_power}")
                elif p2 < p1 and r2 > r1:
                    # 히든 하락이지만 거래량이 강력하면 리포트에서 제외하거나 경고를 완화한다이다
                    if curr_vol_5 < avg_vol_20:
                        results['히든 하락 (추세 하락)'].append(f"- {name}({symbol}) (거래량 부족)")
                    else:
                        # 거래량이 실린 경우 저항 돌파 시도로 보고 박스권 대기로 분류 가능하다이다
                        pass

        except: continue

    report = "🔍 거래량 보정 다이버전스 리포트 (v132)\n"
    report += f"분석 일시: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
    report += "------------------------------\n\n"

    for title, stocks in results.items():
        report += f"■ {title}\n"
        report += "\n".join(stocks) if stocks else "- 해당 없음"
        report += "\n\n"

    report += "------------------------------\n"
    report += "거래량이 실린 하락 신호는 돌파 시도로 해석한다이다."
    send_message(report)

if __name__ == "__main__":
    run_divergence_v132()
