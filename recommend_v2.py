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
        
        peaks, _ = find_peaks(df['High'], distance=5, prominence=c_p*0.005)
        valleys, _ = find_peaks(-df['Low'], distance=5, prominence=c_p*0.005)
        
        is_hh, is_hl = False, False
        if len(peaks) >= 2:
            is_hh = df['High'].iloc[peaks[-1]] > df['High'].iloc[peaks[-2]]
        if len(valleys) >= 2:
            is_hl = df['Low'].iloc[valleys[-1]] > df['Low'].iloc[valleys[-2]]

        is_gold = c_p > c_ma20 and c_smma7 > c_ma20
        recent_low = float(df['Low'].iloc[-10:].min())
        
        info = (f"[{name} ({symbol})]\n"
                f"현재가: {c_p:.2f}$\n"
                f"진입가(7선): {c_smma7:.2f}$\n"
                f"진입가(20선): {c_ma20:.2f}$\n"
                f"단기 손절(20선): {c_ma20:.2f}$\n"
                f"장기 손절(최근저점): {recent_low:.2f}$")

        if is_gold and is_hh and is_hl:
            uptrend_list.append("🚀 " + info)
        elif is_gold:
            consolidation_list.append("💤 " + info)

    except: continue

report = "📢 주가 포착 정밀 리포트이다\n" + "="*25 + "\n\n"
report += "🚀 찐 상승추세 (전환 확인)이다\n"
report += "\n\n".join(uptrend_list) if uptrend_list else "조건 만족 종목 없음이다"
report += "\n\n" + "-"*25 + "\n\n"
report += "💤 보합 및 파동 확인 중이다\n"
report += "\n\n".join(consolidation_list) if consolidation_list else "해당 종목 없음이다"
report += "\n\n" + "="*25 + "\n"
report += "💡 매매 가이드이다\n"
report += "1. 단기 손절: 7선이나 20선에서 매수했더라도 일봉 종가가 20선 아래로 마감되어 추세가 하방으로 바뀌면 손절을 권장한다이다.\n"
report += "2. 장기 손절: 상승 추세를 믿고 홀딩하는 경우에도 전 저점을 이탈하면 추세가 완전히 바뀐 것이므로 손절을 추천한다이다."

send_message(report)
