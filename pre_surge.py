import yfinance as yf
import pandas as pd
import requests
import os

token = os.getenv('TELEGRAM_TOKEN')
chat_id = os.getenv('TELEGRAM_CHAT_ID')

def send_message(text):
    if not token or not chat_id: return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    params = {'chat_id': chat_id, 'text': text, 'parse_mode': 'Markdown'}
    requests.get(url, params=params)

ticker_map = {
    'NVDA': '엔비디아', 'AAPL': '애플', 'MSFT': '마이크로소프트', 'TSLA': '테슬라', 
    'AMZN': '아마존', 'META': '메타', 'GOOGL': '구글', 'AVGO': '브로드컴', 
    'AMD': 'AMD', 'TSM': 'TSMC', 'ASML': 'ASML', 'COST': '코스트코', 
    'QCOM': '퀄컴', 'ARM': 'ARM', 'TQQQ': '나스닥3배레버', 'SOXL': '반도체3배레버',
    'PLTR': '팔란티어', 'MU': '마이크론', 'ORCL': '오라클', 'DELL': '델', 'QQQ': 'QQQ'
}

ignition_alarms = []

for symbol in ticker_map:
    try:
        df = yf.download(symbol, period='1d', interval='1m', progress=False)
        if len(df) < 31: continue
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

        curr = df.iloc[-1]
        prev = df.iloc[-2]
        
        avg_vol_30m = df.iloc[-31:-1]['Volume'].mean()
        curr_vol = float(curr['Volume'])
        price_change = ((float(curr['Close']) - float(prev['Close'])) / float(prev['Close'])) * 100

        if curr_vol > avg_vol_30m * 3.0 and price_change >= 0.5:
            ignition_alarms.append(f"🔥 [점화] {ticker_map[symbol]}({symbol})\n현가: {curr['Close']:.2f}$ (1분 거래량 {int(curr_vol/avg_vol_30m)}배 폭발!)")
    except: continue

# 기존 코드 맨 아래 부분이다
if ignition_alarms:
    msg = "⚠️ [긴급] 급등 전조 현상 포착이다\n" + "-" * 20 + "\n" + "\n\n".join(ignition_alarms)
    send_message(msg)
