import yfinance as yf
import pandas as pd
import requests
import os

token = os.getenv('TELEGRAM_TOKEN')
chat_id = os.getenv('TELEGRAM_CHAT_ID')

def send_message(text):
    if not token or not chat_id: return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    params = {'chat_id': chat_id, 'text': text, 'parse_mode': 'Markdown'}
    requests.get(url, params=params)

ticker_map = {
    'NVDA': '엔비디아', 'AAPL': '애플', 'MSFT': '마이크로소프트', 'TSLA': '테슬라', 
    'AMZN': '아마존', 'META': '메타', 'GOOGL': '구글', 'AVGO': '브로드컴', 
    'AMD': 'AMD', 'TSM': 'TSMC', 'ASML': 'ASML', 'COST': '코스트코', 
    'QCOM': '퀄컴', 'ARM': 'ARM', 'TQQQ': '나스닥3배레버', 'SOXL': '반도체3배레버',
    'PLTR': '팔란티어', 'MU': '마이크론', 'ORCL': '오라클', 'DELL': '델', 'QQQ': 'QQQ'
}

# 결과 저장을 위한 딕셔너리이다
results = {
    'short_up': [], 'short_down': [],
    'long_up': [], 'long_down': [],
    'break_20': [], 'break_60': []
}

for symbol, name in ticker_map.items():
    try:
        # 200일 이평선 계산을 위해 1년치 데이터를 가져온다이다
        df = yf.download(symbol, period='1y', interval='1d', progress=False)
        if len(df) < 200: continue
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

        curr_close = float(df['Close'].iloc[-1])
        ma200 = df['Close'].rolling(window=200).mean().iloc[-1]

        # 1. 단기 추세 (5일 단위)이다
        s_recent = df.iloc[-5:]
        s_prev = df.iloc[-10:-5]
        s_curr_h, s_curr_l = float(s_recent['High'].max()), float(s_recent['Low'].min())
        s_prev_h, s_prev_l = float(s_prev['High'].max()), float(s_prev['Low'].min())

        if s_curr_h > s_prev_h and s_curr_l > s_prev_l:
            results['short_up'].append(name)
        elif s_curr_h < s_prev_h and s_curr_l < s_prev_l:
            results['short_down'].append(name)

        # 2. 장기 추세 (20일 단위 + 200일선 필터)이다
        l_recent = df.iloc[-20:]
        l_prev = df.iloc[-40:-20]
        l_curr_h, l_curr_l = float(l_recent['High'].max()), float(l_recent['Low'].min())
        l_prev_h, l_prev_l = float(l_prev['High'].max()), float(l_prev['Low'].min())

        # 장기는 200일선 위에서 고점/저점이 모두 높아질 때만 상승으로 인정한다이다
        if curr_close > ma200 and l_curr_h > l_prev_h and l_curr_l > l_prev_l:
            results['long_up'].append(name)
        elif curr_close < ma200 or (l_curr_h < l_prev_h and l_curr_l < l_prev_l):
            results['long_down'].append(name)

        # 3. 돌파 확인 (20일 단기 / 60일 장기)이다
        high_20 = float(df.iloc[-21:-1]['High'].max())
        high_60 = float(df.iloc[-61:-1]['High'].max())

        if curr_close > high_20: results['break_20'].append(name)
        if curr_close > high_60: results['break_60'].append(name)

    except: continue

# 리포트 생성이다
report = ["🏛️ 통합 추세 및 다우 이론 리포트이다", "-" * 20]
report.append("1. 장기 추세 (20일 & 200MA 기준)이다")
report.append(f"🟢 상승 대세: {', '.join(results['long_up']) if results['long_up'] else '없음'}")
report.append(f"🔴 하락/주의: {', '.join(results['long_down']) if results['long_down'] else '없음'}")
report.append("")
report.append("2. 단기 추세 (5일 기준)이다")
report.append(f"📈 단기 상승: {', '.join(results['short_up']) if results['short_up'] else '없음'}")
report.append(f"📉 단기 하락: {', '.join(results['short_down']) if results['short_down'] else '없음'}")
report.append("")
report.append("3. 가격 돌파 신호이다")
report.append(f"🔥 장기(60일) 돌파: {', '.join(results['break_60']) if results['break_60'] else '없음'}")
report.append(f"⚡ 단기(20일) 돌파: {', '.join(results['break_20']) if results['break_20'] else '없음'}")

send_message("\n".join(report))
