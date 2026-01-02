import yfinance as yf
import pandas as pd
import requests
import os
import json
import numpy as np
from datetime import datetime

token = os.getenv('TELEGRAM_TOKEN')
chat_id = os.getenv('TELEGRAM_CHAT_ID')
STATE_FILE = 'last_alerts.json'

def send_message(text):
    if not token or not chat_id: return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    params = {'chat_id': chat_id, 'text': text}
    try:
        requests.get(url, params=params, timeout=10)
    except: pass

def calculate_rsi_9_wilder(data, window=9):
    delta = data.diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    avg_gain = up.ewm(com=window-1, min_periods=window).mean()
    avg_loss = down.ewm(com=window-1, min_periods=window).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def detect_divergence_1d(df):
    df['in_low'] = df['RSI_9'] < 35
    df['in_high'] = df['RSI_9'] > 65
    df['low_group'] = (df['in_low'] != df['in_low'].shift()).cumsum()
    df['high_group'] = (df['in_high'] != df['in_high'].shift()).cumsum()
    
    valleys, peaks = [], []
    for g_id, group in df[df['in_low']].groupby('low_group'):
        if len(group) > 0:
            m_idx = group['RSI_9'].idxmin()
            valleys.append({'idx': m_idx, 'rsi': group['RSI_9'].min(), 'price': df['Low'].loc[m_idx]})
    for g_id, group in df[df['in_high']].groupby('high_group'):
        if len(group) > 0:
            m_idx = group['RSI_9'].idxmax()
            peaks.append({'idx': m_idx, 'rsi': group['RSI_9'].max(), 'price': df['High'].loc[m_idx]})

    status = None
    if len(valleys) >= 2:
        v1, v2 = valleys[-2], valleys[-1]
        if (v2['idx'] - v1['idx']).days < 60:
            if v2['price'] < v1['price'] and v2['rsi'] > v1['rsi']: status = '일반 상승 (바닥 반전)'
            elif v2['price'] > v1['price'] and v2['rsi'] < v1['rsi']: status = '히든 상승 (추세 지속)'
    if len(peaks) >= 2:
        p1, p2 = peaks[-2], peaks[-1]
        if (p2['idx'] - p1['idx']).days < 60:
            if p2['price'] > p1['price'] and p2['rsi'] < p1['rsi']: status = '일반 하락 (천장 반전)'
            elif p2['price'] < p1['price'] and p2['rsi'] > p1['rsi']: status = '히든 하락 (추세 하락)'
    return status

def main():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            try: last_alerts = json.load(f)
            except: last_alerts = {}
    else:
        last_alerts = {}

    emoji_map = {
        '일반 상승 (바닥 반전)': '🆘 [강력 매수/바닥 포착]',
        '히든 상승 (추세 지속)': '📈 [추세 지속/눌림목]',
        '일반 하락 (천장 반전)': '🚨 [위험/천장 하락주의]',
        '히든 하락 (추세 하락)': '📉 [하락 지속/탈출권고]'
    }

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

    # 신호들을 담을 딕셔너리이다
    report_data = {key: [] for key in emoji_map.keys()}
    new_alerts = last_alerts.copy()
    any_new_signal = False

    for symbol, name in ticker_map.items():
        try:
            df = yf.download(symbol, period='1y', interval='1d', progress=False)
            if len(df) < 50: continue
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            df['RSI_9'] = calculate_rsi_9_wilder(df['Close'])
            res = detect_divergence_1d(df)
            
            # 신호가 있고 이전 신호와 다를 경우에만 리포트에 추가한다이다
            if res and last_alerts.get(symbol) != res:
                curr_rsi = round(df['RSI_9'].iloc[-1], 2)
                report_data[res].append(f"• {name}({symbol}) | RSI: {curr_rsi}")
                new_alerts[symbol] = res
                any_new_signal = True
            elif not res:
                new_alerts[symbol] = None
        except: continue

    # 새로운 신호가 하나라도 있으면 리포트를 작성한다이다
    if any_new_signal:
        report = "🏛️ 시장 다이버전스 통합 리포트\n"
        report += f"분석 일시: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        report += "="*20 + "\n\n"

        for status, signals in report_data.items():
            if signals:
                report += f"{emoji_map[status]}\n"
                report += "\n".join(signals) + "\n\n"

        send_message(report)
        
        # 상태 업데이트 및 저장이다
        with open(STATE_FILE, 'w') as f:
            json.dump(new_alerts, f)

if __name__ == "__main__":
    main()
