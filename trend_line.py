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
    'NVDA': '엔비디아', 'TSLA': '테슬라', 'PLTR': '팔란티어', 
    'AAPL': '애플', 'MSFT': '마이크로소프트', 'TQQQ': '나스닥3배',
    'ORCL': '오라클', 'MU': '마이크론', 'DELL': '델', 'VRT': '버티브'
}

trend_alerts = []

for symbol, name in ticker_map.items():
    try:
        # 1. 일봉 분석 (단기 및 200일선)이다
        df_d = yf.download(symbol, period='1y', interval='1d', progress=False)
        if len(df_d) < 200: continue
        if isinstance(df_d.columns, pd.MultiIndex): df_d.columns = df_d.columns.get_level_values(0)

        curr_p = float(df_d['Close'].iloc[-1])
        prev_p = float(df_d['Close'].iloc[-2])
        
        # 200일 이평선 돌파 확인이다
        ma200 = df_d['Close'].rolling(window=200).mean().iloc[-1]
        prev_ma200 = df_d['Close'].rolling(window=200).mean().iloc[-2]
        
        if curr_p > ma200 and prev_p <= prev_ma200:
            trend_alerts.append(f"🏰 {name}({symbol}): [장기] 200일선 상향 돌파! (강력 신호)")

        # 2. 주봉 분석 (장기 추세선)이다
        df_w = yf.download(symbol, period='2y', interval='1wk', progress=False)
        if len(df_w) < 30: continue
        if isinstance(df_w.columns, pd.MultiIndex): df_w.columns = df_w.columns.get_level_values(0)

        # 주봉 피벗 고점 찾기 (주변 10봉 기준)이다
        df_w['PH'] = df_w['High'][(df_w['High'] == df_w['High'].rolling(window=21, center=True).max())]
        phs = df_w.dropna(subset=['PH'])
        
        if len(phs) >= 2:
            p1, p2 = phs.iloc[-2], phs.iloc[-1]
            x1, y1 = df_w.index.get_loc(p1.name), p1['PH']
            x2, y2 = df_w.index.get_loc(p2.name), p2['PH']
            m_h = (y2 - y1) / (x2 - x1)
            
            if m_h < 0: # 하락하던 주봉 추세선이다
                w_line = m_h * (len(df_w) - 1 - x1) + y1
                if curr_p > w_line and prev_p <= w_line:
                    trend_alerts.append(f"🏛️ {name}({symbol}): [초장기] 주봉 하락 추세선 돌파!")

    except: continue

if trend_alerts:
    msg = "⚖️ [추세 판도 변화] 장기/단기 추세 돌파 포착이다\n" + "-" * 20 + "\n" + "\n\n".join(trend_alerts)
    send_message(msg)
