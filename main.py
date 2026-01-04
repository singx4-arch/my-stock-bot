import yfinance as yf
import pandas as pd
import requests
import os
import numpy as np
from datetime import datetime

# 텔레그램 설정이다
token = os.getenv('TELEGRAM_TOKEN')
chat_id = os.getenv('TELEGRAM_CHAT_ID')

def send_message(text):
    if not token or not chat_id: return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    params = {'chat_id': chat_id, 'text': text}
    requests.get(url, params=params)

def calculate_rsi(data, window=14):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

ticker_map = {
    # 1. 지수 및 레버리지 (시장 핵심)이다
    'QQQ': '나스닥100', 'TQQQ': '나스닥3배', 'SOXL': '반도체3배', 'NVDA': '엔비디아',
    
    # 2. 반도체 및 AI 하드웨어 (성장 주도)이다
    'AMD': 'AMD', 'TSM': 'TSMC', 'AVGO': '브로드컴', 'MU': '마이크론', 
    'ASML': 'ASML', 'LRCX': '램리서치', 'AMAT': '어플라이드', 'ARM': 'ARM', 
    'MRVL': '마벨', 'SNPS': '시놉시스', 'CDNS': '케이던스', 'ANET': '아리스타',
    'VRT': '버티브', 'SMCI': '슈퍼마이크로', 'DELL': '델', 'HPE': 'HPE',
    
    # 3. 에너지 및 유틸리티 (AI 전력 및 인플레이션 헤지)이다
    'XOM': '엑슨모빌', 'CVX': '쉐브론', 'OXY': '옥시덴탈', 'CCJ': '카메코', 
    'VST': '비스트라', 'CEG': '컨스텔레이션', 'GEV': 'GE베르노바', 'ETN': '이튼',
    'OKLO': '오클로', 'SMR': '뉴스케일파워', 'NXE': '넥스젠에너지', 'ENPH': '엔페이즈',
    
    # 4. 소프트웨어 및 보안 플랫폼 (수익화 단계)이다
    'MSFT': '마이크로소프트', 'GOOGL': '구글', 'AMZN': '아마존', 'META': '메타',
    'PLTR': '팔란티어', 'ORCL': '오라클', 'NOW': '서비스나우', 'APP': '앱러빈', 
    'CRWD': '크라우드스트라이크', 'PANW': '팔로알토', 'MDB': '몽고DB', 'DDOG': '데이터독',
    
    # 5. 금융 및 헬스케어 (포트폴리오 안정)이다
    'JPM': '제이피모건', 'GS': '골드만삭스', 'V': '비자', 'MA': '마스터카드',
    'LLY': '일라이릴리', 'NVO': '노보노디스크', 'UNH': '유나이티드헬스',
    
    # 6. 기타 혁신 기술 및 자산이다
    'MSTR': 'MSTR', 'COIN': '코인베이스', 'IONQ': '아이온큐', 'PATH': '유아이패스'
}

tickers = list(ticker_map.keys())

# 결과 리스트 초기화이다
rsi_bottom_list = []      # 1. 주봉 RSI 30 부근
trend_reversal_list = []  # 2. 주봉 추세 전환 (완료/임박)
top_recommend_list = []    # 3. 일봉 베스트 추천 (7SMMA & 20MA 상회)

for symbol in tickers:
    name = ticker_map[symbol]
    try:
        # 일봉 및 주봉 데이터 다운로드이다
        df_d = yf.download(symbol, period='1y', interval='1d', progress=False)
        df_w = yf.download(symbol, period='2y', interval='1wk', progress=False)
        
        if df_d.empty or df_w.empty: continue
        if isinstance(df_d.columns, pd.MultiIndex): df_d.columns = df_d.columns.get_level_values(0)
        if isinstance(df_w.columns, pd.MultiIndex): df_w.columns = df_w.columns.get_level_values(0)

        # 1. 주봉 RSI 분석 (대바닥권)이다
        df_w['WRSI'] = calculate_rsi(df_w['Close'])
        current_wrsi = float(df_w['WRSI'].iloc[-1])
        if 25 <= current_wrsi <= 38: # 30 부근 여유 범위이다
            rsi_bottom_list.append(f"{name}({symbol})")

        # 2. 주봉 추세 전환 분석 (골든크로스 및 0.15% 근접)이다
        df_w['WSMMA7'] = df_w['Close'].ewm(alpha=1/7, adjust=False).mean()
        df_w['WMA20'] = df_w['Close'].rolling(window=20).mean()
        
        w_c_s7 = float(df_w['WSMMA7'].iloc[-1])
        w_c_m20 = float(df_w['WMA20'].iloc[-1])
        w_p_s7 = float(df_w['WSMMA7'].iloc[-2])
        w_p_m20 = float(df_w['WMA20'].iloc[-2])
        
        # 주봉 이격률 계산이다
        w_gap = (w_c_s7 - w_c_m20) / w_c_m20
        
        # 골든크로스 완료 혹은 임박(0.15% 이내)이다
        is_w_gold = (w_p_s7 <= w_p_m20 and w_c_s7 > w_c_m20)
        is_w_imminent = (w_c_s7 <= w_c_m20) and (abs(w_gap) <= 0.0015)
        
        if is_w_gold:
            trend_reversal_list.append(f"{name}({symbol}) [전환완료]")
        elif is_w_imminent:
            trend_reversal_list.append(f"{name}({symbol}) [전환임박]")

        # 3. 일봉 기준 매수 추천 (정배열 필터링)이다
        df_d['SMMA7'] = df_d['Close'].ewm(alpha=1/7, adjust=False).mean()
        df_d['MA20'] = df_d['Close'].rolling(window=20).mean()
        
        c_price = float(df_d['Close'].iloc[-1])
        c_s7 = float(df_d['SMMA7'].iloc[-1])
        c_m20 = float(df_d['MA20'].iloc[-1])
        
        # 가격이 7SMMA와 20MA 위에 있고, 7SMMA가 20MA 위에 있는 정배열 종목이다
        if c_price > c_s7 and c_price > c_m20 and c_s7 > c_m20:
            top_recommend_list.append(f"{name}({symbol})")

    except Exception as e:
        print(f"{symbol} 분석 중 오류 발생했다이다: {e}")
        continue

# 리포트 구성이다
report = f"🏛️ 주간/일간 통합 기술 분석 리포트\n"
report += f"분석 일시: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
report += "-" * 25 + "\n\n"

report += "■ 주봉 추세 전환 (골든크로스 완료/임박)\n"
report += ", ".join(trend_reversal_list) if trend_reversal_list else "해당 종목 없음"
report += "\n\n"

report += "-" * 25 + "\n"
report += "모든 투자의 책임은 본인에게 있다이다."

send_message(report)
