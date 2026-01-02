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

# 실시간으로 시장의 핫한 종목들을 긁어오는 함수이다
def fetch_discovery_universe():
    urls = [
        "https://finance.yahoo.com/trending-tickers",
        "https://finance.yahoo.com/most-active",
        "https://finance.yahoo.com/gainers"
    ]
    headers = {'User-Agent': 'Mozilla/5.0'}
    discovered_tickers = []
    
    # 기본 감시 종목이다 (우량주)
    base_list = ['NVDA', 'TSLA', 'AAPL', 'MSFT', 'AMZN', 'META', 'GOOGL', 'AVGO', 'MU', 'AMD', 'TSM', 'PLTR', 'MSTR', 'COIN', 'TQQQ', 'SOXL']
    discovered_tickers.extend(base_list)
    
    for url in urls:
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(resp.text, 'html.parser')
            # 야후 파이낸스 테이블에서 티커를 추출한다이다
            for row in soup.find_all('tr'):
                tag = row.find('a')
                if tag:
                    symbol = tag.text.strip()
                    if symbol and len(symbol) < 6: # 지수 제외 개별 종목 위주이다
                        discovered_tickers.append(symbol)
        except:
            continue
            
    return list(set(discovered_tickers)) # 중복 제거이다

def calculate_rsi(series, period=14):
    delta = series.diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    ma_up = up.ewm(com=period-1, min_periods=period).mean()
    ma_down = down.ewm(com=period-1, min_periods=period).mean()
    rs = ma_up / ma_down
    return 100 - (100 / (1 + rs))

# ⚓ 찐바닥 및 매크로 바닥 감지 (주봉 필터 적용)이다
def detect_macro_bottom(symbol):
    try:
        df_w = yf.download(symbol, period='5y', interval='1wk', progress=False)
        if len(df_w) < 30: return None, None
        if isinstance(df_w.columns, pd.MultiIndex): df_w.columns = df_w.columns.get_level_values(0)
        
        # 주봉 RSI $RSI = 100 - \frac{100}{1 + RS}$ 기반이다
        rsi_w = calculate_rsi(df_w['Close']).iloc[-1]
        
        if rsi_w <= 35:
            df_d = yf.download(symbol, period='1y', interval='1d', progress=False)
            if isinstance(df_d.columns, pd.MultiIndex): df_d.columns = df_d.columns.get_level_values(0)
            
            ma20 = df_d['Close'].rolling(window=20).mean()
            std20 = df_d['Close'].rolling(window=20).std()
            lower_band = (ma20 - (2 * std20)).iloc[-2]
            
            is_reentry = (df_d['Close'].iloc[-2] < lower_band) and (df_d['Close'].iloc[-1] > lower_band)
            
            if is_reentry:
                return f"⚓ 주봉 RSI {rsi_w:.1f} 대바닥 구간 및 일봉 반등 확인이다", "bottom"
    except:
        pass
    return None, None

# 🚀 컵앤핸들 돌파 및 📦 에너지 응축 감지이다
def detect_momentum_and_squeeze(symbol):
    try:
        df = yf.download(symbol, period='1y', interval='1d', progress=False)
        if len(df) < 200: return None, None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        # 1. 🚀 돌파 (Cup and Handle)이다
        recent_high = df['High'].iloc[-40:-1].max()
        curr_price = df['Close'].iloc[-1]
        avg_vol = df['Volume'].rolling(window=20).mean().iloc[-2]
        curr_vol = df['Volume'].iloc[-1]
        
        if curr_price > recent_high and curr_vol > avg_vol * 1.5:
            return f"🚀 전고점 돌파 및 거래량 {curr_vol/avg_vol:.1f}배 실린 컵앤핸들 완성이다", "breakout"
        
        # 2. 💎 에너지 응축 (VCP/Squeeze)이다
        ma50 = df['Close'].rolling(window=50).mean().iloc[-1]
        ma200 = df['Close'].rolling(window=200).mean().iloc[-1]
        ma_gap = abs(ma50 - ma200) / ma200
        recent_range = (df['High'].iloc[-14:].max() - df['Low'].iloc[-14:].min()) / df['Close'].iloc[-1]
        
        if ma_gap < 0.04 and recent_range < 0.08 and curr_vol < avg_vol:
            return f"💎 이평선 밀집({ma_gap*100:.1f}%) 및 변동성 수축 중인 매집 구간이다", "squeeze"
    except:
        pass
    return None, None

def main():
    # 인터넷 실시간 검색을 통해 감시 리스트를 확보한다이다
    universe = fetch_discovery_universe()
    
    today_str = datetime.now().strftime('%Y-%m-%d')
    sent_alerts = load_sent_alerts()
    
    if sent_alerts.get('date') != today_str:
        sent_alerts = {'date': today_str, 'alerts': []}

    report_data = {"breakout": [], "squeeze": [], "bottom": []}

    for symbol in universe:
        # 찐바닥 체크이다
        msg, cat = detect_macro_bottom(symbol)
        if msg:
            sig_key = f"{symbol}_{cat}"
            if sig_key not in sent_alerts['alerts']:
                report_data[cat].append(f"⚓ {symbol}: {msg}")
                sent_alerts['alerts'].append(sig_key)
        
        # 돌파 및 응축 체크이다
        msg, cat = detect_momentum_and_squeeze(symbol)
        if msg:
            sig_key = f"{symbol}_{cat}"
            if sig_key not in sent_alerts['alerts']:
                report_data[cat].append(f"🔥 {symbol}: {msg}")
                sent_alerts['alerts'].append(sig_key)

    # 통합 리포트 발송이다
    if any(report_data.values()):
        report = f"🏛️ 시장 전수조사 리포트 (v155)\n일시: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n" + "="*20 + "\n\n"
        
        if report_data["breakout"]:
            report += "🚀 [시세 분출: 컵앤핸들 돌파]\n" + "\n".join(report_data["breakout"]) + "\n\n"
        if report_data["squeeze"]:
            report += "💎 [에너지 응축: 매집 구간]\n" + "\n".join(report_data["squeeze"]) + "\n\n"
        if report_data["bottom"]:
            report += "⚓ [대바닥 포착: 주봉 RSI 35 이하]\n" + "\n".join(report_data["bottom"]) + "\n\n"
            
        send_message(report)
        save_sent_alerts(sent_alerts)

if __name__ == "__main__":
    main()
