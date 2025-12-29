import yfinance as yf
import pandas as pd
import requests
import os

# 깃허브 Secrets 정보 가져오기
token = os.getenv('TELEGRAM_TOKEN')
chat_id = os.getenv('TELEGRAM_CHAT_ID')

def send_message(text):
    url = f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={text}&parse_mode=Markdown"
    requests.get(url)

# 감시 종목 리스트 (AI, 반도체, 주도주 30개)
tickers = [
    'MSFT', 'GOOGL', 'META', 'AMZN', 'PLTR', 'SNOW', 'ORCL', 'CRM', 'AAPL', 'MSTR',
    'NVDA', 'AMD', 'AVGO', 'ARM', 'TSM', 'ASML', 'QCOM', 'INTC', 'MU', 'AMAT',
    'KLAC', 'LRCX', 'SMCI', 'ADI', 'TXN', 'TSLA', 'TQQQ', 'SOXL', 'COIN', 'MDB'
]

above_ma20_list = []
bb_alert_list = []

for symbol in tickers:
    try:
        # 1. 일봉 데이터 분석 (20일선 위 여부)
        df_daily = yf.download(symbol, period='60d', interval='1d', progress=False)
        if isinstance(df_daily.columns, pd.MultiIndex): df_daily.columns = df_daily.columns.get_level_values(0)
        
        ma20_daily = df_daily['Close'].rolling(window=20).mean().iloc[-1]
        current_price = df_daily['Close'].iloc[-1]
        
        if current_price > ma20_daily:
            above_ma20_list.append(symbol)

        # 2. 4시간 봉 데이터 분석 (볼린저 밴드 이탈 여부)
        df_4h = yf.download(symbol, period='20d', interval='4h', progress=False)
        if isinstance(df_4h.columns, pd.MultiIndex): df_4h.columns = df_4h.columns.get_level_values(0)
        
        df_4h['MA20'] = df_4h['Close'].rolling(window=20).mean()
        df_4h['STD'] = df_4h['Close'].rolling(window=20).std()
        df_4h['Upper'] = df_4h['MA20'] + (df_4h['STD'] * 2)
        df_4h['Lower'] = df_4h['MA20'] - (df_4h['STD'] * 2)
        
        last_4h = df_4h.iloc[-1]
        price_4h = last_4h['Close']
        
        if price_4h > last_4h['Upper']:
            bb_alert_list.append(f"🚀 {symbol} (상단 돌파)")
        elif price_4h < last_4h['Lower']:
            bb_alert_list.append(f"⚠️ {symbol} (하단 이탈)")

    except Exception as e:
        print(f"{symbol} 분석 에러: {e}")

# 메시지 구성 및 전송
final_msg = "🔔 **주식 실시간 분석 보고서**\n\n"

if above_ma20_list:
    final_msg += "✅ **일봉 20일선 위 종목:**\n" + ", ".join(above_ma20_list) + "\n\n"

if bb_alert_list:
    final_msg += "📊 **4H 볼린저 밴드 이탈:**\n" + "\n".join(bb_alert_list)
else:
    final_msg += "📊 4H 밴드 이탈 종목 없음"

send_message(final_msg)
