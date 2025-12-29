import yfinance as yf
import pandas as pd
import requests
import os

token = os.getenv('TELEGRAM_TOKEN')
chat_id = os.getenv('TELEGRAM_CHAT_ID')

def send_message(text):
    if not token or not chat_id:
        print("토큰이나 채팅 아이디 설정이 누락되었다이다")
        return
    if len(text) > 4000: 
        text = text[:4000] + "...(중략)"
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    params = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'Markdown'
    }
    try: 
        requests.get(url, params=params)
    except Exception as e: 
        print(f"전송 중 오류 발생했다이다: {e}")

def calculate_rsi(data, window=14):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_macds(data, fast=12, slow=26, signal=9):
    exp1 = data.ewm(span=fast, adjust=False).mean()
    exp2 = data.ewm(span=slow, adjust=False).mean()
    macd = exp1 - exp2
    signal_line = macd.ewm(span=signal, adjust=False).mean()
    hist = macd - signal_line
    return macd, signal_line, hist

ticker_map = {
    'NVDA': '엔비디아', 'TSLA': '테슬라', 'AAPL': '애플', 'MSFT': '마이크로소프트', 
    'AMZN': '아마존', 'META': '메타', 'GOOGL': '구글', 'PLTR': '팔란티어', 
    'MSTR': '마이크로스트래티지', 'COIN': '코인베이스', 'AMD': 'AMD', 'NFLX': '넷플릭스', 
    'AVGO': '브로드컴', 'TQQQ': '나스닥3배레버', 'SOXL': '반도체3배레버', 'ARM': 'ARM', 
    'TSM': 'TSMC', 'MU': '마이크론', 'INTC': '인텔', 'SMCI': '슈퍼마이크로', 
    'PYPL': '페이팔', 'SQQQ': '나스닥3배인버스', 'SOXS': '반도체3배인버스', 'PANW': '팔로알토', 
    'COST': '코스트코', 'QCOM': '퀄컴', 'ASML': 'ASML', 'SNOW': '스노우플레이크', 
    'MARA': '마라톤디지털', 'RIOT': '라이엇플랫폼', 'VRT': '버티브 홀딩스', 
    'ANET': '아리스타 네트웍스', 'LLY': '일라이 릴리', 'NVO': '노보 노디스크'
}

tickers = list(ticker_map.keys())

rsi_30_list = []
bull_div_list = []
bear_div_list = []
support_smma7_list = [] # 7SMMA 지지 종목들이다
support_ma20_list = []  # 20일선 지지 종목들이다
long_trend_list = [] 
recommend_list = []

for symbol in tickers:
    name = ticker_map[symbol]
    try:
        # 1. 일봉 분석이다
        df_d = yf.download(symbol, period='2y', interval='1d', progress=False)
        if df_d.empty or len(df_d) < 200: continue
        if isinstance(df_d.columns, pd.MultiIndex): 
            df_d.columns = df_d.columns.get_level_values(0)
        
        df_d['RSI'] = calculate_rsi(df_d['Close'])
        df_d['MA200'] = df_d['Close'].rolling(window=200).mean()
        df_d['MA20'] = df_d['Close'].rolling(window=20).mean()
        df_d['SMMA7'] = df_d['Close'].ewm(alpha=1/7, adjust=False).mean()
        macd, signal, hist = calculate_macds(df_d['Close'])
        df_d['MACD_Hist'] = hist

        curr = df_d.iloc[-1]
        c_price = float(curr['Close'])
        c_rsi = float(curr['RSI'])
        c_ma200 = float(curr['MA200'])
        c_ma20 = float(curr['MA20'])
        c_smma7 = float(curr['SMMA7'])
        c_macd_h = float(curr['MACD_Hist'])

        if 28 <= c_rsi <= 33:
            rsi_30_list.append(f"{name}({symbol})")

        lookback = df_d.iloc[-25:-2]
        low_price_idx = lookback['Low'].idxmin()
        prev_low_price = float(lookback.loc[low_price_idx, 'Low'])
        prev_low_rsi = float(lookback.loc[low_price_idx, 'RSI'])
        if float(curr['Low']) < prev_low_price and c_rsi > prev_low_rsi and c_rsi < 45:
            bull_div_list.append(f"{name}({symbol})")

        high_price_idx = lookback['High'].idxmax()
        prev_high_price = float(lookback.loc[high_price_idx, 'High'])
        prev_high_rsi = float(lookback.loc[high_price_idx, 'RSI'])
        if float(curr['High']) > prev_high_
