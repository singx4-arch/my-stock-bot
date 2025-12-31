import yfinance as yf
import pandas as pd
import requests
import os
import numpy as np
import json
from datetime import datetime

# 1. 환경 설정 및 세션 로드
token = os.getenv('TELEGRAM_TOKEN')
chat_id = os.getenv('TELEGRAM_CHAT_ID')
SENT_ALERTS_FILE = 'sent_alerts.json'

def load_sent_alerts():
    if os.path.exists(SENT_ALERTS_FILE):
        with open(SENT_ALERTS_FILE, 'r') as f:
            try: return json.load(f)
            except: return {}
    return {}

def save_sent_alerts(sent_alerts):
    with open(SENT_ALERTS_FILE, 'w') as f:
        json.dump(sent_alerts, f)

def send_message(text):
    if not token or not chat_id: return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    params = {'chat_id': chat_id, 'text': text, 'parse_mode': 'Markdown'}
    requests.get(url, params=params)

def calculate_rsi(data, window=14):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# 봇의 로직: 구조적 변곡점(Pivot) 역추적 (GAS getPivots 완벽 이식)
def get_pivots(df, lookback=60, filter_size=3, gap=5, mode='low'):
    pivots = []
    prices = df['Low'] if mode == 'low' else df['High']
    # 오늘 데이터(idx -1)는 형성 중이므로 -2부터 거꾸로 스캔
    for i in range(len(df) - 2, len(df) - lookback, -1):
        if i < filter_size or i >= len(df) - filter_size: continue
        is_pivot = True
        for j in range(1, filter_size + 1):
            if mode == 'low':
                if prices.iloc[i] > prices.iloc[i-j] or prices.iloc[i] > prices.iloc[i+j]:
                    is_pivot = False; break
            else:
                if prices.iloc[i] < prices.iloc[i-j] or prices.iloc[i] < prices.iloc[i+j]:
                    is_pivot = False; break
        if is_pivot:
            if pivots and (pivots[-1]['idx'] - i) < gap: continue
            pivots.append({'val': float(prices.iloc[i]), 'idx': i})
            if len(pivots) == 2: break
    return pivots

# 봇의 로직: 구글 앱스 스크립트 v80의 checkTrueRetest 로직 이식
def check_true_retest(df, pivots, label):
    if len(pivots) < 2: return None
    p2, p1 = pivots[0], pivots[1] 
    idx_now = len(df) - 1
    cp = float(df['Low'].iloc[-1]) # 지지선은 Low 기준
    
    m = (p2['val'] - p1['val']) / (p2['idx'] - p1['idx'])
    line_now = m * (idx_now - p1['idx']) + p1['val']
    margin = 0.015

    if cp < line_now: # 선 아래에 있는 경우 (이탈 상태)
        # 최근 7일 이내에 선 위에 있었는지 확인 (이탈 사건 추적)
        had_breakdown = False
        for i in range(2, 8):
            line_past = m * (idx_now - i - p1['idx']) + p1['val']
            if df['Low'].iloc[-i] > line_past:
                had_breakdown = True; break
        
        if had_breakdown and (line_now - cp) / line_now < margin:
            return f"🔄 주의: {label} 이탈 후 저항 리테스트 중 (매도 타점)"
        return f"🚨 {label} 이탈 상태 (주의 요망)"
    
    # 선 위에 있는 경우 (v80에서는 별도 메시지 없었으나 필요 시 유지 가능)
    return None

# 봇의 로직: 구글 앱스 스크립트 v80의 checkResistanceStatus 로직 이식
def check_resistance_status(df, res_pivots):
    if len(res_pivots) < 2: return None
    p2, p1 = res_pivots[0], res_pivots[1]
    idx_now = len(df) - 1
    cp = float(df['Close'].iloc[-1])
    m = (p2['val'] - p1['val']) / (p2['idx'] - p1['idx'])
    res_line = m * (idx_now - p1['idx']) + p1['val']
    margin = 0.015
    
    if cp > res_line: # 돌파 상태
        # 최근 7일 이내에 선 아래에 있었는지 확인 (돌파 사건 추적)
        had_breakout = False
        for i in range(2, 8):
            line_past = m * (idx_now - i - p1['idx']) + p1['val']
            if df['Close'].iloc[-i] < line_past:
                had_breakout = True; break
        
        if had_breakout and (cp - res_line) / res_line < margin:
            return f"🔄 알림: 장기 저항 돌파 후 지지 리테스트 중 (강력 매수 타점)"
        return f"🔥 장기 저항 돌파 상태입니다. 매수 고려!"
    else: # 돌파 전
        if (res_line - cp) / res_line < margin:
            return f"🎯 돌파 대기: 장기 저항선에 근접했습니다. 돌파 여부를 주시하세요."
    return None

