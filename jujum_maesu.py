import yfinance as yf
import pandas as pd
import requests
import os
import json
import numpy as np
from datetime import datetime
from bs4 import BeautifulSoup

# 1. 환경 설정 및 세션 관리이다
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
        universe.extend(['AAPL', 'MSFT', 'NVDA', 'TSLA', 'MU', 'AMD', 'PLTR', 'BITO', 'MARA'])
    return list(set([s.replace('.', '-') for s in universe]))

def calculate_rsi(series, period=14):
    delta = series.diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    ma_up = up.ewm(com=period-1, min_periods=period).mean()
    ma_down = down.ewm(com=period-1, min_periods=period).mean()
    rs = ma_up / ma_down
    return 100 - (100 / (1 + rs))

# 🪙 코인식 바닥 매집(Accumulation) 감지 로직이다
def detect_crypto_style_bottom(symbol):
    try:
        df = yf.download(symbol, period='1y', interval='1d', progress=False)
        if len(df) < 250: return None, None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        # 1. 가격 범위 유연화 (6개월간 변동폭 35% 이내)이다
        # 비트코인처럼 바닥에서 출렁이며 매집하는 구간을 잡기 위함이다
        recent_6mo = df.iloc[-120:]
        box_range = (recent_6mo['High'].max() - recent_6mo['Low'].min()) / df['Close'].iloc[-1]
        
        # 2. OBV(On-Balance Volume)를 통한 숨은 매집 확인이다
        # 주가는 횡보하지만 거래량 에너지가 상승 중인지 확인한다이다
        obv = (np.sign(df['Close'].diff()) * df['Volume']).fillna(0).cumsum()
        obv_slope = (obv.iloc[-1] - obv.iloc[-20]) / obv.iloc[-20:].mean()
        
        # 3. 이평선 수렴도 계산이다
        ma20 = df['Close'].rolling(window=20).mean().iloc[-1]
        ma50 = df['Close'].rolling(window=50).mean().iloc[-1]
        ma200 = df['Close'].rolling(window=200).mean().iloc[-1]
        ma_list = [ma20, ma50, ma200]
        
        # 이평선 간격 수식이다
        # $$Gap = \frac{\max(MA) - \min(MA)}{\min(MA)}$$
        ma_gap = (max(ma_list) - min(ma_list)) / min(ma_list)
        
        # 조건: 6개월 변동폭 35% 이내 + OBV 우상향 + 이평선 10% 이내 밀집이다
        if box_range < 0.35 and obv_slope > 0 and ma_gap < 0.10:
            return f"🪙 코인식 바닥 매집 중이다. 6개월 변동폭 {box_range*100:.1f}%, OBV 상승세이다", "accumulation"
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
                return f"⚓ 주봉 RSI {rsi_w:.1f} 대바닥 및 일봉 반등 확인이다", "macro_bottom"
    except: pass
    return None, None

def main():
    universe = fetch_mega_universe()
    today_str = datetime.now().strftime('%Y-%m-%d')
    sent_alerts = load_sent_alerts()
    if sent_alerts.get('date') != today_str:
        sent_alerts = {'date': today_str, 'alerts': []}

    report_data = {"accumulation": [], "macro_bottom": []}

    for symbol in universe[:650]:
        # 1. 코인식 바닥 매집주 탐색이다
        msg, cat = detect_crypto_style_bottom(symbol)
        if msg and f"{symbol}_{cat}" not in sent_alerts['alerts']:
            report_data[cat].append(f"🪙 {symbol}: {msg}")
            sent_alerts['alerts'].append(f"{symbol}_{cat}")
        
        # 2. 역사적 대바닥 종목 탐색이다
        msg, cat = detect_macro_bottom(symbol)
        if msg and f"{symbol}_{cat}" not in sent_alerts['alerts']:
            report_data[cat].append(f"⚓ {symbol}: {msg}")
            sent_alerts['alerts'].append(f"{symbol}_{cat}")

    if any(report_data.values()):
        report = "🏛️ 전미 시장 바닥 매집 및 대시세 준비주 리포트 (v158)\n"
        report += f"분석 일시: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n" + "="*20 + "\n\n"
        if report_data["accumulation"]: report += "📦 [코인식 바닥 매집: OBV 상승 및 이평선 수렴]\n" + "\n".join(report_data["accumulation"]) + "\n\n"
        if report_data["macro_bottom"]: report += "⚓ [역사적 바닥: 주봉 RSI 35 이하 공포 구간]\n" + "\n".join(report_data["macro_bottom"]) + "\n\n"
        send_message(report)
        save_sent_alerts(sent_alerts)

if __name__ == "__main__":
    main()
