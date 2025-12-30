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
recommend_details = []

for symbol in tickers:
    name = ticker_map[symbol]
    try:
        # 일봉 데이터 분석이다
        df_d = yf.download(symbol, period='1y', interval='1d', progress=False)
        if df_d.empty or len(df_d) < 50: continue
        if isinstance(df_d.columns, pd.MultiIndex): 
            df_d.columns = df_d.columns.get_level_values(0)
        
        # 지표 계산이다
        df_d['MA20'] = df_d['Close'].rolling(window=20).mean()
        df_d['SMMA7'] = df_d['Close'].ewm(alpha=1/7, adjust=False).mean()
        
        curr = df_d.iloc[-1]
        c_price = float(curr['Close'])
        c_ma20 = float(curr['MA20'])
        c_smma7 = float(curr['SMMA7'])

        # 매수 추천 조건이다
        if c_price > c_ma20 and c_smma7 > c_ma20:
            # 최근 10일 저점 계산이다
            recent_low = float(df_d['Low'].iloc[-10:].min())
            
            detail = f"📍 {name}({symbol})\n"
            detail += f"현재가: {c_price:.2f}$\n"
            detail += f"--- 진입 가이드 ---\n"
            detail += f"1. 7SMMA 지지 시: {c_smma7:.2f}$\n"
            detail += f"2. 20일선 지지 시: {c_ma20:.2f}$\n"
            detail += f"--- 손절 가이드 ---\n"
            detail += f"v1. 최근 저점 이탈 시: {recent_low:.2f}$\n"
            detail += f"v2. 20일선 이탈 시: {c_ma20:.2f}$\n"
            recommend_details.append(detail)

    except Exception as e:
        print(f"{symbol} 분석 실패했다이다: {e}")
        continue

# 리포트 구성이다
report = []
report.append("📢 오늘의 매수 추천 및 전략 리포트이다")
report.append("=" * 20)

if recommend_details:
    report.append("\n\n".join(recommend_details))
else:
    report.append("조건에 맞는 종목이 없다이다")

report.append("\n" + "=" * 20)
report.append("매수 전 반드시 본인의 기준을 확인하라이다.")

send_message("\n".join(report))
