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
    'NVDA': '엔비디아', 'TSLA': '테슬라', 'AAPL': '애플', 'MSFT': '마이크로소프트', 
    'AMZN': '아마존', 'META': '메타', 'GOOGL': '구글', 'PLTR': '팔란티어', 
    'MSTR': '마이크로스트래티지', 'COIN': '코인베이스', 'AMD': 'AMD', 'NFLX': '넷플릭스', 
    'AVGO': '브로드컴', 'TQQQ': '나스닥3배레버', 'SOXL': '반도체3배레버', 'ARM': 'ARM', 
    'TSM': 'TSMC', 'MU': '마이크론', 'INTC': '인텔', 'SMCI': '슈퍼마이크로', 
    'PYPL': '페이팔', 'SQQQ': '나스닥3배인버스', 'SOXS': '반도체3배인버스', 'PANW': '팔로알토', 
    'COST': '코스트코', 'QCOM': '퀄컴', 'ASML': 'ASML', 'SNOW': '스노우플레이크', 
    'MARA': '마라톤디지털', 'RIOT': '라이엇플랫폼', 'VRT': '버티브 홀딩스', 
    'ANET': '아리스타 네트웍스', 'LLY': '일라이 릴리', 'NVO': '노보 노디스크'
}

ignition_alarms = []

for symbol in ticker_map:
    try:
        # 가장 빠른 1분 봉 데이터를 가져온다이다
        df = yf.download(symbol, period='1d', interval='1m', progress=False)
        if len(df) < 31: continue
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

        curr = df.iloc[-1]
        prev = df.iloc[-2]
        
        # 1. 거래량 폭발 감지이다 (최근 30분 평균 대비 3배 이상)
        avg_vol_30m = df.iloc[-31:-1]['Volume'].mean()
        curr_vol = float(curr['Volume'])
        
        # 2. 가격 고개 들기이다 (1분 만에 0.5% 이상 상승)
        price_change = ((float(curr['Close']) - float(prev['Close'])) / float(prev['Close'])) * 100

        # 거래량이 실리면서 가격이 양봉으로 전환되는 찰나이다
        if curr_vol > avg_vol_30m * 3.0 and price_change >= 0.5:
            ignition_alarms.append(f"🔥 [점화] {ticker_map[symbol]}({symbol})\n현가: {curr['Close']:.2f}$ (1분 거래량 {int(curr_vol/avg_vol_30m)}배 폭발!)")
            
    except: continue

if ignition_alarms:
    msg = "⚠️ [긴급] 급등 전조 현상 포착이다\n" + "-" * 20 + "\n"
    msg += "\n\n".join(ignition_alarms)
    msg += "\n\n강력한 거래량이 유입되며 슈팅 준비 중이다이다."
    send_message(msg)
