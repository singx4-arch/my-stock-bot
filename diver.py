import yfinance as yf
import pandas as pd
import requests
import os
import numpy as np
from datetime import datetime

# 1. 환경 설정이다
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

    # 결과를 담을 딕셔너리이다
    div_groups = {
        '일반 상승 다이버전스 (반전 상승)': [],
        '히든 상승 다이버전스 (추세 지속)': [],
        '일반 하락 다이버전스 (반전 하락)': [],
        '히든 하락 다이버전스 (추세 지속)': []
    }

    for symbol, name in ticker_map.items():
        try:
            df = yf.download(symbol, period='1y', interval='1d', progress=False)
            if len(df) < 100: continue
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            
            df['RSI'] = calculate_rsi(df['Close'])
            df = df.dropna()

            # 저점/고점 스윙 포인트 추출이다
            low_idx = find_swings(df['Low'], window=4, mode='low')
            high_idx = find_swings(df['High'], window=4, mode='high')
            
            # 상승 계열 분석 (저점 비교)이다
            if len(low_idx) >= 2:
                i1, i2 = low_idx[-2], low_idx[-1]
                p1, p2 = df['Low'].iloc[i1], df['Low'].iloc[i2]
                r1, r2 = df['RSI'].iloc[i1], df['RSI'].iloc[i2]
                
                # 일반 상승: 가격 저점 하락 + RSI 저점 상승이다
                if p2 < p1 and r2 > r1:
                    div_groups['일반 상승 다이버전스 (반전 상승)'].append(f"- {name}({symbol})")
                # 히든 상승: 가격 저점 상승 + RSI 저점 하락이다
                elif p2 > p1 and r2 < r1:
                    div_groups['히든 상승 다이버전스 (추세 지속)'].append(f"- {name}({symbol})")

            # 하락 계열 분석 (고점 비교)이다
            if len(high_idx) >= 2:
                i1, i2 = high_idx[-2], high_idx[-1]
                p1, p2 = df['High'].iloc[i1], df['High'].iloc[i2]
                r1, r2 = df['RSI'].iloc[i1], df['RSI'].iloc[i2]
                
                # 일반 하락: 가격 고점 상승 + RSI 고점 하락이다
                if p2 > p1 and r2 < r1:
                    div_groups['일반 하락 다이버전스 (반전 하락)'].append(f"- {name}({symbol})")
                # 히든 하락: 가격 고점 하락 + RSI 고점 상승이다
                elif p2 < p1 and r2 > r1:
                    div_groups['히든 하락 다이버전스 (추세 지속)'].append(f"- {name}({symbol})")

        except Exception as e:
            print(f"{symbol} 분석 오류: {e}")

    # 리포트 작성이다
    report = "🔍 4대 다이버전스 정밀 분석 리포트\n"
    report += f"분석 일시: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
    report += "-" * 30 + "\n\n"

    for group_name, stocks in div_groups.items():
        report += f"■ {group_name}\n"
        if stocks:
            report += "\n".join(stocks)
        else:
            report += "- 해당 종목 없음"
        report += "\n\n"

    report += "-" * 30 + "\n"
    report += "모든 투자의 책임은 본인에게 있다이다."
    
    send_message(report)

if __name__ == "__main__":
    run_analysis()
