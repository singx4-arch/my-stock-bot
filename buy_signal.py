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
    'NVDA': '엔비디아', 'TSLA': '테슬라', 'AAPL': '애플', 'MSFT': '마이크로소프트',
    'AMZN': '아마존', 'META': '메타', 'GOOGL': '구글', 'AMD': 'AMD',
    'AVGO': '브로드컴', 'MU': '마이크론', 'ARM': 'ARM', 'NFLX': '넷플릭스',
    'PANW': '팔로알토', 'QCOM': '퀄컴', 'ASML': 'ASML'
}

def get_lower_bb(df):
    if len(df) < 20: return None, None
    ma20 = df['Close'].rolling(window=20).mean()
    std = df['Close'].rolling(window=20).std()
    lower_bb = ma20 - (std * 2)
    return float(df.iloc[-1]['Close']), float(lower_bb.iloc[-1])

daily_buy_list = []   # 일봉 하단 접촉이다
weekly_buy_list = []  # 주봉 하단 접촉이다

for symbol, name in ticker_map.items():
    try:
        # 1. 일봉 분석 (단기 매수 타점)이다
        df_d = yf.download(symbol, period='60d', interval='1d', progress=False)
        if isinstance(df_d.columns, pd.MultiIndex): df_d.columns = df_d.columns.get_level_values(0)
        p_d, l_d = get_lower_bb(df_d)
        
        if p_d is not None and p_d <= l_d:
            daily_buy_list.append(f"{name}({symbol})")

        # 2. 주봉 분석 (강력 매수 타점)이다
        df_w = yf.download(symbol, period='2y', interval='1wk', progress=False)
        if isinstance(df_w.columns, pd.MultiIndex): df_w.columns = df_w.columns.get_level_values(0)
        p_w, l_w = get_lower_bb(df_w)
        
        if p_w is not None and p_w <= l_w:
            weekly_buy_list.append(f"{name}({symbol})")
            
    except:
        continue

# 리포트 발송이다
if daily_buy_list or weekly_buy_list:
    report = []
    report.append("💎 볼린저 밴드 바닥 탐지 리포트이다")
    report.append("-" * 20)
    
    report.append("🔵 [단기 매수 자리] 일봉 하단 접촉:")
    report.append(", ".join(daily_buy_list) if daily_buy_list else "없음")
    
    report.append("\n🔴 [!!무조건 매수!!] 주봉 하단 접촉:")
    report.append(", ".join(weekly_buy_list) if weekly_buy_list else "없음")
    
    report.append("-" * 20)
    report.append("주봉 하단 접촉은 매우 강력한 바닥 신호일 확률이 높다이다.")
    
    send_message("\n".join(report))
