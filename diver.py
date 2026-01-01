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

# 블로그 참조: RSI 9일 및 Wilder's Smoothing 적용이다
def calculate_rsi_wilder(data, window=9):
    delta = data.diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    
    # 블로그 코드의 ewm(com=window-1) 방식과 동일하다이다
    avg_gain = up.ewm(com=window-1, min_periods=window).mean()
    avg_loss = down.ewm(com=window-1, min_periods=window).mean()
    
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# 블로그 참조: 과매도/과매수 구간의 최소/최대치를 비교하는 다이버전스 로직이다
def detect_divergence_expert(df, low_barrier=30, high_barrier=70):
    # 최근 2개의 우물(RSI < 30)과 2개의 산(RSI > 70) 구간을 추출한다이다
    df['in_low'] = df['RSI'] < low_barrier
    df['in_high'] = df['RSI'] > high_barrier
    
    # 구간이 바뀌는 지점을 찾는다이다
    df['low_group'] = (df['in_low'] != df['in_low'].shift()).cumsum()
    df['high_group'] = (df['in_high'] != df['in_high'].shift()).cumsum()
    
    low_valleys = []
    high_peaks = []
    
    # 과매도 구간들 분석이다
    for g_id, group in df[df['in_low']].groupby('low_group'):
        if len(group) > 0:
            min_rsi_idx = group['RSI'].idxmin()
            low_valleys.append({
                'idx': min_rsi_idx,
                'rsi': group['RSI'].min(),
                'price': df['Low'].loc[min_rsi_idx]
            })
            
    # 과매수 구간들 분석이다
    for g_id, group in df[df['in_high']].groupby('high_group'):
        if len(group) > 0:
            max_rsi_idx = group['RSI'].idxmax()
            high_peaks.append({
                'idx': max_rsi_idx,
                'rsi': group['RSI'].max(),
                'price': df['High'].loc[max_rsi_idx]
            })

    sig = None
    # 블로그 로직: 이전 우물보다 현재 우물이 RSI는 높고 가격은 낮으면 상승 다이버전스이다
    if len(low_valleys) >= 2:
        v1, v2 = low_valleys[-2], low_valleys[-1]
        # 시간 간격이 너무 멀지 않은지 확인(최근 60일 이내)한다이다
        if (v2['idx'] - v1['idx']).days < 60:
            if v2['price'] < v1['price'] and v2['rsi'] > v1['rsi']:
                sig = 'REG_BULL'
            elif v2['price'] > v1['price'] and v2['rsi'] < v1['rsi']:
                sig = 'HID_BULL'

    # 하락 다이버전스 로직이다
    if len(high_peaks) >= 2:
        p1, p2 = high_peaks[-2], high_peaks[-1]
        if (p2['idx'] - p1['idx']).days < 60:
            if p2['price'] > p1['price'] and p2['rsi'] < p1['rsi']:
                sig = 'REG_BEAR'
            elif p2['price'] < p1['price'] and p2['rsi'] > p1['rsi']:
                sig = 'HID_BEAR'
                
    return sig

# 3. 메인 분석 엔진 (v136)이다
def run_analysis_v136():
    ticker_map = {
        'QQQ': '나스닥100', 'TQQQ': '나스닥3배', 'SOXL': '반도체3배', 'SPY': 'S&P500',
        'NVDA': '엔비디아', 'TSM': 'TSMC', 'AVGO': '브로드컴', 'ASML': 'ASML', 
        'AMD': 'AMD', 'MU': '마이크론', 'AMAT': '어플라이드', 'LRCX': '램리서치', 
        'QCOM': '퀄컴', 'ARM': 'ARM', 'SMCI': '슈퍼마이크로', 'INTC': '인텔',
        'MSFT': '마이크로소프트', 'AAPL': '애플', 'AMZN': '아마존', 'META': '메타', 
        'GOOGL': '구글', 'PLTR': '팔란티어', 'ORCL': '오라클', 'NOW': '서비스나우',
        'ANET': '아리스타', 'VRT': '버티브', 'DELL': '델', 'IBM': 'IBM',
        'TSLA': '테슬라', 'MSTR': '마이크로스트래티지', 'COIN': '코인베이스', 'IONQ': '아이온큐',
        'NFLX': '넷플릭스', 'UBER': '우버', 'SHOP': '쇼피파이', 'HOOD': '로빈후드',
        'VST': '비스트라', 'CEG': '컨스텔레이션', 'OKLO': '오클로', 'SMR': '뉴스케일',
        'NLR': '우라늄ETF', 'XLE': '에너지ETF', 'GLW': '코닝'
    }

    report_groups = {
        '🆘 진바닥 포착 (일반 상승)': [],
        '🚨 강력 하락 주의 (일반 하락)': [],
        '📈 추세 강화 (히든 상승)': [],
        '📉 조정 경고 (히든 하락)': []
    }

    for symbol, name in ticker_map.items():
        try:
            df = yf.download(symbol, period='1y', interval='1d', progress=False)
            if len(df) < 60: continue
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            
            df['RSI'] = calculate_rsi_wilder(df['Close'], window=9)
            sig = detect_divergence_expert(df)
            
            info = f"- {name}({symbol})"
            if sig == 'REG_BULL': report_groups['🆘 진바닥 포착 (일반 상승)'].append(info)
            elif sig == 'REG_BEAR': report_groups['🚨 강력 하락 주의 (일반 하락)'].append(info)
            elif sig == 'HID_BULL': report_groups['📈 추세 강화 (히든 상승)'].append(info)
            elif sig == 'HID_BEAR': report_groups['📉 조정 경고 (히든 하락)'].append(info)
        except: continue

    report = "🏛️ 블로그 로직 기반 정밀 분석 리포트 (v136)\n"
    report += f"분석 일시: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
    report += "-" * 30 + "\n\n"

    for title, stocks in report_groups.items():
        report += f"■ {title}\n"
        report += "\n".join(stocks) if stocks else "- 해당 없음"
        report += "\n\n"

    report += "-" * 30 + "\n와일더 RSI 9일선 및 우물 추적 로직을 적용했다이다."
    send_message(report)

if __name__ == "__main__":
    run_analysis_v136()
