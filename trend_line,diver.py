import yfinance as yf
import pandas as pd
import requests
import os
import numpy as np
import json
from datetime import datetime

# 1. 환경 설정 및 세션 로드이다
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
    params = {'chat_id': chat_id, 'text': text}
    requests.get(url, params=params)

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
    if len(pivots) < 2: return None, None
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
            return f"🔄 {label} 이탈 후 저항 리테스트 중 (매도 타점)", "caution"
        return f"🚨 {label} 이탈 상태 (주의 요망)", "danger"
    return None, None

def check_resistance_status(df, res_pivots):
    if len(res_pivots) < 2: return None, None
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
            return "🔄 장기 저항 돌파 후 지지 리테스트 중 (강력 매수 타점)", "opportunity"
        return "🔥 장기 저항 돌파 상태 (매수 고려)", "opportunity"
    else:
        if (res_line - cp) / res_line < margin:
            return "🎯 장기 저항선에 근접 (돌파 주시)", "caution"
    return None, None

def main():
    ticker_map = { 
        'NVDA': '엔비디아', 'AAPL': '애플', 'MSFT': '마이크로소프트', 'TSLA': '테슬라', 
        'AMZN': '아마존', 'META': '메타', 'GOOGL': '구글', 'AVGO': '브로드컴', 
        'AMD': 'AMD', 'TSM': 'TSMC', 'ASML': 'ASML', 'COST': '코스트코', 
        'QCOM': '퀄컴', 'ARM': 'ARM', 'TQQQ': '나스닥3배', 'SOXL': '반도체3배',
        'PLTR': '팔란티어', 'MU': '마이크론', 'ORCL': '오라클', 'DELL': '델', 'QQQ': 'QQQ'
    }

    today_str = datetime.now().strftime('%Y-%m-%d')
    sent_alerts = load_sent_alerts()
    if sent_alerts.get('date') != today_str:
        sent_alerts = {'date': today_str, 'alerts': []}

    categories = {
        "opportunity": [], # 🟢 기회
        "caution": [],     # 🟡 주의
        "danger": []       # 🔴 위험
    }

    for symbol, name in ticker_map.items():
        try:
            df_d = yf.download(symbol, period='1y', interval='1d', progress=False)
            if len(df_d) < 200: continue
            if isinstance(df_d.columns, pd.MultiIndex): df_d.columns = df_d.columns.get_level_values(0)
            
            # 1. 단기 지지선
            st_pivots = get_pivots(df_d, lookback=60, filter_size=3, gap=5, mode='low')
            msg, cat = check_true_retest(df_d, st_pivots, "단기 지지선")
            if msg and f"{symbol}_ST_{cat}" not in sent_alerts['alerts']:
                categories[cat].append(f"🛡️ {name}({symbol}): {msg}")
                sent_alerts['alerts'].append(f"{symbol}_ST_{cat}")

            # 2. 장기 지지선
            lt_pivots = get_pivots(df_d, lookback=180, filter_size=15, gap=20, mode='low')
            msg, cat = check_true_retest(df_d, lt_pivots, "장기 지지선")
            if msg and f"{symbol}_LT_{cat}" not in sent_alerts['alerts']:
                categories[cat].append(f"🏰 {name}({symbol}): {msg}")
                sent_alerts['alerts'].append(f"{symbol}_LT_{cat}")

            # 3. 장기 저항선
            res_pivots = get_pivots(df_d, lookback=150, filter_size=15, gap=15, mode='high')
            msg, cat = check_resistance_status(df_d, res_pivots)
            if msg and f"{symbol}_RES_{cat}" not in sent_alerts['alerts']:
                categories[cat].append(f"🎯 {name}({symbol}): {msg}")
                sent_alerts['alerts'].append(f"{symbol}_RES_{cat}")

        except Exception as e: continue

    # 리포트 구성이다
    final_report = "🏛️ 봇의 종합 추세 분석 리포트 (v143)\n"
    final_report += f"분석 일시: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
    final_report += "=" * 25 + "\n\n"

    has_content = False
    if categories["opportunity"]:
        final_report += "🟢 [강력 매수 및 돌파 구간]\n"
        final_report += "\n".join(categories["opportunity"]) + "\n\n"
        has_content = True

    if categories["caution"]:
        final_report += "🟡 [매도 및 저항 확인 구간]\n"
        final_report += "\n".join(categories["caution"]) + "\n\n"
        has_content = True

    if categories["danger"]:
        final_report += "🔴 [지지선 이탈 및 하락 경고]\n"
        final_report += "\n".join(categories["danger"]) + "\n\n"
        has_content = True

    if has_content:
        send_message(final_report)
        save_sent_alerts(sent_alerts)

if __name__ == "__main__":
    main()
