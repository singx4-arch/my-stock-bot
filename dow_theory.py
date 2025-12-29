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

# 재혁님이 요청한 나스닥 핵심 15개 우량주 리스트이다
ticker_map = {
    'NVDA': '엔비디아', 'TSLA': '테슬라', 'AAPL': '애플', 'MSFT': '마이크로소프트',
    'AMZN': '아마존', 'META': '메타', 'GOOGL': '구글', 'AMD': 'AMD',
    'AVGO': '브로드컴', 'MU': '마이크론', 'ARM': 'ARM', 'NFLX': '넷플릭스',
    'PANW': '팔로알토', 'QCOM': '퀄컴', 'ASML': 'ASML'
}

dow_trends = []

for symbol, name in ticker_map.items():
    try:
        df = yf.download(symbol, period='2mo', interval='1d', progress=False)
        if len(df) < 30: continue
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

        # 최근 5일간의 평균과 이전 20일간의 데이터를 비교한다이다
        recent = df.iloc[-5:]
        previous = df.iloc[-25:-5]

        curr_high = float(recent['High'].max())
        curr_low = float(recent['Low'].min())
        prev_high = float(previous['High'].max())
        prev_low = float(previous['Low'].min())

        # 다우 이론: 고점과 저점이 모두 이전보다 높아졌는가?
        is_higher_high = curr_high > prev_high
        is_higher_low = curr_low > prev_low

        # 거래량 확인: 최근 5일 평균 거래량이 이전 20일 평균보다 많은가?
        curr_vol_avg = float(recent['Volume'].mean())
        prev_vol_avg = float(previous['Volume'].mean())
        vol_confirmation = curr_vol_avg > prev_vol_avg

        if is_higher_high and is_higher_low:
            status = "📈 상승 추세 확정" if vol_confirmation else "↗️ 상승 추세 진행 중(거래량 미달)"
            dow_trends.append(f"✅ {name}({symbol})\n- 고점/저점 모두 상승했다이다.\n- {status}")
            
    except: continue

if dow_trends:
    msg = "🏛️ [다우 이론] 추세 분석 리포트이다\n" + "-" * 20 + "\n"
    msg += "\n\n".join(dow_trends)
    msg += "\n\n추세는 명확한 반전 신호가 있을 때까지 지속된다는 것이 다우 이론의 핵심이다이다."
    send_message(msg)
