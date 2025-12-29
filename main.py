import yfinance as yf
import pandas as pd
import requests
import os

# 깃허브 Secrets 정보 가져오기이다
token = os.getenv('TELEGRAM_TOKEN')
chat_id = os.getenv('TELEGRAM_CHAT_ID')

def send_message(text):
    if len(text) > 4000: 
        text = text[:4000] + "...(중략)"
    url = f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={text}&parse_mode=Markdown"
    try: 
        requests.get(url)
    except Exception as e: 
        print(f"전송 실패했다: {e}")

def calculate_rsi(data, window=14):
    # RSI 계산 함수이다
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# 감시 종목 리스트 30개이다
tickers = [
    'MSFT', 'GOOGL', 'META', 'AMZN', 'PLTR', 'SNOW', 'ORCL', 'CRM', 'AAPL', 'MSTR',
    'NVDA', 'AMD', 'AVGO', 'ARM', 'TSM', 'ASML', 'QCOM', 'INTC', 'MU', 'AMAT',
    'KLAC', 'LRCX', 'SMCI', 'ADI', 'TXN', 'TSLA', 'TQQQ', 'SOXL', 'COIN', 'MDB'
]

above_ma20_list = []
touch_ma20_list = []
bb_alert_list = []
rsi_alert_list = []

for symbol in tickers:
    try:
        # 1. 일봉 데이터 분석이다
        df_d = yf.download(symbol, period='60d', interval='1d', progress=False)
        if df_d.empty or len(df_d) < 20: continue
        if isinstance(df_d.columns, pd.MultiIndex): df_d.columns = df_d.columns.get_level_values(0)
        
        # RSI와 20일선 계산이다
        df_d['RSI'] = calculate_rsi(df_d['Close'])
        ma20_d = df_d['Close'].rolling(window=20).mean().iloc[-1]
        curr_d = float(df_d['Close'].iloc[-1])
        rsi_d = float(df_d['RSI'].iloc[-1])
        
        # 20일선 조건 확인이다
        if curr_d > ma20_d:
            above_ma20_list.append(symbol)
            if curr_d <= ma20_d * 1.01:
                touch_ma20_list.append(f"🎯 {symbol} (가격: {curr_d:.2f} / RSI: {rsi_d:.1f})")
        
        # RSI 과열/침체 확인이다
        if rsi_d >= 70:
            rsi_alert_list.append(f"🔥 {symbol} 과매수 (RSI: {rsi_d:.1f})")
        elif rsi_d <= 30:
            rsi_alert_list.append(f"❄️ {symbol} 과매도 (RSI: {rsi_d:.1f})")

        # 2. 4시간 봉 볼린저 밴드 분석이다
        df_4h = yf.download(symbol, period='30d', interval='4h', progress=False)
        if df_4h.empty or len(df_4h) < 20: continue
        if isinstance(df_4h.columns, pd.MultiIndex): df_4h.columns = df_4h.columns.get_level_values(0)
        
        df_4h['MA'] = df_4h['Close'].rolling(window=20).mean()
        df_4h['STD'] = df_4h['Close'].rolling(window=20).std()
        upper_bb = df_4h['MA'] + (df_4h['STD'] * 2)
        lower_bb = df_4h['MA'] - (df_4h['STD'] * 2)
        
        curr_4h = float(df_4h['Close'].iloc[-1])
        if curr_4h > float(upper_bb.iloc[-1]):
            bb_alert_list.append(f"🚀 {symbol} (밴드상단돌파)")
        elif curr_4h < float(lower_bb.iloc[-1]):
            bb_alert_list.append(f"⚠️ {symbol} (밴드하단이탈)")
            
    except: continue

# 메시지 구성이다
msg = "🔔 종합 주식 분석 보고서이다\n\n"
msg += "✅ 일봉 20일선 위:\n" + (", ".join(above_ma20_list) if above_ma20_list else "없음") + "\n\n"
msg += "🎯 20일선 지지/터치 (1% 근접):\n" + ("\n".join(touch_ma20_list) if touch_ma20_list else "없음") + "\n\n"
msg += "📊 4H 볼린저 밴드 신호:\n" + ("\n".join(bb_alert_list) if bb_alert_list else "없음") + "\n\n"
msg += "📈 RSI 과열/침체 신호:\n" + ("\n".join(rsi_alert_list) if rsi_alert_list else "없음")

send_message(msg)
