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
support_smma7_list = []
resistance_smma7_list = []
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
        df_d['SMMA7'] = df_d['Close'].ewm(alpha=1/7, adjust=False).mean()
        macd, signal, hist = calculate_macds(df_d['Close'])
        df_d['MACD_Hist'] = hist

        curr = df_d.iloc[-1]
        prev = df_d.iloc[-2]
        c_price = float(curr['Close'])
        c_rsi = float(curr['RSI'])
        c_ma200 = float(curr['MA200'])
        c_smma7 = float(curr['SMMA7'])
        c_macd_h = float(curr['MACD_Hist'])
        p_macd_h = float(prev['MACD_Hist'])

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
        if float(curr['High']) > prev_high_price and c_rsi < prev_high_rsi and c_rsi > 55:
            bear_div_list.append(f"{name}({symbol})")

        is_near_smma7 = abs(c_price - c_smma7) / c_smma7 <= 0.01
        if is_near_smma7:
            if c_price >= c_smma7: support_smma7_list.append(f"{name}({symbol})")
            else: resistance_smma7_list.append(f"{name}({symbol})")

        # 2. 주봉 분석이다
        df_w = yf.download(symbol, period='2y', interval='1wk', progress=False)
        if not df_w.empty and len(df_w) >= 21:
            if isinstance(df_w.columns, pd.MultiIndex): 
                df_w.columns = df_w.columns.get_level_values(0)
            df_w['WSMMA7'] = df_w['Close'].ewm(alpha=1/7, adjust=False).mean()
            df_w['WMA20'] = df_w['Close'].rolling(window=20).mean()
            w_curr = df_w.iloc[-1]
            w_prev = df_w.iloc[-2]
            w_c_price = float(w_curr['Close'])
            w_c_smma7 = float(w_curr['WSMMA7'])
            w_c_ma20 = float(w_curr['WMA20'])
            is_w_gc = float(w_prev['WSMMA7']) < float(w_prev['WMA20']) and w_c_smma7 > w_c_ma20
            is_above_ma = w_c_price > w_c_smma7 and w_c_price > w_c_ma20
            if is_w_gc or is_above_ma:
                long_trend_list.append(f"{name}({symbol})")

        # 3. 매수 추천 로직이다
        is_long_term_uptrend = c_price > c_ma200
        is_macd_reversal = p_macd_h < 0 and c_macd_h > p_macd_h
        if is_long_term_uptrend and (c_rsi < 40 or any(symbol in d for d in bull_div_list)) and is_macd_reversal:
            recommend_list.append(f"{name}({symbol})")

    except Exception as e:
        print(f"{symbol} 분석 중 오류이다: {e}")
        continue

report = []
report.append("📢 실시간 주식 분석 리포트이다")
report.append("-" * 20)
report.append("1. RSI 30 부근 (바닥권):")
report.append(", ".join(rsi_30_list) if rsi_30_list else "없음")
report.append("\n2. 상승 다이버전스 (반등 신호):")
report.append(", ".join(bull_div_list) if bull_div_list else "없음")
report.append("\n3. 하락 다이버전스 (하락 신호):")
report.append(", ".join(bear_div_list) if bear_div_list else "없음")
report.append("\n4. 7SMMA 지지/저항:")
report.append(f"\n지지(롱)\n {', '.join(support_smma7_list) if support_smma7_list else '없음'}")
report.append(f"\n저항(숏)\n {', '.join(resistance_smma7_list) if resistance_smma7_list else '없음'}")
report.append("\n5. 장기 상승 추세 종목:")
report.append(", ".join(long_trend_list) if long_trend_list else "없음")
report.append("-" * 20)
report.append("💡 오늘의 매수 추천 종목:")
report.append(", ".join(recommend_list) if recommend_list else "없음")

send_message("\n".join(report))
