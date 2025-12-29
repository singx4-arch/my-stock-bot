import yfinance as yf
import pandas as pd
import requests
import os

# 깃허브 Secrets 정보 가져오기이다
token = os.getenv('TELEGRAM_TOKEN')
chat_id = os.getenv('TELEGRAM_CHAT_ID')

def send_message(text):
    if not token or not chat_id:
        print("토큰이나 채팅 아이디 설정이 누락되었다")
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
        print(f"전송 중 오류 발생했다: {e}")

def calculate_rsi(data, window=14):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# 종목 리스트이다 (SyntaxError 방지를 위해 형식을 맞췄다)
ticker_map = {
    'NVDA': '엔비디아', 'TSLA': '테슬라', 'AAPL': '애플', 'MSFT': '마이크로소프트', 
    'AMZN': '아마존', 'META': '메타', 'GOOGL': '구글', 'PLTR': '팔란티어', 
    'MSTR': '마이크로스트래티지', 'COIN': '코인베이스', 'AMD': 'AMD', 'NFLX': '넷플릭스', 
    'AVGO': '브로드컴', 'TQQQ': '나스닥3배레버', 'SOXL': '반도체3배레버', 'ARM': 'ARM', 
    'TSM': 'TSMC', 'MU': '마이크론', 'INTC': '인텔', 'SMCI': '슈퍼마이크로', 
    'PYPL': '페이팔', 'SQQQ': '나스닥3배인버스', 'SOXS': '반도체3배인버스', 'PANW': '팔로알토', 
    'COST': '코스트코', 'QCOM': '퀄컴', 'ASML': 'ASML', 'SNOW': '스노우플레이크', 
    'MARA': '마라톤디지털', 'RIOT': '라이엇플랫폼'
}

tickers = list(ticker_map.keys())

# 결과 저장을 위한 리스트들이다
golden_cross_list = []
high_volume_list = []
uptrend_list = []
touch_ma7_list = []
support_list = []
bb_alert_list = []
rsi_alert_list = []

for symbol in tickers:
    name = ticker_map[symbol]
    try:
        # 일봉 데이터 분석이다
        df_d = yf.download(symbol, period='60d', interval='1d', progress=False)
        if df_d.empty or len(df_d) < 21: continue
        if isinstance(df_d.columns, pd.MultiIndex): 
            df_d.columns = df_d.columns.get_level_values(0)
        
        # 지표 계산이다
        df_d['MA7'] = df_d['Close'].rolling(window=7).mean()
        df_d['MA20'] = df_d['Close'].rolling(window=20).mean()
        df_d['Vol_MA20'] = df_d['Volume'].rolling(window=20).mean()
        df_d['RSI'] = calculate_rsi(df_d['Close'])
        
        curr = df_d.iloc[-1]
        prev = df_d.iloc[-2]
        
        c_price = float(curr['Close'])
        c_ma7 = float(curr['MA7'])
        c_ma20 = float(curr['MA20'])
        c_vol = float(curr['Volume'])
        a_vol = float(curr['Vol_MA20'])
        c_rsi = float(curr['RSI'])
        
        p_ma7 = float(prev['MA7'])
        p_ma20 = float(prev['MA20'])
        
        # 1. 7/20 골든 크로스이다
        if p_ma7 < p_ma20 and c_ma7 > c_ma20:
            golden_cross_list.append(f"{name}({symbol})")
        
        # 2. 거래량 급증 확인이다 (평균 1.5배 이상)
        if c_vol > a_vol * 1.5:
            high_volume_list.append(f"{name}({symbol})")
        
        # 3. 7SMA 근접 확인이다
        if abs(c_price - c_ma7) / c_ma7 <= 0.01:
            touch_ma7_list.append(f"{name}({symbol})")
            
        # 4. 상승 추세 및 20일선 지지 확인이다
        if c_price > c_ma20:
            uptrend_list.append(f"{name}({symbol})")
            if c_price <= c_ma20 * 1.01:
                support_list.append(f"{name}({symbol})")
        
        # 5. RSI 지표이다
        if c_rsi >= 70:
            rsi_alert_list.append(f"{name}({symbol}) 과열")
        elif c_rsi <= 30:
            rsi_alert_list.append(f"{name}({symbol}) 침체")

        # 4시간 봉 볼린저 밴드 분석이다
        df_4h = yf.download(symbol, period='30d', interval='4h', progress=False)
        if not df_4h.empty and len(df_4h) >= 20:
            if isinstance(df_4h.columns, pd.MultiIndex): 
                df_4h.columns = df_4h.columns.get_level_values(0)
            df_4h['MA'] = df_4h['Close'].rolling(window=20).mean()
            df_4h['STD'] = df_4h['Close'].rolling(window=20).std()
            u_bb = df_4h['MA'] + (df_4h['STD'] * 2)
            l_bb = df_4h['MA'] - (df_4h['STD'] * 2)
            c_4h = float(df_4h['Close'].iloc[-1])
            if c_4h > float(u_bb.iloc[-1]):
                bb_alert_list.append(f"{name}({symbol}) 상단돌파")
            elif c_4h < float(l_bb.iloc[-1]):
                bb_alert_list.append(f"{name}({symbol}) 하단이탈")
            
    except Exception as e: 
        print(f"{symbol} 분석 중 오류 발생했다: {e}")
        continue

# 메시지 조립이다
msg = "📢 실시간 주식 시장 분석 보고서이다\n\n"
msg += "7/20 골든 크로스 발생 종목이다:\n" + (", ".join(golden_cross_list) if golden_cross_list else "없음") + "\n\n"
msg += "거래량 급증 종목이다 (평균 1.5배 이상):\n" + (", ".join(high_volume_list) if high_volume_list else "없음") + "\n\n"
msg += "현재 상승 추세인 종목이다:\n" + (", ".join(uptrend_list) if uptrend_
