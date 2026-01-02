import yfinance as yf
import pandas as pd
import requests
import os
import json
import numpy as np
from datetime import datetime
from bs4 import BeautifulSoup

# 1. 환경 설정 및 텔레그램 정보이다
token = os.getenv('TELEGRAM_TOKEN') or '7971022798:AAFGQR1zxdCq1urZKgdRzjjsvr3Lt6T9y1I'
chat_id = os.getenv('TELEGRAM_CHAT_ID')
SENT_ALERTS_FILE = 'sent_alerts.json'

def send_message(text):
    if not token or not chat_id: return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    params = {'chat_id': chat_id, 'text': text}
    try:
        requests.get(url, params=params, timeout=10)
    except:
        pass

def load_sent_alerts():
    if os.path.exists(SENT_ALERTS_FILE):
        with open(SENT_ALERTS_FILE, 'r') as f:
            try: return json.load(f)
            except: return {}
    return {}

def save_sent_alerts(sent_alerts):
    with open(SENT_ALERTS_FILE, 'w') as f:
        json.dump(sent_alerts, f)

# 시장 전체 종목 리스트를 긁어오는 함수이다
def fetch_mega_universe():
    universe = []
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        # S&P 500 리스트이다
        sp500 = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')[0]
        universe.extend(sp500['Symbol'].tolist())
        
        # NASDAQ 100 리스트이다
        nasdaq100 = pd.read_html('https://en.wikipedia.org/wiki/Nasdaq-100')[4]
        universe.extend(nasdaq100['Ticker'].tolist())
        
        # 야후 파이낸스 실시간 수급주이다
        for url in ["https://finance.yahoo.com/most-active", "https://finance.yahoo.com/gainers", "https://finance.yahoo.com/trending-tickers"]:
            resp = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(resp.text, 'html.parser')
            for row in soup.find_all('tr'):
                tag = row.find('a')
                if tag:
                    symbol = tag.text.strip()
                    if symbol and len(symbol) < 6:
                        universe.append(symbol)
    except:
        universe.extend(['AAPL', 'MSFT', 'NVDA', 'TSLA', 'MU', 'AMD', 'PLTR', 'TQQQ', 'SOXL'])
        
    # 중복 제거 및 티커 포맷 수정(BRK.B -> BRK-B)이다
    clean_universe = list(set([s.replace('.', '-') for s in universe]))
    return clean_universe

def calculate_rsi(series, period=14):
    delta = series.diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    ma_up = up.ewm(com=period-1, min_periods=period).mean()
    ma_down = down.ewm(com=period-1, min_periods=period).mean()
    rs = ma_up / ma_down
    return 100 - (100 / (1 + rs))

# ⚓ 대바닥 감지이다
def detect_macro_bottom(symbol):
    try:
        df_w = yf.download(symbol, period='2y', interval='1wk', progress=False)
        if len(df_w) < 30: return None, None
        if isinstance(df_w.columns, pd.MultiIndex): df_w.columns = df_w.columns.get_level_values(0)
        
        rsi_w = calculate_rsi(df_w['Close']).iloc[-1]
        
        if rsi_w <= 35:
            df_d = yf.download(symbol, period='1y', interval='1d', progress=False)
            if isinstance(df_d.columns, pd.MultiIndex): df_d.columns = df_d.columns.get_level_values(0)
            
            ma20 = df_d['Close'].rolling(window=20).mean()
            std20 = df_d['Close'].rolling(window=20).std()
            lower_band = (ma20 - (2 * std20)).iloc[-2]
            
            is_reentry = (df_d['Close'].iloc[-2] < lower_band) and (df_d['Close'].iloc[-1] > lower_band)
            if is_reentry:
                return f"⚓ 주봉 RSI {rsi_w:.1f} 바닥 및 일봉 반등 확인이다", "bottom"
    except: pass
    return None, None

# 🚀 돌파 및 💎 응축 감지이다
def detect_momentum_and_squeeze(symbol):
    try:
        df = yf.download(symbol, period='1y', interval='1d', progress=False)
        if len(df) < 150: return None, None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        # 1. 🚀 컵앤핸들 돌파이다
        recent_high = df['High'].iloc[-40:-1].max()
        curr_price = df['Close'].iloc[-1]
        avg_vol = df['Volume'].rolling(window=20).mean().iloc[-2]
        curr_vol = df['Volume'].iloc[-1]
        
        if curr_price > recent_high and curr_vol > avg_vol * 1.5:
            return f"🚀 전고점 돌파 및 거래량 {curr_vol/avg_vol:.1f}배 폭발이다", "breakout"
        
        # 2. 💎 에너지 응축이다
        ma50 = df['Close'].rolling(window=50).mean().iloc[-1]
        ma200 = df['Close'].rolling(window=200).mean().iloc[-1]
        ma_gap = abs(ma50 - ma200) / ma200
        recent_range = (df['High'].iloc[-14:].max() - df['Low'].iloc[-14:].min()) / df['Close'].iloc[-1]
        
        if ma_gap < 0.05 and recent_range < 0.10 and curr_vol < avg_vol:
            return f"💎 이평선 밀집 및 변동성 수축 매집 구간이다", "squeeze"
    except: pass
    return None, None

def main():
    universe = fetch_mega_universe()
    today_str = datetime.now().strftime('%Y-%m-%d')
    sent_alerts = load_sent_alerts()
    if sent_alerts.get('date') != today_str:
        sent_alerts = {'date': today_str, 'alerts': []}

    report_data = {"breakout": [], "squeeze": [], "bottom": []}

    # API 과부하 방지를 위해 상위 600개 종목으로 제한한다이다
    for symbol in universe[:600]:
        msg, cat = detect_macro_bottom(symbol)
        if msg:
            sig_key = f"{symbol}_{cat}"
            if sig_key not in sent_alerts['alerts']:
                report_data[cat].append(f"⚓ {symbol}: {msg}")
                sent_alerts['alerts'].append(sig_key)
        
        msg, cat = detect_momentum_and_squeeze(symbol)
        if msg:
            sig_key = f"{symbol}_{cat}"
            if sig_key not in sent_alerts['alerts']:
                report_data[cat].append(f"🔥 {symbol}: {msg}")
                sent_alerts['alerts'].append(sig_key)

    if any(report_data.values()):
        report = "🏛️ 전미 시장 전수조사 리포트 (v156)\n"
        report += f"분석 일시: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n" + "="*20 + "\n\n"
        if report_data["breakout"]: report += "🚀 [시세 분출]\n" + "\n".join(report_data["breakout"]) + "\n\n"
        if report_data["squeeze"]: report += "💎 [에너지 응축]\n" + "\n".join(report_data["squeeze"]) + "\n\n"
        if report_data["bottom"]: report += "⚓ [대바닥 포착]\n" + "\n".join(report_data["bottom"]) + "\n\n"
        send_message(report)
        save_sent_alerts(sent_alerts)

if __name__ == "__main__":
    main()
