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
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    params = {'chat_id': chat_id, 'text': text, 'parse_mode': 'Markdown'}
    try:
        requests.get(url, params=params)
    except Exception as e:
        print(f"전송 중 오류 발생했다이다: {e}")

# 요청하신 15개 핵심 종목 리스트이다
ticker_map = {
    'NVDA': '엔비디아', 'AAPL': '애플', 'MSFT': '마이크로소프트', 'TSLA': '테슬라', 
    'AMZN': '아마존', 'META': '메타', 'GOOGL': '구글', 'AVGO': '브로드컴', 
    'AMD': 'AMD', 'TSM': 'TSMC', 'ASML': 'ASML', 'COST': '코스트코', 
    'QCOM': '퀄컴', 'ARM': 'ARM', 'TQQQ': '나스닥3배레버', 'SOXL': '반도체3배레버',
    'PLTR': '팔란티어', 'MU': '마이크론', 'ORCL': '오라클', 'DELL': '델', 'QQQ': 'QQQ'
}

tickers = list(ticker_map.keys())

# 추세 및 돌파 분류 리스트이다
uptrend_list = []
downtrend_list = []
neutral_list = []
breakout_list = []

for symbol in tickers:
    name = ticker_map[symbol]
    try:
        # 데이터 다운로드이다
        df = yf.download(symbol, period='2mo', interval='1d', progress=False)
        if len(df) < 30: continue
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # 1. 다우 이론 추세 판독이다
        recent = df.iloc[-5:] 
        previous = df.iloc[-10:-5]
        
        curr_high = float(recent['High'].max())
        curr_low = float(recent['Low'].min())
        prev_high = float(previous['High'].max())
        prev_low = float(previous['Low'].min())

        if curr_high > prev_high and curr_low > prev_low:
            uptrend_list.append(name)
        elif curr_high < prev_high and curr_low < prev_low:
            downtrend_list.append(name)
        else:
            neutral_list.append(name)

        # 2. 전고점 돌파 확인이다 (20일 기준)
        lookback_20 = df.iloc[-21:-1]
        if float(df.iloc[-1]['Close']) > float(lookback_20['High'].max()):
            breakout_list.append(name)

    except Exception as e:
        print(f"{symbol} 분석 실패했다이다: {e}")
        continue

# 리포트 구성이다
report = []
report.append("🏛️ 다우 이론 실시간 추세 리포트이다")
report.append("-" * 20)
report.append(f"상승추세: {', '.join(uptrend_list) if uptrend_list else '없음'}")
report.append(f"하락추세: {', '.join(downtrend_list) if downtrend_list else '없음'}")
report.append(f"보합: {', '.join(neutral_list) if neutral_list else '없음'}")
report.append("-" * 20)
report.append(f"🔥 전고점 돌파: {', '.join(breakout_list) if breakout_list else '없음'}")

send_message("\n".join(report))
