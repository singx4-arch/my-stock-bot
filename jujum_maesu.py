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

# 종목 리스트를 더 공격적으로 가져오도록 수정했다이다
def fetch_mega_universe():
    universe = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    
    # 1. S&P 500 리스트이다
    try:
        sp500 = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')[0]
        universe.extend(sp500['Symbol'].tolist())
    except: pass
    
    # 2. NASDAQ 100 리스트이다
    try:
        nasdaq100 = pd.read_html('https://en.wikipedia.org/wiki/Nasdaq-100')[4]
        universe.extend(nasdaq100['Ticker'].tolist())
    except: pass
    
    # 3. 야후 파이낸스 실시간 데이터이다
    urls = [
        "https://finance.yahoo.com/most-active",
        "https://finance.yahoo.com/gainers",
        "https://finance.yahoo.com/trending-tickers"
    ]
    for url in urls:
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            soup = BeautifulSoup(resp.text, 'html.parser')
            for row in soup.find_all('tr'):
                tag = row.find('a')
                if tag:
                    symbol = tag.text.strip()
                    if symbol and len(symbol) < 6: universe.append(symbol)
        except: continue
        
    # 만약 위 과정이 모두 실패했다면 기본 리스트를 반환한다이다
    if not universe:
        universe = ['AAPL', 'MSFT', 'NVDA', 'TSLA', 'MU', 'AMD', 'PLTR', 'BITO', 'MARA', 'RIOT', 'COIN', 'SOXL', 'TQQQ']
        
    return list(set([s.replace('.', '-') for s in universe]))

def get_accumulation_score(symbol):
    try:
        df = yf.download(symbol, period='1y', interval='1d', progress=False)
        if len(df) < 150: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        # 박스권 범위이다
        recent_6mo = df.iloc[-120:]
        box_range = (recent_6mo['High'].max() - recent_6mo['Low'].min()) / df['Close'].iloc[-1]
        
        # OBV 상승세이다
        obv = (np.sign(df['Close'].diff()) * df['Volume']).fillna(0).cumsum()
        obv_slope = (obv.iloc[-1] - obv.iloc[-20]) / (obv.iloc[-20:].mean() + 1e-9)
        
        # 이평선 밀집도이다
        ma20 = df['Close'].rolling(window=20).mean().iloc[-1]
        ma50 = df['Close'].rolling(window=50).mean().iloc[-1]
        ma200 = df['Close'].rolling(window=200).mean().iloc[-1]
        ma_list = [ma20, ma50, ma200]
        ma_gap = (max(ma_list) - min(ma_list)) / (min(ma_list) + 1e-9)
        
        score = 0
        if box_range < 0.50: score += 40
        if obv_slope > 0: score += 30
        if ma_gap < 0.20: score += 30
        
        # 점수 커트라인을 60점으로 더 낮춰서 더 많은 종목을 보여준다이다
        if score >= 60:
            return {
                "score": score,
                "msg": f"{score}점 | 박스: {box_range*100:.1f}% | 이평차: {ma_gap*100:.1f}%"
            }
    except: pass
    return None

def main():
    universe = fetch_mega_universe()
    total_found = len(universe)
    
    today_str = datetime.now().strftime('%Y-%m-%d')
    sent_alerts = load_sent_alerts()
    if sent_alerts.get('date') != today_str:
        sent_alerts = {'date': today_str, 'alerts': []}

    discovered_acc = []
    
    # 분석 대상을 800개로 늘렸다이다
    for symbol in universe[:800]:
        res = get_accumulation_score(symbol)
        if res:
            # 중복 알람 방지용 키를 생성한다이다
            sig_key = f"{symbol}_ACC_{res['score']}"
            if sig_key not in sent_alerts['alerts']:
                discovered_acc.append((res['score'], f"📦 {symbol}: {res['msg']}"))
                sent_alerts['alerts'].append(sig_key)

    discovered_acc.sort(key=lambda x: x[0], reverse=True)

    if discovered_acc:
        report = f"🏛️ 전미 시장 전수조사 리포트 (v160)\n"
        report += f"발견된 총 종목 수: {total_found}개\n"
        report += f"분석 완료: {min(total_found, 800)}개\n"
        report += "="*20 + "\n\n"
        
        for _, m in discovered_acc[:30]: # 상위 30개로 대폭 늘렸다이다
            report += m + "\n"

        send_message(report)
        save_sent_alerts(sent_alerts)

if __name__ == "__main__":
    main()
