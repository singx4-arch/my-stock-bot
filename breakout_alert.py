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

# 15개 핵심 종목 리스트이다
ticker_map = {
    'NVDA': '엔비디아', 'TSLA': '테슬라', 'AAPL': '애플', 'MSFT': '마이크로소프트',
    'AMZN': '아마존', 'META': '메타', 'GOOGL': '구글', 'AMD': 'AMD',
    'AVGO': '브로드컴', 'MU': '마이크론', 'ARM': 'ARM', 'NFLX': '넷플릭스',
    'PANW': '팔로알토', 'QCOM': '퀄컴', 'ASML': 'ASML'
}

breakout_list = []

for symbol, name in ticker_map.items():
    try:
        # 최근 22일치 데이터를 가져온다 (20일 고점을 계산하기 위함이다)
        df = yf.download(symbol, period='1mo', interval='1d', progress=False)
        if len(df) < 21: continue
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

        # 오늘을 제외한 최근 20일간의 최고가이다
        prev_high_20 = float(df.iloc[-21:-1]['High'].max())
        
        # 현재 가격과 직전 가격을 비교하기 위해 1시간 봉 데이터를 가져온다이다
        df_1h = yf.download(symbol, period='2d', interval='1h', progress=False)
        if isinstance(df_1h.columns, pd.MultiIndex): df_1h.columns = df_1h.columns.get_level_values(0)
        
        curr_p = float(df_1h.iloc[-1]['Close'])
        prev_p = float(df_1h.iloc[-2]['Close'])

        # 돌파 조건: 현재는 20일 고점보다 높은데, 직전에는 고점 아래였을 때만이다
        if curr_p > prev_high_20 and prev_p <= prev_high_20:
            diff = ((curr_p - prev_high_20) / prev_high_20) * 100
            breakout_list.append(f"🚀 {name}({symbol}): 20일 전고점 돌파! (현재가:{curr_p}$, +{diff:+.2f}%)")

    except:
        continue

if breakout_list:
    msg = "🔥 [돌파 신호] 전고점 돌파 종목 포착이다\n" + "-" * 20 + "\n"
    msg += "\n".join(breakout_list)
    msg += "\n\n강력한 추세 상승의 시작일 가능성이 높다이다."
    send_message(msg)
