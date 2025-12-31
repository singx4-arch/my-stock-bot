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

uptrend_gold = []    # 1. 골크 + 상승 추세이다
recovery_attempt = [] # 2. 하락 추세 + 상승 가능성이다

for symbol, name in ticker_map.items():
    try:
        df = yf.download(symbol, period='1y', interval='1d', progress=False)
        if len(df) < 50: continue
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['SMMA7'] = df['Close'].ewm(alpha=1/7, adjust=False).mean()
        
        curr = df.iloc[-1]
        c_p, c_ma20, c_smma7 = float(curr['Close']), float(curr['MA20']), float(curr['SMMA7'])
        
        # 다우 이론 (20일 기준 비교)이다
        recent = df.iloc[-20:]
        prev = df.iloc[-40:-20]
        c_h, c_l = float(recent['High'].max()), float(recent['Low'].min())
        p_h, p_l = float(prev['High'].max()), float(prev['Low'].min())
        
        recent_low = float(df['Low'].iloc[-10:].min())
        
        # 종목별 상세 정보 구성이다 (요청하신 진입가/손절가 명시)이다
        info = f"[{name} ({symbol})]\n"
        info += f"현재가: {c_p:.2f}$\n"
        info += f"진입가(7선): {c_smma7:.2f}$\n"
        info += f"진입가(20선): {c_ma20:.2f}$\n"
        info += f"손절가(저점): {recent_low:.2f}$"

        # 로직 분류이다
        if c_p > c_ma20 and c_smma7 > c_ma20 and c_h > p_h and c_l > p_l:
            uptrend_gold.append("🚀 " + info)
        elif (c_p > c_ma20 or c_l > p_l):
            if abs(c_p - c_ma20)/c_ma20 <= 0.02:
                recovery_attempt.append("🛡️ " + info)

    except: continue

# 리포트 조립이다
report = "📢 오늘의 매수 전략 리포트이다\n" + "="*25 + "\n\n"
report += "🚀 골크 + 상승 추세 종목 (추세 매수)이다\n"
report += "\n\n".join(uptrend_gold) if uptrend_gold else "조건 만족 종목 없음이다"
report += "\n\n" + "-"*25 + "\n\n"
report += "🛡️ 하락 추세 + 상승 가능성 (반전 매수)이다\n"
report += "\n\n".join(recovery_attempt) if recovery_attempt else "조건 만족 종목 없음이다"
report += "\n\n" + "="*25 + "\n"

report += "💡 투자 가이드이다\n"
report += "1. 가장 안전한 타점: 🚀 그룹에 있는 종목이 주가가 살짝 눌려서 7smma(7선)에 닿았을 때가 가장 승률이 높다이다.\n"
report += "2. 역전의 기회: 🛡️ 그룹에 있는 종목은 손절가가 매우 짧기 때문에, 20일선 이탈을 손절 잡고 진입하면 손익비가 좋은 자리가 된다이다."

send_message(report)
