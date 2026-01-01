import yfinance as yf
import pandas as pd
import requests
import os
import numpy as np
import json
from datetime import datetime

# 1. 환경 설정 및 세션 로드
token = os.getenv('TELEGRAM_TOKEN') or '7971022798:AAFGQR1zxdCq1urZKgdRzjjsvr3Lt6T9y1I'
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
    params = {'chat_id': chat_id, 'text': text} # 마크다운은 특수문자 오류가 잦아 일반 텍스트로 보낸다이다
    requests.get(url, params=params)

def calculate_rsi(data, window=14):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# 전문가 방식: 피벗 포인트를 이용한 다이버전스 감지 함수이다
def detect_divergence(df, window=5):
    # window는 좌우 몇 개의 캔들보다 높거나 낮아야 하는지를 결정한다이다
    bull_div = False
    bear_div = False
    
    # 최근 2개의 저점/고점 피벗을 찾는다이다
    low_pivots = []
    high_pivots = []
    
    # 캔들 끝부분(최근 캔들)부터 역순으로 스캔하여 피벗을 탐색한다이다
    for i in range(len(df) - window - 1, window, -1):
        # 저점 피벗 확인 (Low 기준)
        is_low_pivot = True
        for j in range(1, window + 1):
            if df['Low'].iloc[i] >= df['Low'].iloc[i-j] or df['Low'].iloc[i] >= df['Low'].iloc[i+j]:
                is_low_pivot = False; break
        if is_low_pivot:
            low_pivots.append(i)
        
        # 고점 피벗 확인 (High 기준)
        is_high_pivot = True
        for j in range(1, window + 1):
            if df['High'].iloc[i] <= df['High'].iloc[i-j] or df['High'].iloc[i] <= df['High'].iloc[i+j]:
                is_high_pivot = False; break
        if is_high_pivot:
            high_pivots.append(i)
            
        if len(low_pivots) >= 2 and len(high_pivots) >= 2: break

    # 일반 상승 다이버전스 (Regular Bullish): 가격 저점 낮아짐 + RSI 저점 높아짐
    if len(low_pivots) >= 2:
        p1, p2 = low_pivots[1], low_pivots[0] # p1이 과거, p2가 최근
        if df['Low'].iloc[p2] < df['Low'].iloc[p1] and df['RSI'].iloc[p2] > df['RSI'].iloc[p1]:
            # 마지막 캔들이 최근 피벗 이후 반등 중인지 확인한다이다
            if df['Close'].iloc[-1] > df['Low'].iloc[p2]:
                bull_div = True
                
    # 일반 하락 다이버전스 (Regular Bearish): 가격 고점 높아짐 + RSI 고점 낮아짐
    if len(high_pivots) >= 2:
        p1, p2 = high_pivots[1], high_pivots[0]
        if df['High'].iloc[p2] > df['High'].iloc[p1] and df['RSI'].iloc[p2] < df['RSI'].iloc[p1]:
            if df['Close'].iloc[-1] < df['High'].iloc[p2]:
                bear_div = True
                
    return bull_div, bear_div

# 기존 추세선 로직들이다 (수정 없이 유지)
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

def check_true_retest(df, pivots, label):
    if len(pivots) < 2: return None
    p2, p1 = pivots[0], pivots[1] 
    idx_now = len(df) - 1
    cp = float(df['Low'].iloc[-1])
    m = (p2['val'] - p1['val']) / (p2['idx'] - p1['idx'])
    line_now = m * (idx_now - p1['idx']) + p1['val']
    margin = 0.015
    if cp < line_now:
        had_breakdown = False
        for i in range(2, 8):
            line_past = m * (idx_now - i - p1['idx']) + p1['val']
            if df['Low'].iloc[-i] > line_past:
                had_breakdown = True; break
        if had_breakdown and (line_now - cp) / line_now < margin:
            return f"🔄 주의: {label} 이탈 후 저항 리테스트 중 (매도 타점)"
        return f"🚨 {label} 이탈 상태 (주의 요망)"
    return None

def check_resistance_status(df, res_pivots):
    if len(res_pivots) < 2: return None
    p2, p1 = res_pivots[0], res_pivots[1]
    idx_now = len(df) - 1
    cp = float(df['Close'].iloc[-1])
    m = (p2['val'] - p1['val']) / (p2['idx'] - p1['idx'])
    res_line = m * (idx_now - p1['idx']) + p1['val']
    margin = 0.015
    if cp > res_line:
        had_breakout = False
        for i in range(2, 8):
            line_past = m * (idx_now - i - p1['idx']) + p1['val']
            if df['Close'].iloc[-i] < line_past:
                had_breakout = True; break
        if had_breakout and (cp - res_line) / res_line < margin:
            return f"🔄 알림: 장기 저항 돌파 후 지지 리테스트 중 (강력 매수 타점)"
        return f"🔥 장기 저항 돌파 상태입니다. 매수 고려!"
    else:
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
        
        # 1. 전문가급 다이버전스 분석 적용이다
        bull_div, bear_div = detect_divergence(df_d, window=5)
        
        if bull_div:
            sig_key = f"{symbol}_BULL_DIV"
            if sig_key not in sent_alerts['alerts']:
                new_alerts.append(f"📈 {name}({symbol}): [전문가] RSI 상승 다이버전스 포착!!")
                sent_alerts['alerts'].append(sig_key)
        
        if bear_div:
            sig_key = f"{symbol}_BEAR_DIV"
            if sig_key not in sent_alerts['alerts']:
                new_alerts.append(f"📉 {name}({symbol}): [전문가] RSI 하락 다이버전스 포착!!")
                sent_alerts['alerts'].append(sig_key)

        # 2 & 3. 추세선 및 저항선 로직 실행이다
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

        res_pivots = get_pivots(df_d, lookback=150, filter_size=15, gap=15, mode='high')
        res_msg = check_resistance_status(df_d, res_pivots)
        if res_msg:
            sig_key = f"{symbol}_RES_STATUS"
            if sig_key not in sent_alerts['alerts']:
                new_alerts.append(f"🎯 {name}({symbol}): {res_msg}")
                sent_alerts['alerts'].append(sig_key)

    except Exception as e: continue

if new_alerts:
    msg = "⚖️ 봇의 종합 추세 및 전문가 다이버전스 알림\n" + "-" * 20 + "\n" + "\n\n".join(new_alerts)
    send_message(msg)
    save_sent_alerts(sent_alerts)
