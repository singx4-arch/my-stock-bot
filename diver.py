import yfinance as yf
import pandas as pd
import requests
import os
import numpy as np
from datetime import datetime

# 1. 환경 설정이다
token = os.getenv('TELEGRAM_TOKEN') or '7971022798:AAFGQR1zxdCq1urZKgdRzjjsvr3Lt6T9y1I'
chat_id = os.getenv('TELEGRAM_CHAT_ID')

def send_message(text):
    if not token or not chat_id: return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    params = {'chat_id': chat_id, 'text': text}
    try:
        requests.get(url, params=params, timeout=10)
    except: pass

def calculate_rsi(data, window=14):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def find_swings(series, window=3, mode='low'):
    swings = []
    for i in range(window, len(series) - window):
        is_swing = True
        for j in range(1, window + 1):
            if mode == 'low':
                if series.iloc[i] > series.iloc[i-j] or series.iloc[i] > series.iloc[i+j]:
                    is_swing = False; break
            else:
                if series.iloc[i] < series.iloc[i-j] or series.iloc[i] < series.iloc[i+j]:
                    is_swing = False; break
        if is_swing:
            swings.append(i)
    return swings

# 2. 고도화된 분석 엔진이다
def run_analysis_v134():
    # 티커 리스트를 40개 이상으로 대폭 확장했다이다
    ticker_map = {
        # 지수 및 레버리지
        'QQQ': '나스닥100', 'TQQQ': '나스닥3배', 'SOXL': '반도체3배', 'SPY': 'S&P500',
        # 반도체 및 장비
        'NVDA': '엔비디아', 'TSM': 'TSMC', 'AVGO': '브로드컴', 'ASML': 'ASML', 
        'AMD': 'AMD', 'MU': '마이크론', 'AMAT': '어플라이드', 'LRCX': '램리서치', 
        'QCOM': '퀄컴', 'ARM': 'ARM', 'SMCI': '슈퍼마이크로', 'INTC': '인텔',
        # AI 및 빅테크
        'MSFT': '마이크로소프트', 'AAPL': '애플', 'AMZN': '아마존', 'META': '메타', 
        'GOOGL': '구글', 'PLTR': '팔란티어', 'ORCL': '오라클', 'NOW': '서비스나우',
        # AI 인프라 및 네트워킹
        'ANET': '아리스타', 'VRT': '버티브', 'DELL': '델', 'IBM': 'IBM',
        # 유망 기술 및 성장주
        'TSLA': '테슬라', 'MSTR': '마이크로스트래티지', 'COIN': '코인베이스', 'IONQ': '아이온큐',
        'NFLX': '넷플릭스', 'UBER': '우버', 'SHOP': '쇼피파이', 'HOOD': '로빈후드',
        # 에너지 및 유틸리티 (AI 전력 관련)
        'VST': '비스트라', 'CEG': '컨스텔레이션', 'OKLO': '오클로', 'SMR': '뉴스케일',
        'NLR': '우라늄ETF', 'XLE': '에너지ETF', 'GLW': '코닝'
    }

    final_groups = {
        '🚨 강력 하락 주의 (일반 하락)': [],
        '🆘 진바닥 포착 (일반 상승)': [],
        '📈 추세 강화 (히든 상승)': [],
        '📉 조정 경고 (히든 하락)': [],
        '🔄 신호 충돌 (변곡점 주의)': []
    }

    for symbol, name in ticker_map.items():
        try:
            df = yf.download(symbol, period='1y', interval='1d', progress=False)
            if len(df) < 60: continue
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            
            df['RSI'] = calculate_rsi(df['Close'])
            avg_vol = df['Volume'].rolling(window=20).mean().iloc[-1]
            curr_vol = df['Volume'].rolling(window=5).mean().iloc[-1]
            
            low_idx = find_swings(df['Low'], window=3, mode='low')
            high_idx = find_swings(df['High'], window=3, mode='high')
            
            sigs = []

            # 상승 계열 분석이다
            if len(low_idx) >= 2:
                i1, i2 = low_idx[-2], low_idx[-1]
                p1, p2, r1, r2 = df['Low'].iloc[i1], df['Low'].iloc[i2], df['RSI'].iloc[i1], df['RSI'].iloc[i2]
                if p2 < p1 and r2 > r1 and r1 <= 38: sigs.append('REG_BULL')
                elif p2 > p1 and r2 < r1: sigs.append('HID_BULL')

            # 하락 계열 분석이다
            if len(high_idx) >= 2:
                i1, i2 = high_idx[-2], high_idx[-1]
                p1, p2, r1, r2 = df['High'].iloc[i1], df['High'].iloc[i2], df['RSI'].iloc[i1], df['RSI'].iloc[i2]
                if p2 > p1 and r2 < r1 and r1 >= 62: sigs.append('REG_BEAR')
                elif p2 < p1 and r2 > r1: sigs.append('HID_BEAR')

            # 신호 필터링 및 우선순위 결정이다
            curr_p = df['Close'].iloc[-1]
            vol_msg = " (거래량 동반)" if curr_vol > avg_vol else ""
            info = f"- {name}({symbol}){vol_msg}"

            if 'REG_BEAR' in sigs and 'HID_BULL' in sigs:
                res_line = df['High'].iloc[high_idx[-1]]
                if abs(curr_p - res_line) / res_line < 0.03:
                    final_groups['🚨 강력 하락 주의 (일반 하락)'].append(info + " (고점 저항 근접)")
                else:
                    final_groups['🔄 신호 충돌 (변곡점 주의)'].append(info)
            elif 'REG_BEAR' in sigs:
                final_groups['🚨 강력 하락 주의 (일반 하락)'].append(info)
            elif 'REG_BULL' in sigs:
                final_groups['🆘 진바닥 포착 (일반 상승)'].append(info)
            elif 'HID_BULL' in sigs:
                final_groups['📈 추세 강화 (히든 상승)'].append(info)
            elif 'HID_BEAR' in sigs:
                if curr_vol < avg_vol:
                    final_groups['📉 조정 경고 (히든 하락)'].append(info)

        except: continue

    report = "🏛️ 확장 마켓 구조 분석 리포트 (v134)\n"
    report += f"분석 일시: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
    report += f"분석 대상: {len(ticker_map)}개 종목\n"
    report += "-" * 30 + "\n\n"

    for title, stocks in final_groups.items():
        report += f"■ {title}\n"
        report += "\n".join(stocks) if stocks else "- 해당 없음"
        report += "\n\n"

    report += "-" * 30 + "\n전 섹터 유망주 분석을 마친다이다."
    send_message(report)

if __name__ == "__main__":
    run_analysis_v134()
