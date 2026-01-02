import yfinance as yf
import pandas as pd
import requests
import os
import json
import numpy as np
from datetime import datetime
from bs4 import BeautifulSoup

token = os.getenv('TELEGRAM_TOKEN') or '7971022798:AAFGQR1zxdCq1urZKgdRzjjsvr3Lt6T9y1I'
chat_id = os.getenv('TELEGRAM_CHAT_ID')
SENT_ALERTS_FILE = 'sent_alerts.json'

def send_message(text):
    if not token or not chat_id: return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    params = {'chat_id': chat_id, 'text': text}
    try: requests.get(url, params=params, timeout=10)
    except: pass

def load_sent_alerts():
    if os.path.exists(SENT_ALERTS_FILE):
        with open(SENT_ALERTS_FILE, 'r') as f:
            try: return json.load(f)
            except: return {}
    return {}

def save_sent_alerts(sent_alerts):
    with open(SENT_ALERTS_FILE, 'w') as f:
        json.dump(sent_alerts, f)

def fetch_mega_universe():
    universe = []
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        sp500 = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')[0]
        universe.extend(sp500['Symbol'].tolist())
        nasdaq100 = pd.read_html('https://en.wikipedia.org/wiki/Nasdaq-100')[4]
        universe.extend(nasdaq100['Ticker'].tolist())
        for url in ["https://finance.yahoo.com/most-active", "https://finance.yahoo.com/gainers"]:
            resp = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(resp.text, 'html.parser')
            for row in soup.find_all('tr'):
                tag = row.find('a')
                if tag: universe.append(tag.text.strip())
    except:
        universe.extend(['AAPL', 'MSFT', 'NVDA', 'TSLA', 'MU', 'AMD', 'PLTR'])
    return list(set([s.replace('.', '-') for s in universe]))

def calculate_rsi(series, period=14):
    delta = series.diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    ma_up = up.ewm(com=period-1, min_periods=period).mean()
    ma_down = down.ewm(com=period-1, min_periods=period).mean()
    rs = ma_up / ma_down
    return 100 - (100 / (1 + rs))

# 🏗️ 장기 응축(Long-term Squeeze) 감지 로직이다
def detect_long_term_squeeze(symbol):
    try:
        # 최소 1년(250거래일)의 데이터가 필요하다이다
        df = yf.download(symbol, period='1y', interval='1d', progress=False)
        if len(df) < 250: return None, None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        # 1. 장기 이격도 수렴 확인이다
        # 50일, 100일, 200일 이평선이 모두 10% 이내로 모였는지 확인한다이다
        ma50 = df['Close'].rolling(window=50).mean().iloc[-1]
        ma100 = df['Close'].rolling(window=100).mean().iloc[-1]
        ma200 = df['Close'].rolling(window=200).mean().iloc[-1]
        
        ma_list = [ma50, ma100, ma200]
        # 이평선 밀집도 계산 수식이다: 
        # $$Gap = \frac{\max(MA_{50}, MA_{100}, MA_{200}) - \min(MA_{50}, MA_{100}, MA_{200})}{\min(MA_{50}, MA_{100}, MA_{200})}$$
        ma_gap = (max(ma_list) - min(ma_list)) / min(ma_list)
        
        # 2. 장기 박스권 확인 (최근 6개월/120일간의 가격 변동 폭)이다
        recent_6mo = df.iloc[-120:]
        box_range = (recent_6mo['High'].max() - recent_6mo['Low'].min()) / df['Close'].iloc[-1]
        
        # 3. 거래량 메마름 확인 (최근 1개월 거래량이 연간 평균보다 적음)이다
        vol_avg_y = df['Volume'].mean()
        vol_avg_m = df['Volume'].iloc[-20:].mean()
        
        # 조건: 이평선이 8% 이내 밀집 + 6개월간 주가 변동 20% 이내 + 거래량 진정이다
        if ma_gap < 0.08 and box_range < 0.20 and vol_avg_m < vol_avg_y:
            return f"🏗️ 장기 매집 포착이다. 6개월 박스권 범위 {box_range*100:.1f}% 및 장기 이평선 밀집 상태이다", "long_squeeze"
    except: pass
    return None, None

def detect_macro_bottom(symbol):
    try:
        df_w = yf.download(symbol, period='2y', interval='1wk', progress=False)
        if len(df_w) < 20: return None, None
        if isinstance(df_w.columns, pd.MultiIndex): df_w.columns = df_w.columns.get_level_values(0)
        rsi_w = calculate_rsi(df_w['Close']).iloc[-1]
        if rsi_w <= 35:
            df_d = yf.download(symbol, period='6mo', interval='1d', progress=False)
            if isinstance(df_d.columns, pd.MultiIndex): df_d.columns = df_d.columns.get_level_values(0)
            ma20 = df_d['Close'].rolling(window=20).mean(); std20 = df_d['Close'].rolling(window=20).std()
            lower_band = (ma20 - (2 * std20)).iloc[-2]
            if (df_d['Close'].iloc[-2] < lower_band) and (df_d['Close'].iloc[-1] > lower_band):
                return f"⚓ 주봉 RSI {rsi_w:.1f} 바닥 및 일봉 반등 확인이다", "bottom"
    except: pass
    return None, None

def main():
    universe = fetch_mega_universe()
    today_str = datetime.now().strftime('%Y-%m-%d')
    sent_alerts = load_sent_alerts()
    if sent_alerts.get('date') != today_str:
        sent_alerts = {'date': today_str, 'alerts': []}

    report_data = {"long_squeeze": [], "bottom": []}

    # 분석 대상을 600개로 확대했다이다
    for symbol in universe[:600]:
        # 장기 응축 체크이다
        msg, cat = detect_long_term_squeeze(symbol)
        if msg and f"{symbol}_{cat}" not in sent_alerts['alerts']:
            report_data[cat].append(f"🏗️ {symbol}: {msg}")
            sent_alerts['alerts'].append(f"{symbol}_{cat}")
        
        # 매크로 바닥 체크이다
        msg, cat = detect_macro_bottom(symbol)
        if msg and f"{symbol}_{cat}" not in sent_alerts['alerts']:
            report_data[cat].append(f"⚓ {symbol}: {msg}")
            sent_alerts['alerts'].append(f"{symbol}_{cat}")

    if any(report_data.values()):
        report = "🏛️ 전미 시장 장기 응축 및 바닥 탐색 리포트 (v157)\n"
        report += f"분석 일시: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n" + "="*20 + "\n\n"
        if report_data["long_squeeze"]: report += "🏗️ [장기 에너지 응축: 대시세 준비주]\n" + "\n".join(report_data["long_squeeze"]) + "\n\n"
        if report_data["bottom"]: report += "⚓ [대바닥 포착: 주봉 RSI 35 이하]\n" + "\n".join(report_data["bottom"]) + "\n\n"
        send_message(report)
        save_sent_alerts(sent_alerts)

if __name__ == "__main__":
    main()
