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

# 1. 상승추세 + 골드크로스 (강력 추천)이다
uptrend_gold = []
# 2. 골드크로스 발생했으나 다우이론 추세 하락 (주의/반전 시도)이다
gold_cross_but_dow_down = []

for symbol, name in ticker_map.items():
    try:
        # 한 달(20일) 분석을 위해 1년치 데이터를 가져온다이다
        df = yf.download(symbol, period='1y', interval='1d', progress=False)
        if len(df) < 50: continue
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

        # 지표 계산이다
        # 20일 이동평균선이다
        df['MA20'] = df['Close'].rolling(window=20).mean()
        # 7일 SMMA (Smoothed Moving Average)이다
        # SMMA N은 EMA(alpha=1/N)과 동일한 원리이다이다
        df['SMMA7'] = df['Close'].ewm(alpha=1/7, adjust=False).mean()
        
        curr = df.iloc[-1]
        c_p, c_ma20, c_smma7 = float(curr['Close']), float(curr['MA20']), float(curr['SMMA7'])
        
        # 다우 이론 판독 (최근 한 달 20일 vs 이전 한 달 20일)이다
        recent = df.iloc[-20:] # 최근 20일이다
        prev = df.iloc[-40:-20] # 이전 20일이다
        c_h, c_l = float(recent['High'].max()), float(recent['Low'].min())
        p_h, p_l = float(prev['High'].max()), float(prev['Low'].min())
        
        # 공통 정보 출력 양식이다
        recent_low = float(df['Low'].iloc[-10:].min())
        info = f"[{name} ({symbol})]\n"
        info += f"현재가: {c_p:.2f}$\n"
        info += f"진입가(7선): {c_smma7:.2f}$\n"
        info += f"진입가(20선): {c_ma20:.2f}$\n"
        info += f"손절가(저점): {recent_low:.2f}$"

        # 조건 1: 골드크로스 여부 확인 (가격과 7선이 모두 20선 위이다)이다
        is_gold_cross = c_p > c_ma20 and c_smma7 > c_ma20

        # 조건 2: 다우이론 상승 추세 (고점과 저점 모두 상승)이다
        is_dow_uptrend = c_h > p_h and c_l > p_l

        # 분류이다
        if is_gold_cross and is_dow_uptrend:
            uptrend_gold.append("🚀 " + info)
        elif is_gold_cross and not is_dow_uptrend:
            gold_cross_but_dow_down.append("⚠️ " + info)

    except: continue

# 리포트 구성이다
report = "📢 오늘의 매수 전략 리포트\n" + "="*25 + "\n\n"
report += "🚀 상승추세 + 골드크로스 (순항 중)이다\n"
report += "\n\n".join(uptrend_gold) if uptrend_gold else "조건 만족 종목 없음"
report += "\n\n" + "-"*25 + "\n\n"
report += "⚠️ 골드크로스 발생 + 다우이론 추세 하락 (주의/반등)\n"
report += "\n\n".join(gold_cross_but_dow_down) if gold_cross_but_dow_down else "조건 만족 종목 없음이다"
report += "\n\n" + "="*25 + "\n"

report += "💡 투자 가이드이다\n"
report += "1. 가장 안전한 타점: 🚀 그룹에 있는 종목이 주가가 살짝 눌려서 7smma(7선)에 닿았을 때가 가장 승률이 높다.\n"
report += "2. 역전의 기회: ⚠️ 그룹에 있는 종목은 다우이론상 고점이 아직 낮지만, 20일선 지지 성공 시 추세 전환의 초입이 될 수 있다."

send_message(report)
