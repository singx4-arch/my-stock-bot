import yfinance as yf
import pandas as pd
import requests
import os

token = os.getenv('TELEGRAM_TOKEN')
chat_id = os.getenv('TELEGRAM_CHAT_ID')

def send_message(text):
    if not token or not chat_id: return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    params = {'chat_id': chat_id, 'text': text}
    requests.get(url, params=params)

ticker_map = { 
    'NVDA': '엔비디아', 'TSLA': '테슬라', 'AAPL': '애플', 'MSFT': '마이크로소프트', 
    'AMZN': '아마존', 'META': '메타', 'GOOGL': '구글', 'PLTR': '팔란티어', 
    'MSTR': '마이크로스트래티지', 'COIN': '코인베이스', 'AMD': 'AMD', 'NFLX': '넷플릭스', 
    'AVGO': '브로드컴', 'TQQQ': '나스닥3배레버', 'SOXL': '반도체3배레버', 'ARM': 'ARM', 
    'TSM': 'TSMC', 'MU': '마이크론', 'INTC': '인텔', 'SMCI': '슈퍼마이크로', 
    'PYPL': '페이팔', 'SQQQ': '나스닥3배인버스', 'SOXS': '반도체3배인버스', 'PANW': '팔로알토', 
    'COST': '코스트코', 'QCOM': '퀄컴', 'ASML': 'ASML', 'SNOW': '스노우플레이크', 
    'MARA': '마라톤디지털', 'RIOT': '라이엇플랫폼', 'VRT': '버티브 홀딩스', 
    'ANET': '아리스타 네트웍스', 'LLY': '일라이 릴리', 'NVO': '노보 노디스크', 'VST': '비스트라', 
    'GEV': 'GE 베르노바', 'MRVL': '마벨 테크놀로지', 'LRCX': '램리서치', 'AUR': '오로라 이노베이션', 
    'UBER': '우버', 'APP': '앱러빈', 'SAP': 'SAP', 'SOFI': '소파이', 'LMND': '레모네이드', 'ISRG': '인튜이티브 서지컬', 
    'VRTX': '버텍스 파마슈티컬스', 'REGN': '리제네론', 'CLSK': '클린스파크', 'HOOD': '로빈후드'
}

uptrend_gold = []    # 🚀 진짜 상승 추세 (HH+HL 달성)이다
consolidation_gold = [] # 💤 골든크로스이나 추세 미달성 (보합/주의)이다

for symbol, name in ticker_map.items():
    try:
        df = yf.download(symbol, period='1y', interval='1d', progress=False)
        if len(df) < 50: continue
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

        # 지표 계산 (MA20, 7SMMA)이다
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['SMMA7'] = df['Close'].ewm(alpha=1/7, adjust=False).mean()
        
        curr = df.iloc[-1]
        c_p, c_ma20, c_smma7 = float(curr['Close']), float(curr['MA20']), float(curr['SMMA7'])
        
        # 다우 이론: 10일(2주일) 비교 구간 설정이다
        recent = df.iloc[-10:] 
        prev = df.iloc[-20:-10] 
        c_h, c_l = float(recent['High'].max()), float(recent['Low'].min())
        p_h, p_l = float(prev['High'].max()), float(prev['Low'].min())
        
        # 임계값 없이 순수하게 수치만 비교한다이다
        is_hh = c_h > p_h # 고점 상승이다
        is_hl = c_l > p_l # 저점 상승이다
        is_gold = c_p > c_ma20 and c_smma7 > c_ma20 # 골든크로스(정배열)이다
        
        recent_low = float(df['Low'].iloc[-10:].min())
        info = f"[{name} ({symbol})]\n현재가: {c_p:.2f}$\n진입가(7선): {c_smma7:.2f}$\n진입가(20선): {c_ma20:.2f}$\n손절가(저점): {recent_low:.2f}$"

        if is_gold:
            if is_hh and is_hl:
                # 고점과 저점이 모두 높아진 완벽한 상승 추세이다
                uptrend_gold.append("🚀 " + info)
            else:
                # 골든크로스 상태이지만 고점이나 저점 중 하나라도 낮아진 경우이다
                consolidation_gold.append("💤 " + info)

    except: continue

report = "📢 민감형 매수 전략 리포트 (임계값 제거)이다\n" + "="*25 + "\n\n"
report += "🚀 진짜 상승추세 (10일 HH+HL 달성)이다\n"
report += "\n\n".join(uptrend_gold) if uptrend_gold else "해당 종목 없음이다"
report += "\n\n" + "-"*25 + "\n\n"
report += "💤 보합 및 추세 확인 중 (주의/대기)이다\n"
report += "\n\n".join(consolidation_gold) if consolidation_gold else "해당 종목 없음이다"
report += "\n\n" + "="*25 + "\n"

report += "💡 투자 가이드이다\n"
report += "1. 가장 안전한 타점: 🚀 그룹 종목이 7smma(7선)에 눌릴 때가 승률이 높다이다.\n"
report += "2. 역전의 기회: 💤 그룹 종목은 고점(HH)을 다시 높이는 순간 🚀로 진입한다이다."

send_message(report)
