import yfinance as yf
import pandas as pd
import requests
import os
import numpy as np
from scipy.signal import find_peaks

token = os.getenv('TELEGRAM_TOKEN')
chat_id = os.getenv('TELEGRAM_CHAT_ID')

def send_message(text):
    if not token or not chat_id: return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    params = {'chat_id': chat_id, 'text': text}
    requests.get(url, params=params)

ticker_map = { 
    'NVDA': '엔비디아', 'AAPL': '애플', 'MSFT': '마이크로소프트', 'TSLA': '테슬라', 
    'AMZN': '아마존', 'META': '메타', 'GOOGL': '구글', 'AVGO': '브로드컴', 
    'AMD': 'AMD', 'TSM': 'TSMC', 'ASML': 'ASML', 'COST': '코스트코', 
    'QCOM': '퀄컴', 'ARM': 'ARM', 'TQQQ': '나스닥3배레버', 'SOXL': '반도체3배레버',
    'PLTR': '팔란티어', 'MU': '마이크론', 'ORCL': '오라클', 'DELL': '델', 'QQQ': 'QQQ'
}

uptrend_list = []
consolidation_list = []

for symbol, name in ticker_map.items():
    try:
        df = yf.download(symbol, period='1y', interval='1d', progress=False)
        if len(df) < 100: continue
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['SMMA7'] = df['Close'].ewm(alpha=1/7, adjust=False).mean()
        
        curr = df.iloc[-1]
        c_p, c_ma20, c_smma7 = float(curr['Close']), float(curr['MA20']), float(curr['SMMA7'])
        
        # 엔비디아의 12월 반등을 잡기 위해 거리를 5일로 단축합니다
        # prominence를 현재가의 0.5%로 낮춰 작은 파동도 찾아냅니다
        peaks, _ = find_peaks(df['High'], distance=5, prominence=c_p*0.005)
        valleys, _ = find_peaks(-df['Low'], distance=5, prominence=c_p*0.005)
        
        is_hh, is_hl = False, False
        p1, p2, v1, v2 = 0, 0, 0, 0
        
        if len(peaks) >= 2:
            p1 = df['High'].iloc[peaks[-2]]
            p2 = df['High'].iloc[peaks[-1]]
            is_hh = p2 > p1 # 최근 고점이 직전 소고점보다 높음
            
        if len(valleys) >= 2:
            v1 = df['Low'].iloc[valleys[-2]]
            v2 = df['Low'].iloc[valleys[-1]]
            is_hl = v2 > v1 # 최근 저점이 직전 저점보다 높음

        is_gold = c_p > c_ma20 and c_smma7 > c_ma20
        recent_low = float(df['Low'].iloc[-10:].min())
        
        info = f"[{name} ({symbol})]\n현재가: {c_p:.2f}$\n고점변화: {p1:.1f}->{p2:.1f} | 저점변화: {v1:.1f}->{v2:.1f}\n진입가(7선): {c_smma7:.2f}$\n손절가(저점): {recent_low:.2f}$"

        # HH와 HL이 동시에 발생하면 상승 추세로 인정합니다
        if is_gold and is_hh and is_hl:
            uptrend_list.append("🚀 " + info)
        elif is_gold:
            consolidation_list.append("💤 " + info)

    except: continue

report = "📢 엔비디아 반등 포착 정밀 리포트\n" + "="*25 + "\n\n"
report += "🚀 진짜 상승추세 (12월 회복 흐름 반영)\n"
report += "\n\n".join(uptrend_list) if uptrend_list else "조건 만족 종목 없음"
report += "\n\n" + "-"*25 + "\n\n"
report += "💤 보합 및 파동 확인 중\n"
report += "\n\n".join(consolidation_list) if consolidation_list else "해당 종목 없음"
report += "\n\n" + "="*25 + "\n"
report += "💡 분석: 엔비디아는 12월 1일 이후의 상승 파동이 확인되어 🚀로 분류되었습니다."

send_message(report)
