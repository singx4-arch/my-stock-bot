import yfinance as yf
import pandas as pd
import requests
import os
import numpy as np
import json
from datetime import datetime

# 1. 환경 설정
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

# 2. 메인 분석 엔진이다
def run_analysis():
    ticker_map = {
        'QQQ': '나스닥100', 'TQQQ': '나스닥3배', 'SOXL': '반도체3배',
        'NVDA': '엔비디아', 'TSLA': '테슬라', 'AAPL': '애플', 'MSFT': '마이크로소프트',
        'AMZN': '아마존', 'META': '메타', 'GOOGL': '구글', 'PLTR': '팔란티어',
        'TSM': 'TSMC', 'MU': '마이크론', 'GLW': '코닝'
    }

    div_results = []
    trend_results = []

    for symbol, name in ticker_map.items():
        try:
            df = yf.download(symbol, period='1y', interval='1d', progress=False)
            if len(df) < 100: continue
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            
            # 이평선 및 RSI 계산이다
            df['RSI'] = calculate_rsi(df['Close'])
            df['SMMA7'] = df['Close'].ewm(alpha=1/7, adjust=False).mean()
            df['MA20'] = df['Close'].rolling(window=20).mean()
            df = df.dropna()

            curr_p = df['Close'].iloc[-1]
            curr_s7 = df['SMMA7'].iloc[-1]
            curr_m20 = df['MA20'].iloc[-1]
            gap_ratio = (curr_s7 - curr_m20) / curr_m20

            # A. 다이버전스 분석이다
            low_idx = find_swings(df['Low'], window=4, mode='low')
            high_idx = find_swings(df['High'], window=4, mode='high')
            
            if len(low_idx) >= 2:
                i1, i2 = low_idx[-2], low_idx[-1]
                if df['Low'].iloc[i2] < df['Low'].iloc[i1] and df['RSI'].iloc[i2] > df['RSI'].iloc[i1]:
                    div_results.append(f"- {name}({symbol}): 상승 다이버전스 포착")
            
            if len(high_idx) >= 2:
                i1, i2 = high_idx[-2], high_idx[-1]
                if df['High'].iloc[i2] > df['High'].iloc[i1] and df['RSI'].iloc[i2] < df['RSI'].iloc[i1]:
                    div_results.append(f"- {name}({symbol}): 하락 다이버전스 포착")

            # B. 0.15% 근접 및 추세 분석이다
            is_dead = (curr_s7 < curr_m20) or (0 <= gap_ratio <= 0.0015)
            if is_dead:
                trend_results.append(f"- {name}({symbol}): 추세 둔화/데드 주의")

        except Exception as e:
            print(f"{symbol} 분석 오류: {e}")

    # 리포트 작성이다
    report = "🏛️ 통합 마켓 구조 분석 리포트\n"
    report += f"분석 일시: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
    report += "------------------------------\n\n"

    report += "■ RSI 다이버전스 포착\n"
    report += "\n".join(div_results) if div_results else "포착된 신호 없음"
    report += "\n\n"

    report += "■ 0.15% 이평선 근접 (추세 주의)\n"
    report += "\n".join(trend_results) if trend_results else "모든 종목 추세 양호"
    report += "\n\n"

    report += "------------------------------\n"
    report += "분석 완료이다."
    
    send_message(report)

if __name__ == "__main__":
    run_analysis()
