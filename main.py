import yfinance as yf
import pandas as pd
import requests
import os

# 깃허브 Secrets 정보 가져오기이다
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

weekly_rsi_30_list = [] # 주봉 RSI 리스트이다
support_smma7_list = [] 
support_ma20_list = []  
long_trend_list = [] 
recommend_list = []

for symbol in tickers:
    name = ticker_map[symbol]
    try:
        # 1. 일봉 분석이다
        df_d = yf.download(symbol, period='1y', interval='1d', progress=False)
        if df_d.empty or len(df_d) < 50: continue
        if isinstance(df_d.columns, pd.MultiIndex): 
            df_d.columns = df_d.columns.get_level_values(0)
        
        df_d['MA20'] = df_d['Close'].rolling(window=20).mean()
        df_d['SMMA7'] = df_d['Close'].ewm(alpha=1/7, adjust=False).mean()
        
        curr = df_d.iloc[-1]
        c_price = float(curr['Close'])
        c_ma20 = float(curr['MA20'])
        c_smma7 = float(curr['SMMA7'])

        # 일봉 지지 로직이다
        is_near_smma7 = abs(c_price - c_smma7) / c_smma7 <= 0.01
        if is_near_smma7 and c_price >= c_smma7:
            support_smma7_list.append(f"{name}({symbol})")

        is_near_ma20 = abs(c_price - c_ma20) / c_ma20 <= 0.01
        if c_price < c_smma7 and is_near_ma20 and c_price >= c_ma20:
            support_ma20_list.append(f"{name}({symbol})")

        # 2. 주봉 분석이다
        df_w = yf.download(symbol, period='2y', interval='1wk', progress=False)
        if not df_w.empty and len(df_w) >= 21:
            if isinstance(df_w.columns, pd.MultiIndex): 
                df_w.columns = df_w.columns.get_level_values(0)
            
            # 주봉 RSI 계산이다
            df_w['WRSI'] = calculate_rsi(df_w['Close'])
            df_w['WSMMA7'] = df_w['Close'].ewm(alpha=1/7, adjust=False).mean()
            df_w['WMA20'] = df_w['Close'].rolling(window=20).mean()
            
            w_curr = df_w.iloc[-1]
            w_c_rsi = float(w_curr['WRSI'])
            w_c_price = float(w_curr['Close'])
            w_c_smma7 = float(w_curr['WSMMA7'])
            w_c_ma20 = float(w_curr['WMA20'])

            # 주봉 RSI 30 부근 감지이다
            if 28 <= w_c_rsi <= 35:
                weekly_rsi_30_list.append(f"{name}({symbol})")

            # 장기 추세 확인이다
            if w_c_price > w_c_smma7 and w_c_price > w_c_ma20:
                long_trend_list.append(f"{name}({symbol})")

        # 3. 매수 추천 로직이다
        if c_price > c_ma20 and c_smma7 > c_ma20:
            recommend_list.append(f"{name}({symbol})")

    except Exception as e:
        print(f"{symbol} 분석 실패했다이다: {e}")
        continue

# 리포트 구성이다
report = []
report.append("📢 매수와 매도는 개인의 책임입니다.")
report.append("-" * 20)
report.append("1. 주봉 RSI 30 부근 (대바닥권):")
report.append(", ".join(weekly_rsi_30_list) if weekly_rsi_30_list else "없음")
report.append("\n2. 일봉 7SMMA에 근접!! (강한 추세):")
report.append(", ".join(support_smma7_list) if support_smma7_list else "없음")
report.append("\n3. 일봉 20일선에 근접!! (눌림목):")
report.append(", ".join(support_ma20_list) if support_ma20_list else "없음")
report.append("\n4. 장기 상승 추세 종목 (주봉 정배열):")
report.append(", ".join(long_trend_list) if long_trend_list else "없음")
report.append("-" * 20)
report.append("💡 오늘의 매수 추천 종목:")
report.append(", ".join(recommend_list) if recommend_list else "없음")

send_message("\n".join(report))
