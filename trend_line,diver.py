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

# 봇의 로직: 구조적 변곡점(Pivot) 역추적 함수
def get_pivots(df, lookback=60, filter_size=3, gap=5, mode='low'):
    pivots = []
    prices = df['Low'] if mode == 'low' else df['High']
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

# 봇의 로직: 방향성 리테스트 감지 함수
def check_directional_retest(df, pivots, label):
    if len(pivots) < 2: return None
    p2, p1 = pivots[0], pivots[1] 
    idx_now = len(df) - 1
    cp, pp = float(df['Close'].iloc[-1]), float(df['Close'].iloc[-2])
    m = (p2['val'] - p1['val']) / (p2['idx'] - p1['idx'])
    line_now = m * (idx_now - p1['idx']) + p1['val']
    margin = 0.015

    if cp < line_now: # 이탈 리테스트
        had_breakdown = any(df['Low'].iloc[-i] > (m * (idx_now - i - p1['idx']) + p1['val']) for i in range(2, 8))
        if had_breakdown and (line_now - cp) / line_now < margin:
            if cp > pp: return f"🔄 {label} 이탈 후 저항 리테스트 중 (반등 시 매도 주의)"
    elif cp >= line_now: # 지지 리테스트
        had_breakout = any(df['Low'].iloc[-i] < (m * (idx_now - i - p1['idx']) + p1['val']) for i in range(2, 8))
        dist = (cp - line_now) / line_now
        if dist < margin:
            if had_breakout: return f"✅ {label} 돌파 후 지지 확인 중 (진짜 리테스트 매수 타점)"
            elif pp > cp: return f"🔄 {label} 눌림목 접근 중 (지지 여부 확인 필요)"
            elif cp > pp: return f"💎 {label} 지지 성공 후 반등 중"
    return None

# 2. 분석 대상 종목 설정
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

# 3. 메인 분석 루프
for symbol, name in ticker_map.items():
    try:
        df_d = yf.download(symbol, period='1y', interval='1d', progress=False)
        if len(df_d) < 200: continue
        if isinstance(df_d.columns, pd.MultiIndex): df_d.columns = df_d.columns.get_level_values(0)
        
        df_d['RSI'] = calculate_rsi(df_d['Close'])
        curr_p = float(df_d['Close'].iloc[-1])
        idx_d = len(df_d) - 1

        # --- 다이버전스 분석 로직 ---
        df_d['PH'] = df_d['High'][(df_d['High'] == df_d['High'].rolling(window=11, center=True).max())]
        df_d['PL'] = df_d['Low'][(df_d['Low'] == df_d['Low'].rolling(window=11, center=True).min())]
        pls = df_d.dropna(subset=['PL'])
        phs = df_d.dropna(subset=['PH'])

        # 상승 다이버전스
        if len(pls) >= 2:
            l1, l2 = pls.iloc[-2], pls.iloc[-1]
            if l2['Low'] < l1['Low'] and l2['RSI'] > l1['RSI'] and curr_p > l2['Low']:
                sig_key = f"{symbol}_BULL_DIV"
                if sig_key not in sent_alerts['alerts']:
                    new_alerts.append(f"📈 {name}({symbol}): RSI 상승 다이버전스 출현!!")
                    sent_alerts['alerts'].append(sig_key)

        # 하락 다이버전스
        if len(phs) >= 2:
            h1, h2 = phs.iloc[-2], phs.iloc[-1]
            if h2['High'] > h1['High'] and h2['RSI'] < h1['RSI'] and curr_p < h2['High']:
                sig_key = f"{symbol}_BEAR_DIV"
                if sig_key not in sent_alerts['alerts']:
                    new_alerts.append(f"📉 {name}({symbol}): RSI 하락 다이버전스 출현!!")
                    sent_alerts['alerts'].append(sig_key)

        # --- 봇의 로직 기반 지지선 분석 ---
        st_pivots = get_pivots(df_d, lookback=60, filter_size=3, gap=5, mode='low')
        st_retest_msg = check_directional_retest(df_d, st_pivots, "단기 지지선")
        if st_retest_msg:
            sig_key = f"{symbol}_ST_RETEST"
            if sig_key not in sent_alerts['alerts']:
                new_alerts.append(f"🛡️ {name}({symbol}): {st_retest_msg}")
                sent_alerts['alerts'].append(sig_key)

        lt_pivots = get_pivots(df_d, lookback=180, filter_size=15, gap=20, mode='low')
        lt_retest_msg = check_directional_retest(df_d, lt_pivots, "장기 지지선")
        if lt_retest_msg:
            sig_key = f"{symbol}_LT_RETEST"
            if sig_key not in sent_alerts['alerts']:
                new_alerts.append(f"🏰 {name}({symbol}): {lt_retest_msg}")
                sent_alerts['alerts'].append(sig_key)

        # --- 장기 저항선 분석 강화 (DELL 오류 해결 버전) ---
        res_pivots = get_pivots(df_d, lookback=150, filter_size=15, gap=15, mode='high')
        if len(res_pivots) >= 2:
            p2, p1 = res_pivots[0], res_pivots[1]
            m_res = (p2['val'] - p1['val']) / (p2['idx'] - p1['idx'])
            res_line = m_res * (idx_d - p1['idx']) + p1['val']
            
            if curr_p > res_line:
                had_breakout = any(df_d['Close'].iloc[-i] < (m_res * (idx_d - i - p1['idx']) + p1['val']) for i in range(2, 10))
                if had_breakout and (curr_p - res_line) / res_line < 0.015:
                    sig_key = f"{symbol}_RES_RETEST"
                    if sig_key not in sent_alerts['alerts']:
                        new_alerts.append(f"🔥 {name}({symbol}): 장기 저항 돌파 후 지지 리테스트 중!")
                        sent_alerts['alerts'].append(sig_key)
                elif had_breakout:
                    sig_key = f"{symbol}_RES_BREAK"
                    if sig_key not in sent_alerts['alerts']:
                        new_alerts.append(f"🚀 {name}({symbol}): 장기 저항 돌파 성공!")
                        sent_alerts['alerts'].append(sig_key)
            elif (res_line - curr_p) / res_line < 0.015:
                sig_key = f"{symbol}_RES_READY"
                if sig_key not in sent_alerts['alerts']:
                    new_alerts.append(f"🎯 {name}({symbol}): 장기 저항선 돌파 대기 중")
                    sent_alerts['alerts'].append(sig_key)

    except Exception as e: continue

# 4. 결과 전송
if new_alerts:
    msg = "⚖️ 봇의 종합 추세 및 다이버전스 알림\n" + "-" * 20 + "\n" + "\n\n".join(new_alerts)
    send_message(msg)
    save_sent_alerts(sent_alerts)
