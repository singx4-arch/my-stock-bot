import yfinance as yf
import pandas as pd
import requests
import os

# 깃허브 Secrets 정보 가져오기이다
token = os.getenv('TELEGRAM_TOKEN')
chat_id = os.getenv('TELEGRAM_CHAT_ID')

def send_message(text):
    if len(text) > 4000: 
        text = text[:4000] + "...(중략)"
    url = f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={text}&parse_mode=Markdown"
    try: 
        requests.get(url)
    except Exception as e: 
        print(f"전송 실패했다: {e}")

def calculate_rsi(data, window=14):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# 종목별 한글 이름 매핑이다
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

uptrend_list = []
support_list = []
touch_ma7_list = []
bb_alert_list = []
rsi_alert_list = []

for symbol in tickers:
    name = ticker_map[symbol]
    try:
        df_d = yf.download(symbol, period='60d', interval='1d', progress=False)
        if df_d.empty or len(df_d) < 20: continue
        if isinstance(df_d.columns, pd.MultiIndex): df_d.columns = df_d.columns.get_level_values(0)
        
        df_d['MA7'] = df_d['Close'].rolling(window=7).mean()
        df_d['MA20'] = df_d['Close'].rolling(window=20).mean()
        df_d['RSI'] = calculate_rsi(df_d['Close'])
        
        curr_d = float(df_d['Close'].iloc[-1])
        ma7_d = float(df_d['MA7'].iloc[-1])
        ma20_d = float(df_d['MA20'].iloc[-1])
        rsi_d = float(df_d['RSI'].iloc[-1])
        
        # 숫자 정보를 빼고 종목명만 추가한다
        if abs(curr_d - ma7_d) / ma7_d <= 0.01:
            touch_ma7_list.append(f"⚡ {name}({symbol})")
            
        if curr_d > ma20_d:
            uptrend_list.append(f"{name}({symbol})")
            if curr_d <= ma20_d * 1.01:
                support_list.append(f"🎯 {name}({symbol})")
        
        if rsi_d >= 70:
            rsi_alert_list.append(f"🔥 {name}({symbol}) 과열")
        elif rsi_d <= 30:
            rsi_alert_list.append(f"❄️ {name}({symbol}) 침체")

        df_4h = yf.download(symbol, period='30d', interval='4h', progress=False)
        if df_4h.empty or len(df_4h) < 20: continue
        if isinstance(df_4h.columns, pd.MultiIndex): df_4h.columns = df_4h.columns.get_level_values(0)
        
        df_4h['MA'] = df_4h['Close'].rolling(window=20).mean()
        df_4h['STD'] = df_4h['Close'].rolling(window=20).std()
        upper_bb = df_4h['MA'] + (df_4h['STD'] * 2)
        lower_bb = df_4h['MA'] - (df_4h['STD'] * 2)
        
        curr_4h = float(df_4h['Close'].iloc[-1])
        if curr_4h > float(upper_bb.iloc[-1]):
            bb_alert_list.append(f"🚀 {name}({symbol}) 상단돌파")
        elif curr_4h < float(lower_bb.iloc[-1]):
            bb_alert_list.append(f"⚠️ {name}({symbol}) 하단이탈")
            
    except: continue

msg = "📢 실시간 주식 시장 분석 보고서이다\n\n"
msg += "✅ 현재 상승 추세인 종목이다:\n" + (", ".join(uptrend_list) if uptrend_list else "없음") + "\n\n"
msg += "⚡ 7SMA 지지/저항 근접 구간이다:\n" + (", ".join(touch_ma7_list) if touch_ma7_list else "없음") + "\n\n"
msg += "🎯 20일선 지지 확인 구간이다:\n" + (", ".join(support_list) if support_list else "없음") + "\n\n"
msg += "📊 4시간 봉 변동성 포착이다:\n" + (", ".join(bb_alert_list) if bb_alert_list else "없음") + "\n\n"
msg += "📈 RSI 지표 과열/침체 신호이다:\n" + (", ".join(rsi_alert_list) if rsi_alert_list else "없음")

send
