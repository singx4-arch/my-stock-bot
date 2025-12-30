import yfinance as yf
import pandas as pd
import requests
import os
import numpy as np
import json
from datetime import datetime

token = os.getenv('TELEGRAM_TOKEN')
chat_id = os.getenv('TELEGRAM_CHAT_ID')
SENT_ALERTS_FILE = 'sent_alerts.json'

def load_sent_alerts():
    if os.path.exists(SENT_ALERTS_FILE):
        with open(SENT_ALERTS_FILE, 'r') as f:
            try:
                return json.load(f)
            except:
                return {}
    return {}

def save_sent_alerts(sent_alerts):
    with open(SENT_ALERTS_FILE, 'w') as f:
        json.dump(sent_alerts, f)

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

today_str = datetime.now().strftime('%Y-%m-%d')
sent_alerts = load_sent_alerts()

if sent_alerts.get('date') != today_str:
    sent_alerts = {'date': today_str, 'alerts': []}

new_alerts = []

for symbol, name in ticker_map.items():
    try:
        df_d = yf.download(symbol, period='1y', interval='1d', progress=False)
        if len(df_d) < 200: continue
        if isinstance(df_d.columns, pd.MultiIndex): df_d.columns = df_d.columns.get_level_values(0)

        df_d['RSI'] = calculate_rsi(df_d['Close'])
        curr_p = float(df_d['Close'].iloc[-1])
        prev_p = float(df_d['Close'].iloc[-2])
        curr_low = float(df_d['Low'].iloc[-1])
        curr_high = float(df_d['High'].iloc[-1])
        idx_d = len(df_d) - 1

        current_signals = []

        # 다이버전스 분석 로직이다
        df_d['PH'] = df_d['High'][(df_d['High'] == df_d['High'].rolling(window=11, center=True).max())]
        df_d['PL'] = df_d['Low'][(df_d['Low'] == df_d['Low'].rolling(window=11, center=True).min())]
        phs = df_d.dropna(subset=['PH'])
        pls = df_d.dropna(subset=['PL'])

        # 상승 다이버전스 체크이다
        if len(pls) >= 2:
            l1, l2 = pls.iloc[-2], pls.iloc[-1]
            if l2['Low'] < l1['Low'] and l2['RSI'] > l1['RSI'] and curr_p > l2['Low']:
                current_signals.append(f"🌌 {name}({symbol}): RSI 상승 다이버전스 출현!!")

        # 하락 다이버전스 체크이다
        if len(phs) >= 2:
            h1, h2 = phs.iloc[-2], phs.iloc[-1]
            if h2['High'] > h1['High'] and h2['RSI'] < h1['RSI'] and curr_p < h2['High']:
                current_signals.append(f"🌋 {name}({symbol}): RSI 하락 다이버전스 출현!!")

        # 기타 추세 신호들이다
        ma200 = df_d['Close'].rolling(window=200).mean().iloc[-1]
        prev_ma200 = df_d['Close'].rolling(window=200).mean().iloc[-2]
        if curr_p > ma200 and prev_p <= prev_ma200:
            current_signals.append(f"🏰 {name}({symbol}): 200일선 상향 돌파!")

        # 중복 방지 체크 후 추가한다이다
        for signal in current_signals:
            if signal not in sent_alerts['alerts']:
                new_alerts.append(signal)
                sent_alerts['alerts'].append(signal)

    except Exception as e:
        continue

if new_alerts:
    msg = "⚖️ 종합 추세 및 다이버전스 알림이다\n" + "-" * 20 + "\n" + "\n\n".join(new_alerts)
    send_message(msg)
    save_sent_alerts(sent_alerts)
