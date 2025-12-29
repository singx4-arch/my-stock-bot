import yfinance as yf
import pandas as pd
import requests
import os

# 깃허브 Secrets 정보 가져오기이다
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

def get_bb_status(df):
    """볼린저 밴드 계산 및 현재 상태 반환 함수이다"""
    if len(df) < 20: return None, None, None
    ma20 = df['Close'].rolling(window=20).mean()
    std = df['Close'].rolling(window=20).std()
    upper = ma20 + (std * 2)
    lower = ma20 - (std * 2)
    
    curr_price = float(df.iloc[-1]['Close'])
    curr_upper = float(upper.iloc[-1])
    curr_lower = float(lower.iloc[-1])
    return curr_price, curr_upper, curr_lower

bb_alarms = []

for symbol, name in ticker_map.items():
    try:
        # 1. 4시간 봉 확인이다
        df_4h = yf.download(symbol, period='30d', interval='4h', progress=False)
        if isinstance(df_4h.columns, pd.MultiIndex): df_4h.columns = df_4h.columns.get_level_values(0)
        p_4h, u_4h, l_4h = get_bb_status(df_4h)

        # 2. 1시간 봉 확인이다
        df_1h = yf.download(symbol, period='7d', interval='1h', progress=False)
        if isinstance(df_1h.columns, pd.MultiIndex): df_1h.columns = df_1h.columns.get_level_values(0)
        p_1h, u_1h, l_1h = get_bb_status(df_1h)

        if p_4h is None or p_1h is None: continue

        # 동시 이탈 조건 검사이다
        # 상단 동시 이탈이다
        if p_4h > u_4h and p_1h > u_1h:
            gap_4h = ((p_4h - u_4h) / u_4h) * 100
            bb_alarms.append(f"🚨 {name}({symbol}): 상단 이탈입니다 (4H+1H 동시 돌파, 괴리율 {gap_4h:+.2f}%)")
        
        # 하단 동시 이탈이다
        elif p_4h < l_4h and p_1h < l_1h:
            gap_4h = ((l_4h - p_4h) / l_4h) * 100
            bb_alarms.append(f"📉 {name}({symbol}): 하단 이탈입니다 (4H+1H 동시 이탈, 괴리율 {gap_4h:+.2f}%)")

    except:
        continue

# 동시 이탈 종목이 있을 때만 알람이다
if bb_alarms:
    msg = "⚠️ [강력 신호] 4시간/1시간 볼린저 밴드 동시 이탈이다\n" + "-" * 20 + "\n"
    msg += "\n".join(bb_alarms)
    msg += "\n\n두 시간대 모두 밴드를 벗어나 추세 전환 가능성이 매우 높다이다."
    send_message(msg)
