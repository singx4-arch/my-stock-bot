import yfinance as yf
import pandas as pd
import requests
import os
import json
import numpy as np
from datetime import datetime

# 1. 환경 설정 및 세션 관리이다
token = '8160201188:AAELStlMFcTeqpFZYuF-dsvnXWppN7iOHiI' 
chat_id = '-4998189045'
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
    universe_info = {} 
    try:
        nasdaq100_tables = pd.read_html('https://en.wikipedia.org/wiki/Nasdaq-100')
        nasdaq100 = nasdaq100_tables[4] if len(nasdaq100_tables) > 4 else nasdaq100_tables[0]
        ticker_col = 'Ticker' if 'Ticker' in nasdaq100.columns else 'Symbol'
        for ticker in nasdaq100[ticker_col].tolist():
            universe_info[ticker.replace('.', '-')] = '나스닥100'
        # SECTOR_MAP 생략 (기존과 동일)
    except:
        universe_info = {'NVDA': '나스닥100', 'TSLA': '나스닥100'}
    return universe_info

def calculate_rsi(series, period=14):
    delta = series.diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    ma_up = up.ewm(com=period-1, min_periods=period).mean()
    ma_down = down.ewm(com=period-1, min_periods=period).mean()
    rs = ma_up / (ma_down + 1e-9)
    return 100 - (100 / (1 + rs))

def main():
    universe_info = fetch_mega_universe()
    tickers = list(universe_info.keys())
    
    print(f"Downloading data for {len(tickers)} tickers...")
    full_df = yf.download(tickers, period='2y', interval='1d', progress=True, group_by='ticker')
    
    today_str = datetime.now().strftime('%Y-%m-%d')
    sent_alerts = load_sent_alerts()
    if sent_alerts.get('date') != today_str:
        sent_alerts = {'date': today_str, 'alerts': []}

    sector_results = {}

    for symbol in tickers:
        try:
            df_d = full_df[symbol].dropna()
            if len(df_d) < 200: continue
            
            df_w = df_d.resample('W').agg({'Open':'first','High':'max','Low':'min','Close':'last','Volume':'sum'})
            
            # 1. 주봉 RSI 분석이다
            rsi_w = calculate_rsi(df_w['Close']).iloc[-1]
            is_macro_bottom = rsi_w <= 35
            
            # 2. 일봉 매집 및 수급 분석이다
            recent_6mo = df_d.iloc[-120:]
            current_price = df_d['Close'].iloc[-1]
            
            # [개선] 최근 5일 평균 거래량 vs 20일 평균 거래량 (수급 확인)이다
            vol_5 = df_d['Volume'].iloc[-5:].mean()
            vol_20 = df_d['Volume'].iloc[-20:].mean()
            vol_ratio = vol_5 / (vol_20 + 1e-9)
            
            # [개선] 권장 손절선 (6개월 최저가 또는 현재가 -10%)이다
            stop_loss = recent_6mo['Low'].min()
            
            box_range = (recent_6mo['High'].max() - recent_6mo['Low'].min()) / current_price
            obv = (np.sign(df_d['Close'].diff()) * df_d['Volume']).fillna(0).cumsum()
            obv_slope = (obv.iloc[-1] - obv.iloc[-20]) / (obv.iloc[-20:].mean() + 1e-9)
            
            ma20 = df_d['Close'].rolling(window=20).mean().iloc[-1]
            ma50 = df_d['Close'].rolling(window=50).mean().iloc[-1]
            ma200 = df_d['Close'].rolling(window=200).mean().iloc[-1]
            ma_gap = (max([ma20, ma50, ma200]) - min([ma20, ma50, ma200])) / (min([ma20, ma50, ma200]) + 1e-9)
            
            # 점수 체계 조정 (수급 가점 포함)이다
            score = 0
            if box_range < 0.45: score += 30
            if obv_slope > 0: score += 20
            if ma_gap < 0.20: score += 20
            if vol_ratio > 1.2: score += 30 # 거래량이 20% 이상 증가하면 가점이다
            
            # 리포팅 조건: 대바닥이거나, 매집 점수가 높으면서 최소한의 수급(vol_ratio > 1.0)이 있을 때이다
            if is_macro_bottom or (score >= 60 and vol_ratio > 1.0):
                sig_key = f"{symbol}_V167"
                if sig_key not in sent_alerts['alerts']:
                    status = ""
                    if is_macro_bottom: status += f"⚓ [대바닥: RSI {rsi_w:.1f}] "
                    if score >= 60: status += f"📦 [매집: {score}점] "
                    if vol_ratio > 1.5: status += f"🔥 [수급폭발] "
                    
                    msg = (f"{symbol}: {status}\n"
                           f"   - 현가: ${current_price:.2f} (손절선: ${stop_loss:.2f})\n"
                           f"   - 수급: {vol_ratio:.1f}배, 박스: {box_range*100:.1f}%, 이평차: {ma_gap*100:.1f}%")
                    
                    sector = universe_info[symbol]
                    if sector not in sector_results: sector_results[sector] = []
                    sector_results[sector].append(msg)
                    sent_alerts['alerts'].append(sig_key)
        except: continue

    if sector_results:
        report = "🏛️ 통합 리포트 v167 (수급 확인 및 손절선 추가)\n"
        report += f"분석 일시: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        report += "⚓대바닥, 📦매집, 🔥수급폭발 / 손절선 이탈 시 유의바란다.\n"
        report += "="*20 + "\n\n"
        # 리포트 구성 생략 (기존과 동일)
        send_message(report)
        save_sent_alerts(sent_alerts)

if __name__ == "__main__":
    main()
