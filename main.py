import yfinance as yf
import pandas as pd
import requests
import os

# 깃허브 Secrets 정보 가져오기
token = os.getenv('TELEGRAM_TOKEN')
chat_id = os.getenv('TELEGRAM_CHAT_ID')

def send_message(text):
    if len(text) > 4000: text = text[:4000] + "...(중략)"
    url = f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={text}&parse_mode=Markdown"
    try: requests.get(url)
    except Exception as e: print(f"전송 실패: {e}")

# 주도주 30개 리스트
tickers = [
    'MSFT', 'GOOGL', 'META', 'AMZN', 'PLTR', 'SNOW', 'ORCL', 'CRM', 'AAPL', 'MSTR',
    'NVDA', 'AMD', 'AVGO', 'ARM', 'TSM', 'ASML', 'QCOM', 'INTC', 'MU', 'AMAT',
    'KLAC', 'LRCX', 'SMCI', 'ADI', 'TXN', 'TSLA', 'TQQQ', 'SOXL', 'COIN', 'MDB'
]

above_ma20_list = []
bb_alert_list = []

for symbol in tickers:
    try:
        # 1. 일봉 20일선 체크
        df_d = yf.download(symbol, period='60d', interval='1d', progress=False)
        if df_d.empty or len(df_d) < 20: continue
        if isinstance(df_d.columns, pd.MultiIndex): df_d.columns = df_d.columns.get_level_values(0)
        ma20 = df_d['Close'].rolling(window=20).mean().iloc[-1]
        if float(df_d['Close'].iloc[-1]) > float(ma20): above_ma20_list.append(symbol)

        # 2. 4시간 봉 볼린저 밴드 체크
        df_4h = yf.download(symbol, period='30d', interval='4h', progress=False)
        if df_4h.empty or len(df_4h) < 20: continue
        if isinstance(df_4h.columns, pd.MultiIndex): df_4h.columns = df_4h.columns.get_level_values(0)
        df_4h['MA'] = df_4h['Close'].rolling(window=20).mean()
        df_4h['STD'] = df_4h['Close'].rolling(window=20).std()
        upper = df_4h['MA'] + (df_4h['STD'] * 2)
        lower = df_4h['MA'] - (df_4h['STD'] * 2)
        price = float(df_4h['Close'].iloc[-1])
        if price > float(upper.iloc[-1]): bb_alert_list.append(f"🚀 {symbol} (상단돌파)")
        elif price < float(lower.iloc[-1]): bb_alert_list.append(f"⚠️ {symbol} (하단이탈)")
    except: continue

# 메시지 발송
msg = "🔔 **주식 분석 보고서**\n\n"
msg += "✅ **일봉 20일선 위:**\n" + (", ".join(above_ma20_list) if above_ma20_list else "없음") + "\n\n"
msg += "📊 **4H 밴드 이탈:**\n" + ("\n".join(bb_alert_list) if bb_alert_list else "없음")
send_message(msg)
