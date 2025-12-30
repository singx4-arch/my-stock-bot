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

ticker_map = { 
    'NVDA': '엔비디아', 'AAPL': '애플', 'MSFT': '마이크로소프트', 'TSLA': '테슬라', 
    'AMZN': '아마존', 'META': '메타', 'GOOGL': '구글', 'AVGO': '브로드컴', 
    'AMD': 'AMD', 'TSM': 'TSMC', 'ASML': 'ASML', 'COST': '코스트코', 
    'QCOM': '퀄컴', 'ARM': 'ARM', 'TQQQ': '나스닥3배레버', 'SOXL': '반도체3배레버' 
}

tickers = list(ticker_map.keys())
recommend_details = []

for symbol in tickers:
    name = ticker_map[symbol]
    try:
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

        if c_price > c_ma20 and c_smma7 > c_ma20:
            recent_low = float(df_d['Low'].iloc[-10:].min())
            
            support_status = ""
            gap_smma = abs(c_price - c_smma7) / c_smma7
            gap_ma20 = abs(c_price - c_ma20) / c_ma20
            
            if c_price >= c_smma7:
                if gap_smma <= 0.01:
                    support_status = "\n> 🚨 7SMMA 지지 구간이다!!"
            elif c_price < c_smma7:
                if gap_ma20 <= 0.01:
                    support_status = "\n> 🚨 20일선 지지 구간이다!!"
            
            # 가독성을 위해 불렛 포인트와 헤더를 사용했다이다
            detail = f"### 📍 {name} ({symbol}) {support_status}\n"
            detail += f"* 현재가: {c_price:.2f}$\n"
            detail += f"* 진입 타점\n"
            detail += f"  - 1차 (7SMMA): {c_smma7:.2f}$\n"
            detail += f"  - 2차 (20MA): {c_ma20:.2f}$\n"
            detail += f"* 손절 라인\n"
            detail += f"  - 저점 이탈: {recent_low:.2f}$\n"
            detail += f"  - 20MA 이탈: {c_ma20:.2f}$"
            recommend_details.append(detail)

    except Exception as e:
        print(f"{symbol} 분석 실패했다이다: {e}")
        continue

report = []
report.append("## 🏛️ 오늘의 매수 전략 리포트이다")
report.append("---")

if recommend_details:
    report.append("\n\n---\n\n".join(recommend_details))
else:
    report.append("> 조건에 맞는 종목이 현재 없다이다")

report.append("\n---")
report.append("💡 7SMMA 이탈 시 20일선 지지를 반드시 확인하라이다")

send_message("\n".join(report))
