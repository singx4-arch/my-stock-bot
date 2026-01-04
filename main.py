import yfinance as yf
import pandas as pd
import requests
import os
import numpy as np
import json
from datetime import datetime

# 텔레그램 설정이다
token = os.getenv('TELEGRAM_TOKEN')
chat_id = os.getenv('TELEGRAM_CHAT_ID')

def send_message(text):
    if not token or not chat_id: return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    params = {'chat_id': chat_id, 'text': text}
    requests.get(url, params=params)

def get_fear_and_greed():
    # 시장의 전반적인 심리 상태를 가져오는 함수이다
    try:
        url = "https://api.alternative.me/fng/?limit=1"
        res = requests.get(url, timeout=10)
        data = res.json()
        val = int(data['data'][0]['value'])
        classification = data['data'][0]['value_classification']
        k_map = {
            "Extreme Fear": "😱 극도의 공포",
            "Fear": "😨 공포",
            "Neutral": "😐 중립",
            "Greed": "🤑 탐욕",
            "Extreme Greed": "🔥 극도의 탐욕"
        }
        return f"{val} ({k_map.get(classification, classification)})"
    except: return "⚠️ 확인 불가"

def calculate_vidya(df, length=121):
    # 변동성 가중 이동 평균(VIDYA) 수식이다
    close = df['Close']
    change = close.diff()
    upside = change.where(change > 0, 0).rolling(window=9).sum()
    downside = -change.where(change < 0, 0).rolling(window=9).sum()
    cmo = abs((upside - downside) / (upside + downside)).fillna(0)
    alpha = 2 / (length + 1)
    vidya = pd.Series(index=close.index, dtype='float64')
    vidya.iloc[length] = close.iloc[:length].mean()
    for i in range(length + 1, len(close)):
        k = alpha * cmo.iloc[i]
        vidya.iloc[i] = k * close.iloc[i] + (1 - k) * vidya.iloc[i-1]
    return vidya

# 재혁이가 선택한 전섹터 통합 티커 리스트이다
ticker_map = {
    'QQQ': '나스닥100', 'TQQQ': '나스닥3배', 'SOXL': '반도체3배', 'NVDA': '엔비디아',
    'AMD': 'AMD', 'TSM': 'TSMC', 'AVGO': '브로드컴', 'MU': '마이크론', 
    'ASML': 'ASML', 'LRCX': '램리서치', 'AMAT': '어플라이드', 'ARM': 'ARM', 
    'MRVL': '마벨', 'SNPS': '시놉시스', 'CDNS': '케이던스', 'ANET': '아리스타',
    'VRT': '버티브', 'SMCI': '슈퍼마이크로', 'DELL': '델', 'HPE': 'HPE',
    'XOM': '엑슨모빌', 'CVX': '쉐브론', 'OXY': '옥시덴탈', 'CCJ': '카메코', 
    'VST': '비스트라', 'CEG': '컨스텔레이션', 'GEV': 'GE베르노바', 'ETN': '이튼',
    'OKLO': '오클로', 'SMR': '뉴스케일파워', 'NXE': '넥스젠에너지', 'ENPH': '엔페이즈',
    'MSFT': '마이크로소프트', 'GOOGL': '구글', 'AMZN': '아마존', 'META': '메타',
    'PLTR': '팔란티어', 'ORCL': '오라클', 'NOW': '서비스나우', 'APP': '앱러빈', 
    'CRWD': '크라우드스트라이크', 'PANW': '팔로알토', 'MDB': '몽고DB', 'DDOG': '데이터독',
    'JPM': '제이피모건', 'GS': '골드만삭스', 'V': '비자', 'MA': '마스터카드',
    'LLY': '일라이릴리', 'NVO': '노보노디스크', 'UNH': '유나이티드헬스',
    'MSTR': 'MSTR', 'COIN': '코인베이스', 'IONQ': '아이온큐', 'PATH': '유아이패스'
}

tickers = list(ticker_map.keys())
super_buy_list = []     # 일봉 VIYA 돌파 & 주봉 크로스 동시 만족이다
viya_signals = []       # 일봉 VIYA 상방/하방 신호이다
weekly_signals = []     # 주봉 골든크로스 신호이다
big_picture_bull = []   # 200일선 위 장기 우상향이다