ticker_map = { 
    'NVDA': '엔비디아', 'AAPL': '애플', 'MSFT': '마이크로소프트', 'TSLA': '테슬라', 
    'AMZN': '아마존', 'META': '메타', 'GOOGL': '구글', 'AVGO': '브로드컴', 
    'AMD': 'AMD', 'TSM': 'TSMC', 'ASML': 'ASML', 'COST': '코스트코', 
    'QCOM': '퀄컴', 'ARM': 'ARM', 'TQQQ': '나스닥3배레버', 'SOXL': '반도체3배레버',
    'PLTR': '팔란티어', 'MU': '마이크론', 'ORCL': '오라클', 'DELL': '델', 'QQQ': 'QQQ'
}

today_str = datetime.now().strftime('%Y-%m-%d')
sent_alerts = load_sent_alerts()
if sent_alerts.get('date') != today_str:
    sent_alerts = {'date': today_str, 'alerts': []}

new_alerts = []

for symbol, name in ticker_map.items():
    try:
        df_d = yf.download(symbol, period='1y', interval='1d', progress=False)
        if len(df_d) < 200: continue
        if isinstance(df_d.columns, pd.MultiIndex): df_d.columns = df_d.columns.get_level_values(0)
        
        df_d['RSI'] = calculate_rsi(df_d['Close'])
        curr_p = float(df_d['Close'].iloc[-1])

        # 1. 다이버전스 분석 (유저 요청: 그대로 유지)
        df_d['PH'] = df_d['High'][(df_d['High'] == df_d['High'].rolling(window=11, center=True).max())]
        df_d['PL'] = df_d['Low'][(df_d['Low'] == df_d['Low'].rolling(window=11, center=True).min())]
        pls = df_d.dropna(subset=['PL'])
        phs = df_d.dropna(subset=['PH'])

        if len(pls) >= 2:
            l1, l2 = pls.iloc[-2], pls.iloc[-1]
            if l2['Low'] < l1['Low'] and l2['RSI'] > l1['RSI'] and curr_p > l2['Low']:
                sig_key = f"{symbol}_BULL_DIV"
                if sig_key not in sent_alerts['alerts']:
                    new_alerts.append(f"📈 {name}({symbol}): RSI 상승 다이버전스 출현!!")
                    sent_alerts['alerts'].append(sig_key)

        if len(phs) >= 2:
            h1, h2 = phs.iloc[-2], phs.iloc[-1]
            if h2['High'] > h1['High'] and h2['RSI'] < h1['RSI'] and curr_p < h2['High']:
                sig_key = f"{symbol}_BEAR_DIV"
                if sig_key not in sent_alerts['alerts']:
                    new_alerts.append(f"📉 {name}({symbol}): RSI 하락 다이버전스 출현!!")
                    sent_alerts['alerts'].append(sig_key)

        # 2. 봇의 지지선 로직 (구글 v80 checkTrueRetest 방식)
        st_pivots = get_pivots(df_d, lookback=60, filter_size=3, gap=5, mode='low')
        st_msg = check_true_retest(df_d, st_pivots, "단기 지지선")
        if st_msg:
            sig_key = f"{symbol}_ST_RETEST"
            if sig_key not in sent_alerts['alerts']:
                new_alerts.append(f"🛡️ {name}({symbol}): {st_msg}")
                sent_alerts['alerts'].append(sig_key)

        lt_pivots = get_pivots(df_d, lookback=180, filter_size=15, gap=20, mode='low')
        lt_msg = check_true_retest(df_d, lt_pivots, "장기 지지선")
        if lt_msg:
            sig_key = f"{symbol}_LT_RETEST"
            if sig_key not in sent_alerts['alerts']:
                new_alerts.append(f"🏰 {name}({symbol}): {lt_msg}")
                sent_alerts['alerts'].append(sig_key)

        # 3. 봇의 저항선 로직 (구글 v80 checkResistanceStatus 방식)
        res_pivots = get_pivots(df_d, lookback=150, filter_size=15, gap=15, mode='high')
        res_msg = check_resistance_status(df_d, res_pivots)
        if res_msg:
            sig_key = f"{symbol}_RES_STATUS"
            if sig_key not in sent_alerts['alerts']:
                new_alerts.append(f"🎯 {name}({symbol}): {res_msg}")
                sent_alerts['alerts'].append(sig_key)

    except Exception as e: continue

if new_alerts:
    msg = "⚖️ 봇의 종합 추세 및 다이버전스 알림\n" + "-" * 20 + "\n" + "\n\n".join(new_alerts)
    send_message(msg)
    save_sent_alerts(sent_alerts)
