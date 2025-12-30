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

ignition_alarms = [] # 급등 알람 리스트이다
plunge_alarms = []   # 급락 알람 리스트이다

for symbol in ticker_map:
    try:
        df = yf.download(symbol, period='1d', interval='1m', progress=False)
        if len(df) < 31: continue
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

        curr = df.iloc[-1]
        prev = df.iloc[-2]
        
        avg_vol_30m = df.iloc[-31:-1]['Volume'].mean()
        curr_vol = float(curr['Volume'])
        
        # 가격 변동률 계산이다
        price_change = ((float(curr['Close']) - float(prev['Close'])) / float(prev['Close'])) * 100
        vol_ratio = int(curr_vol / avg_vol_30m)

        # 1. 급등 (점화) 조건이다: 거래량 3배 이상 & 가격 0.5% 이상 상승
        if curr_vol > avg_vol_30m * 3.0 and price_change >= 0.5:
            ignition_alarms.append(f"🔥 [점화] {ticker_map[symbol]}({symbol})\n현가: {curr['Close']:.2f}$ (1분 거래량 {vol_ratio}배 폭발!)")
        
        # 2. 급락 조건이다: 거래량 3배 이상 & 가격 -0.5% 이하 하락
        elif curr_vol > avg_vol_30m * 3.0 and price_change <= -0.5:
            plunge_alarms.append(f"🆘 [급락] {ticker_map[symbol]}({symbol})\n현가: {curr['Close']:.2f}$ (1분 거래량 {vol_ratio}배 투매 발생!)")
            
    except: continue

# 메시지 전송 로직이다
if ignition_alarms or plunge_alarms:
    total_msg = []
    
    if ignition_alarms:
        total_msg.append("⚠️ [긴급] 급등 전조 현상 포착이다\n" + "-" * 20 + "\n" + "\n\n".join(ignition_alarms))
    
    if plunge_alarms:
        # 급락 알람이 있다면 구분선을 넣고 추가한다이다
        if total_msg: total_msg.append("\n" + "="*20 + "\n")
        total_msg.append("🚨 [경고] 단기 급락/투매 포착이다\n" + "-" * 20 + "\n" + "\n\n".join(plunge_alarms))
    
    send_message("\n".join(total_msg))
