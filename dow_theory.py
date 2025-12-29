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

# 나스닥 핵심 15개 우량 기술주 리스트이다
ticker_map = {
    'NVDA': '엔비디아', 'TSLA': '테슬라', 'AAPL': '애플', 'MSFT': '마이크로소프트',
    'AMZN': '아마존', 'META': '메타', 'GOOGL': '구글', 'AMD': 'AMD',
    'AVGO': '브로드컴', 'MU': '마이크론', 'ARM': 'ARM', 'NFLX': '넷플릭스',
    'PANW': '팔로알토', 'QCOM': '퀄컴', 'ASML': 'ASML'
}

trend_results = []

for symbol, name in ticker_map.items():
    try:
        df = yf.download(symbol, period='2mo', interval='1d', progress=False)
        if len(df) < 30: continue
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

        # 분석 구간 설정이다 (최근 5일 vs 이전 20일)
        recent = df.iloc[-5:]
        previous = df.iloc[-25:-5]

        curr_high = float(recent['High'].max())
        curr_low = float(recent['Low'].min())
        prev_high = float(previous['High'].max())
        prev_low = float(previous['Low'].min())

        # 다우 이론 추세 판별 로직이다
        # 1. 상승 추세: 고점과 저점이 모두 높아짐이다
        is_uptrend = curr_high > prev_high and curr_low > prev_low
        # 2. 하락 추세: 고점과 저점이 모두 낮아짐이다
        is_downtrend = curr_high < prev_high and curr_low < prev_low

        if is_uptrend:
            trend_results.append(f"📈 [상승 추세] {name}({symbol})\n- 이전보다 고점과 저점을 높이며 우상향 중이다.")
        elif is_downtrend:
            trend_results.append(f"📉 [하락 추세] {name}({symbol})\n- 이전보다 고점과 저점이 낮아지며 우하향 중이다.")
        else:
            trend_results.append(f"↔️ [보합/혼조] {name}({symbol})\n- 명확한 방향성 없이 박스권이나 변곡점에 있다.")
            
    except: continue

if trend_results:
    msg = "🏛️ [다우 이론] 실시간 추세 판독 리포트이다\n" + "-" * 20 + "\n"
    msg += "\n\n".join(trend_results)
    msg += "\n\n다우 이론에 따르면 추세는 반전 신호가 나오기 전까지 지속된다."
    send_message(msg)
