import yfinance as yf
import pandas as pd
import requests
import os

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

uptrend_gold = []    # 🚀 그룹: HH+HL(상승추세) + 골든크로스이다
recovery_gold = []   # ⚠️ 그룹: 골든크로스이나 아직 HH/HL 미달성(반등 시도)이다

for symbol, name in ticker_map.items():
    try:
        df = yf.download(symbol, period='1y', interval='1d', progress=False)
        if len(df) < 60: continue
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

        # 지표 계산이다
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['SMMA7'] = df['Close'].ewm(alpha=1/7, adjust=False).mean()
        
        curr = df.iloc[-1]
        c_p, c_ma20, c_smma7 = float(curr['Close']), float(curr['MA20']), float(curr['SMMA7'])
        
        # 다우 이론: 한 달(20일) 기준 고점/저점 비교이다
        recent = df.iloc[-20:]
        prev = df.iloc[-40:-20]
        c_h, c_l = float(recent['High'].max()), float(recent['Low'].min())
        p_h, p_l = float(prev['High'].max()), float(prev['Low'].min())
        
        # 도식에 따른 추세 판독이다
        is_hh = c_h > p_h # Higher High (고점 상승)이다
        is_hl = c_l > p_l # Higher Low (저점 상승)이다
        is_gold = c_p > c_ma20 and c_smma7 > c_ma20 # 골든크로스 상태이다
        
        recent_low = float(df['Low'].iloc[-10:].min())
        info = f"[{name} ({symbol})]\n현재가: {c_p:.2f}$\n진입가(7선): {c_smma7:.2f}$\n진입가(20선): {c_ma20:.2f}$\n손절가(저점): {recent_low:.2f}$"

        if is_gold:
            if is_hh and is_hl:
                uptrend_gold.append("🚀 " + info)
            else:
                recovery_gold.append("⚠️ " + info)

    except: continue

report = "📢 다우 이론 기반 이상적인 전략 리포트\n" + "="*25 + "\n\n"
report += "🚀 상승추세(HH+HL) + 골드크로스이다\n"
report += "\n\n".join(uptrend_gold) if uptrend_gold else "해당 종목 없음"
report += "\n\n" + "-"*25 + "\n\n"
report += "⚠️ 골드크로스 발생 + 추세 확인 중 (반등 시도)\n"
report += "\n\n".join(recovery_gold) if recovery_gold else "해당 종목 없음이다"
report += "\n\n" + "="*25 + "\n"
report += "💡 가이드: 🚀는 7선 눌림목 매수, ⚠️는 20선 지지 확인 후 진입하라"

send_message(report)
