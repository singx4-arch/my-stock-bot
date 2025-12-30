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

def check_new_touch(df):
    """현재는 하단 아래인데 이전에는 하단 위에 있었는지 확인한다이다"""
    if len(df) < 21: return False, 0
    
    ma20 = df['Close'].rolling(window=20).mean()
    std = df['Close'].rolling(window=20).std()
    lower_bb = ma20 - (std * 2)
    
    curr_p = float(df.iloc[-1]['Close'])
    prev_p = float(df.iloc[-2]['Close'])
    curr_l = float(lower_bb.iloc[-1])
    prev_l = float(lower_bb.iloc[-2])
    
    # 새로운 진입 조건: 지금은 하단 터치(이하), 직전에는 하단 위
    is_touch = curr_p <= curr_l and prev_p > prev_l
    gap = ((curr_l - curr_p) / curr_l) * 100 if curr_l > 0 else 0
    
    return is_touch, gap

daily_buy_list = []
weekly_buy_list = []

for symbol, name in ticker_map.items():
    try:
        # 1. 일봉 분석이다
        df_d = yf.download(symbol, period='60d', interval='1d', progress=False)
        if isinstance(df_d.columns, pd.MultiIndex): df_d.columns = df_d.columns.get_level_values(0)
        
        is_d_touch, d_gap = check_new_touch(df_d)
        if is_d_touch:
            daily_buy_list.append(f"{name}({symbol}) 괴리율:{d_gap:+.2f}%")

        # 2. 주봉 분석이다
        df_w = yf.download(symbol, period='2y', interval='1wk', progress=False)
        if isinstance(df_w.columns, pd.MultiIndex): df_w.columns = df_w.columns.get_level_values(0)
        
        is_w_touch, w_gap = check_new_touch(df_w)
        if is_w_touch:
            weekly_buy_list.append(f"{name}({symbol}) 괴리율:{w_gap:+.2f}%")
            
    except:
        continue

if daily_buy_list or weekly_buy_list:
    report = []
    report.append("💎 볼린저 밴드 새로운 바닥 진입 알람이다")
    report.append("-" * 20)
    
    if daily_buy_list:
        report.append("🔵 [단기 매수 자리] 일봉 하단 신규 접촉:")
        report.append(", ".join(daily_buy_list))
    
    if weekly_buy_list:
        report.append("\n🔴 [!!무조건 매수!!] 주봉 하단 신규 접촉:")
        report.append(", ".join(weekly_buy_list))
    
    report.append("-" * 20)
    report.append("밴드 안에서 밖으로 막 진입한 종목들이다.")
    
    send_message("\n".join(report))