market_sentiment = get_fear_and_greed()

for symbol in tickers:
    name = ticker_map[symbol]
    try:
        df_d = yf.download(symbol, period='2y', interval='1d', progress=False)
        df_w = yf.download(symbol, period='2y', interval='1wk', progress=False)
        if df_d.empty or df_w.empty: continue
        if isinstance(df_d.columns, pd.MultiIndex): df_d.columns = df_d.columns.get_level_values(0)

        # 1. 일봉 VIYA 분석이다
        df_d['VIYA'] = calculate_vidya(df_d, 121)
        cp = float(df_d['Close'].iloc[-1]); cv = float(df_d['VIYA'].iloc[-1])
        pp = float(df_d['Close'].iloc[-2]); pv = float(df_d['VIYA'].iloc[-2])
        is_viya_gold = (pp <= pv and cp > cv)
        is_viya_dead = (pp >= pv and cp < cv)

        # 2. 주봉 추세 분석이다 (7s-20 크로스)
        df_w['WSMMA7'] = df_w['Close'].ewm(alpha=1/7, adjust=False).mean()
        df_w['WMA20'] = df_w['Close'].rolling(window=20).mean()
        wc7 = float(df_w['WSMMA7'].iloc[-1]); wm20 = float(df_w['WMA20'].iloc[-1])
        wp7 = float(df_w['WSMMA7'].iloc[-2]); wm20p = float(df_w['WMA20'].iloc[-2])
        is_weekly_gold = (wp7 <= wm20p and wc7 > wm20)

        # 3. 특급 매수 및 일반 신호 분류이다
        if is_viya_gold and is_weekly_gold:
            super_buy_list.append(f"💎 {name}({symbol})")
        elif is_viya_gold:
            viya_signals.append(f"🟢 {name}: 일봉 VIYA 상방 돌파")
        elif is_viya_dead:
            viya_signals.append(f"🔴 {name}: 일봉 VIYA 하방 이탈")
        elif is_weekly_gold:
            weekly_signals.append(f"✅ {name}: 주봉 골든크로스 완료")

        # 4. 장기 대세 확인 (200일선)이다
        df_d['MA200'] = df_d['Close'].rolling(window=200).mean()
        if cp > float(df_d['MA200'].iloc[-1]):
            big_picture_bull.append(name)

    except: continue

# 리포트 구성이다
report = f"🏛️ 재혁 v195 특급 매수 통합 리포트\n"
report += f"분석 일시: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
report += f"📊 시장 심리 지수: {market_sentiment}\n"
report += "=" * 25 + "\n\n"

if super_buy_list:
    report += "🔥 [특급 매수: SUPER BUY] 🔥\n"
    report += "일봉 모멘텀과 주봉 추세가 동시 폭발했다이다!\n"
    report += "\n".join(super_buy_list) + "\n\n"

if viya_signals or weekly_signals:
    report += "📢 [실시간 주요 추세 신호]이다\n"
    report += "\n".join(viya_signals + weekly_signals) + "\n\n"

report += "💎 [200일선 위 장기 우상향 종목]이다\n"
# 종목이 너무 많으므로 10개씩 끊어서 보여준다이다
report += ", ".join(big_picture_bull[:10]) + (f" 외 {len(big_picture_bull)-10}개" if len(big_picture_bull) > 10 else "")
report += "\n\n"

report += "💡 전략 가이드: 특급 매수 종목은 1억 투자 시 연평균 3,800만원 수익을 목표로 하는 핵심 타점이다이다.\n"
report += "\n"
report += "추세 매매 가이드\n상승 추세 종목은 세가지로 나뉩니다.\n로켓, 다이아, 위험으로 나뉘는데
\n로켓, 다이아 종목 두가지만 사면 되고
\n다이아 종목이 제일 사기 좋은 애들입니다.
\n주요 지지선에 닿으면 알람이 오니까 그거 보고 사면됨 ㅅㄱ"

send_message(report)
