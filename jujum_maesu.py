import yfinance as yf
import pandas as pd
import requests
import os
import json
import numpy as np
from datetime import datetime
from bs4 import BeautifulSoup

# 1. 환경 설정 및 세션 관리이다
token = os.getenv('TELEGRAM_TOKEN') or '8160201188:AAELStlMFcTeqpFZYuF-dsvnXWppN7iOHiI'
chat_id = '-1004998189045'
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

# 섹터별 종목 매핑 정보이다
SECTOR_MAP = {
    '에너지-원자력': ['CCJ', 'CEG', 'SMR', 'OKLO', 'BWXT', 'NNE'],
    '소재-리튬/광물': ['ALB', 'FCX', 'LAC', 'ALTM', 'GLW', 'DD', 'NUE', 'STLD'],
    '방위산업': ['LMT', 'RTX', 'NOC', 'BA', 'GD', 'HWM'],
    '해운물류': ['ZIM', 'FRO', 'DSX', 'SBLK'],
    '에너지-전통': ['XOM', 'CVX', 'COP', 'SLB', 'VLO'],
    '반도체-장비/소재': ['ASML', 'AMAT', 'LRCX', 'KLAC', 'TSM', 'MU']
}

def fetch_mega_universe():
    universe_info = {} 
    try:
        nasdaq100 = pd.read_html('https://en.wikipedia.org/wiki/Nasdaq-100')[4]
        for ticker in nasdaq100['Ticker'].tolist():
            universe_info[ticker.replace('.', '-')] = '나스닥100'
        for sector, tickers in SECTOR_MAP.items():
            for t in tickers:
                universe_info[t] = sector
    except:
        universe_info = {'NVDA': '나스닥100', 'TSLA': '나스닥100', 'GLW': '소재-광물', 'CCJ': '에너지-원자력'}
    return universe_info

def calculate_rsi(series, period=14):
    delta = series.diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    ma_up = up.ewm(com=period-1, min_periods=period).mean()
    ma_down = down.ewm(com=period-1, min_periods=period).mean()
    rs = ma_up / ma_down
    return 100 - (100 / (1 + rs))

# 주봉 RSI 및 매집 점수를 통합 분석하는 함수이다
def analyze_ticker(symbol):
    try:
        # 1. 주봉 데이터 분석 (RSI 35 이하 체크)이다
        df_w = yf.download(symbol, period='2y', interval='1wk', progress=False)
        if len(df_w) < 20: return None
        if isinstance(df_w.columns, pd.MultiIndex): df_w.columns = df_w.columns.get_level_values(0)
        
        rsi_w = calculate_rsi(df_w['Close']).iloc[-1]
        is_macro_bottom = rsi_w <= 35
        
        # 2. 일봉 데이터 분석 (매집 점수 계산)이다
        df_d = yf.download(symbol, period='1y', interval='1d', progress=False)
        if len(df_d) < 150: return None
        if isinstance(df_d.columns, pd.MultiIndex): df_d.columns = df_d.columns.get_level_values(0)
        
        recent_6mo = df_d.iloc[-120:]
        box_range = (recent_6mo['High'].max() - recent_6mo['Low'].min()) / df_d['Close'].iloc[-1]
        
        obv = (np.sign(df_d['Close'].diff()) * df_d['Volume']).fillna(0).cumsum()
        obv_slope = (obv.iloc[-1] - obv.iloc[-20]) / (obv.iloc[-20:].mean() + 1e-9)
        
        ma20 = df_d['Close'].rolling(window=20).mean().iloc[-1]
        ma50 = df_d['Close'].rolling(window=50).mean().iloc[-1]
        ma200 = df_d['Close'].rolling(window=200).mean().iloc[-1]
        ma_gap = (max([ma20, ma50, ma200]) - min([ma20, ma50, ma200])) / (min([ma20, ma50, ma200]) + 1e-9)
        
        score = 0
        if box_range < 0.45: score += 40
        if obv_slope > 0: score += 30
        if ma_gap < 0.20: score += 30
        
        # 주봉 RSI가 바닥이거나 매집 점수가 60점 이상이면 보고한다이다
        if is_macro_bottom or score >= 60:
            status = ""
            if is_macro_bottom: status += f"⚓ [대바닥: 주봉 RSI {rsi_w:.1f}] "
            if score >= 60: status += f"📦 [매집: {score}점]"
            
            return {
                "msg": f"{symbol}: {status} (박스 {box_range*100:.1f}%, 이평차 {ma_gap*100:.1f}%)"
            }
    except: pass
    return None

def main():
    universe_info = fetch_mega_universe()
    today_str = datetime.now().strftime('%Y-%m-%d')
    sent_alerts = load_sent_alerts()
    if sent_alerts.get('date') != today_str:
        sent_alerts = {'date': today_str, 'alerts': []}

    sector_results = {}

    for symbol, sector in universe_info.items():
        res = analyze_ticker(symbol)
        if res:
            sig_key = f"{symbol}_V165" # 버전별 중복 방지이다
            if sig_key not in sent_alerts['alerts']:
                if sector not in sector_results:
                    sector_results[sector] = []
                sector_results[sector].append(res['msg'])
                sent_alerts['alerts'].append(sig_key)

    if sector_results:
        report = "🏛️ 나스닥100 및 전략 섹터 통합 리포트 (v165)\n"
        report += f"분석 일시: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        report += "⚓는 주봉 RSI 35 이하 대바닥, 📦는 매집 진행 중 신호이다.\n"
        report += "="*20 + "\n\n"
        
        for sector in sorted(sector_results.keys()):
            report += f"[{sector}]\n"
            report += "\n".join(sector_results[sector])
            report += "\n\n"

        send_message(report)
        save_sent_alerts(sent_alerts)

if __name__ == "__main__":
    main()
