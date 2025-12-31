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
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    # 마크다운 대신 일반 텍스트로 보내서 문법 오류를 원천 차단한다이다
    params = {
        'chat_id': chat_id,
        'text': text
    }
    try: 
        response = requests.get(url, params=params)
        if response.status_code != 200:
            print(f"전송 실패! 이유: {response.text}")
        else:
            print("메시지 전송 성공했다이다!")
    except Exception as e: 
        print(f"전송 중 예외 발생했다이다: {e}")

ticker_map = { 
    'NVDA': '엔비디아', 'AAPL': '애플', 'MSFT': '마이크로소프트', 'TSLA': '테슬라', 
    'AMZN': '아마존', 'META': '메타', 'GOOGL': '구글', 'AVGO': '브로드컴', 
    'AMD': 'AMD', 'TSM': 'TSMC', 'ASML': 'ASML', 'COST': '코스트코', 
    'QCOM': '퀄컴', 'ARM': 'ARM', 'TQQQ': '나스닥3배레버', 'SOXL': '반도체3배레버',
    'PLTR': '팔란티어', 'MU': '마이크론', 'ORCL': '오라클', 'DELL': '델', 'QQQ': 'QQQ'
}

tickers = list(ticker_map.keys())
recommend_details = []

print(f"분석 시작한다이다... 대상: {len(tickers)}종목")

for symbol in tickers:
    name = ticker_map[symbol]
    try:
        # 데이터 기간을 넉넉히 가져온다이다
        df_d = yf.download(symbol, period='1y', interval='1d', progress=False)
        if df_d.empty or len(df_d) < 50:
            continue
            
        if isinstance(df_d.columns, pd.MultiIndex): 
            df_d.columns = df_d.columns.get_level_values(0)
        
        df_d['MA20'] = df_d['Close'].rolling(window=20).mean()
        df_d['SMMA7'] = df_d['Close'].ewm(alpha=1/7, adjust=False).mean()
        
        curr = df_d.iloc[-1]
        c_price = float(curr['Close'])
        c_ma20 = float(curr['MA20'])
        c_smma7 = float(curr['SMMA7'])

        # 정배열 조건 확인이다
        if c_price > c_ma20 and c_smma7 > c_ma20:
            recent_low = float(df_d['Low'].iloc[-10:].min())
            
            support_status = ""
            gap_smma = abs(c_price - c_smma7) / c_smma7
            gap_ma20 = abs(c_price - c_ma20) / c_ma20
            
            if c_price >= c_smma7 and gap_smma <= 0.01:
                support_status = " [!] 7smma 지지권"
            elif c_price < c_smma7 and gap_ma20 <= 0.01:
                support_status = " [!] 20일선 지지권"
            
            detail = f"[{name} ({symbol}){support_status}]\n"
            detail += f"현재가: {c_price:.2f}$\n"
            detail += f"진입가(7선): {c_smma7:.2f}$\n"
            detail += f"진입가(20선): {c_ma20:.2f}$\n"
            detail += f"손절가(저점): {recent_low:.2f}$"
            recommend_details.append(detail)

    except Exception as e:
        print(f"{symbol} 분석 중 오류 발생했다이다: {e}")
        continue

# 리포트 조립이다
report = "📢 단기 매수가 가이드 리포트이다()\n" + "="*20 + "\n\n"

if recommend_details:
    report += "\n\n".join(recommend_details)
else:
    report += "현재 조건(정배열)에 맞는 종목이 하나도 없다."

report += "\n\n" + "="*20
report += "\n7선을 깨면 20일선 지지를 확인하라"

send_message(report)
