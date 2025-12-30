import yfinance as yf
import pandas as pd
import requests
import time
import os

token = os.getenv('TELEGRAM_TOKEN')

def get_updates(offset=None):
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    params = {'offset': offset, 'timeout': 30}
    try:
        r = requests.get(url, params=params)
        return r.json()
    except:
        return None

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    params = {'chat_id': chat_id, 'text': text, 'parse_mode': 'Markdown'}
    requests.get(url, params=params)

def calculate_stop_loss(symbol):
    try:
        df = yf.download(symbol, period='1mo', interval='1d', progress=False)
        if df.empty or len(df) < 10: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

        curr_price = float(df['Close'].iloc[-1])
        low_10d = float(df['Low'].iloc[-10:].min())
        stop_loss_low = low_10d * 0.98 
        
        df['TR'] = df['High'] - df['Low']
        atr = df['TR'].rolling(window=14).mean().iloc[-1]
        stop_loss_atr = curr_price - (atr * 1.5)
        
        return {'curr': curr_price, 'low_base': stop_loss_low, 'atr_base': stop_loss_atr}
    except:
        return None

# 주요 한글 종목명 매핑이다 (나스닥 시총 상위 및 인기 종목이다)
name_to_ticker = {
    '엔비디아': 'NVDA', '테슬라': 'TSLA', '애플': 'AAPL', '마이크로소프트': 'MSFT',
    '아마존': 'AMZN', '메타': 'META', '구글': 'GOOGL', '팔란티어': 'PLTR',
    '마이크론': 'MU', '넷플릭스': 'NFLX', '브로드컴': 'AVGO', '퀄컴': 'QCOM',
    'AMD': 'AMD', '인텔': 'INTC', '암': 'ARM', 'ASML': 'ASML', '어플라이드': 'AMAT',
    '스타벅스': 'SBUX', '코스트코': 'COST', '펩시': 'PEP', '어도비': 'ADBE',
    '시스코': 'CSCO', '티모바일': 'TMUS', '인튜이티브': 'ISRG', '페이팔': 'PYPL',
    '에어비앤비': 'ABNB', '모더나': 'MRNA', '루시드': 'LCID', '리비안': 'RIVN',
    '코인베이스': 'COIN', '마이크로스트래티지': 'MSTR', '나스닥100': 'QQQ',
    '나스닥3배': 'TQQQ', '반도체3배': 'SOXL', '데이터독': 'DDOG', '클라우드플레어': 'NET'
}

print("나스닥 전종목 대응 봇 가동 중이다...")
last_update_id = None
help_text = "🏛️ 나스닥 종목 손절가 검색기이다\n\n/손절 종목명 또는 티커\n\n이렇게 입력하면 검색이 가능하다이다.\n예1 (한글): /손절 엔비디아\n예2 (티커): /손절 TSLA, /손절 AAPL"

while True:
    updates = get_updates(last_update_id)
    if updates and "result" in updates:
        for update in updates["result"]:
            last_update_id = update["update_id"] + 1
            if "message" in update and "text" in update["message"]:
                msg_text = update["message"]["text"]
                chat_id = update["message"]["chat"]["id"]

                if msg_text in ["/start", "/help"]:
                    send_message(chat_id, help_text)
                    continue

                if msg_text.startswith("/손절"):
                    target = msg_text.replace("/손절", "").strip()
                    if not target:
                        send_message(chat_id, "검색할 종목을 입력해달라이다.")
                        continue
                    
                    # 한글 이름이면 티커로 바꾸고, 아니면 입력한 그대로(티커) 사용한다이다
                    ticker = name_to_ticker.get(target, target.upper())
                    
                    send_message(chat_id, f"🔍 {ticker} 종목을 나스닥에서 찾는 중이다...")
                    result = calculate_stop_loss(ticker)
                    
                    if result:
                        res_msg = f"✅ {target}({ticker}) 분석 완료이다\n"
                        res_msg += f"현재가: {result['curr']:.2f}$\n"
                        res_msg += "-" * 15 + "\n"
                        res_msg += f"🛡️ 보수적 손절가: {result['low_base']:.2f}$ (지지선)\n"
                        res_msg += f"📉 공격적 손절가: {result['atr_base']:.2f}$ (변동성)\n"
                        send_message(chat_id, res_msg)
                    else:
                        send_message(chat_id, f"❌ {target} 정보를 찾을 수 없다이다. 티커가 정확한지 확인해달라이다.")
                
                elif not msg_text.startswith("/"):
                    send_message(chat_id, help_text)

    time.sleep(1)
