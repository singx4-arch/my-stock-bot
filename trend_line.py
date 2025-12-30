import yfinance as yf
import pandas as pd
import requests
import os
import numpy as np

token = os.getenv('TELEGRAM_TOKEN')
chat_id = os.getenv('TELEGRAM_CHAT_ID')

def send_message(text):
    if not token or not chat_id: return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    params = {'chat_id': chat_id, 'text': text, 'parse_mode': 'Markdown'}
    requests.get(url, params=params)

def calculate_rsi(data, window=14):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

ticker_map = { 
    'NVDA': '엔비디아', 'AAPL': '애플', 'MSFT': '마이크로소프트', 'TSLA': '테슬라', 
    'AMZN': '아마존', 'META': '메타', 'GOOGL': '구글', 'AVGO': '브로드컴', 
    'AMD': 'AMD', 'TSM': 'TSMC', 'ASML': 'ASML', 'COST': '코스트코', 
    'QCOM': '퀄컴', 'ARM': 'ARM', 'TQQQ': '나스닥3배레버', 'SOXL': '반도체3배레버',
    'PLTR': '팔란티어', 'MU': '마이크론', 'ORCL': '오라클', 'DELL': '델', 'QQQ': 'QQQ'
}

trend_alerts = []

for symbol, name in ticker_map.items():
    try:
        # 일봉 데이터 분석이다
        df_d = yf.download(symbol, period='1y', interval='1d', progress=False)
        if len(df_d) < 50: continue
        if isinstance(df_d.columns, pd.MultiIndex): df_d.columns = df_d.columns.get_level_values(0)

        df_d['RSI'] = calculate_rsi(df_d['Close'])
        curr_p = float(df_d['Close'].iloc[-1])
        prev_p = float(df_d['Close'].iloc[-2])
        idx_d = len(df_d) - 1

        # 1. RSI 다이버전스 로직 추가이다
        # 피벗 포인트를 찾아 가격과 RSI의 고점/저점을 비교한다이다
        df_d['PH'] = df_d['High'][(df_d['High'] == df_d['High'].rolling(window=11, center=True).max())]
        df_d['PL'] = df_d['Low'][(df_d['Low'] == df_d['Low'].rolling(window=11, center=True).min())]
        phs = df_d.dropna(subset=['PH'])
        pls = df_d.dropna(subset=['PL'])

        # 상승 다이버전스 감지 (저점 비교)이다
        if len(pls) >= 2:
            l1, l2 = pls.iloc[-2], pls.iloc[-1]
            if l2['Low'] < l1['Low'] and l2['RSI'] > l1['RSI']:
                # 현재 시점이 최근 저점 발생 후 반등 중인지 확인한다이다
                if curr_p > l2['Low']:
                    trend_alerts.append(f"🌌 {name}({symbol}): [신호] RSI 상승 다이버전스 출현!! (추세 반전 기대)")

        # 하락 다이버전스 감지 (고점 비교)이다
        if len(phs) >= 2:
            h1, h2 = phs.iloc[-2], phs.iloc[-1]
            if h2['High'] > h1['High'] and h2['RSI'] < h1['RSI']:
                if curr_p < h2['High']:
                    trend_alerts.append(f"🌋 {name}({symbol}): [주의] RSI 하락 다이버전스 출현!! (조정 가능성)")

        # 2. 기존 추세선 및 리테스트 로직이다
        # (중략: 기존에 작성했던 200일선, 추세선 리테스트, 주봉 돌파 로직이 이 자리에 들어간다이다)
        
        # 예시로 200일선 로직만 유지한다이다
        ma200 = df_d['Close'].rolling(window=200).mean().iloc[-1]
        if curr_p > ma200 and prev_p <= df_d['Close'].rolling(window=200).mean().iloc[-2]:
            trend_alerts.append(f"🏰 {name}({symbol}): [장기] 200일선 상향 돌파!")

    except Exception as e:
        print(f"Error: {e}")
        continue

if trend_alerts:
    msg = "⚖️ [종합 추세 및 다이버전스 알림]이다\n" + "-" * 20 + "\n" + "\n\n".join(trend_alerts)
    send_message(msg)
