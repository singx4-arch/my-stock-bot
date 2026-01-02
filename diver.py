import yfinance as yf
import pandas as pd
import requests
import os
from datetime import datetime

token = os.getenv('TELEGRAM_TOKEN') or '7971022798:AAFGQR1zxdCq1urZKgdRzjjsvr3Lt6T9y1I'
chat_id = os.getenv('TELEGRAM_CHAT_ID')

def send_message(text):
    if not token or not chat_id: return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    params = {'chat_id': chat_id, 'text': text, 'disable_notification': 'true'}
    try: requests.post(url, json=params, timeout=15)
    except: pass

def calculate_wilder_rsi(series, period=14):
    delta = series.diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    avg_gain = up.ewm(com=period-1, min_periods=period).mean()
    avg_loss = down.ewm(com=period-1, min_periods=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def detect_divergence_final(df, rsi, curr_rsi_w):
    lows = df['Low'].values
    highs = df['High'].values
    volumes = df['Volume'].values
    length = len(df)
    
    valleys, peaks = [], []
    
    # 해결책: 5일 간격으로 로컬 최저점/최고점을 찾아 더 촘촘하게 데이터를 수집한다이다
    for i in range(max(5, length - 120), length - 5):
        # 저점 후보 (주변 5일보다 낮음)이다
        if rsi.iloc[i] < 45 and all(rsi.iloc[i] <= rsi.iloc[i+j] for j in range(-5, 6)):
            valleys.append({'idx': i, 'rsi': rsi.iloc[i], 'price': lows[i], 'vol': volumes[i]})
        # 고점 후보 (주변 5일보다 높음)이다
        if rsi.iloc[i] > 55 and all(rsi.iloc[i] >= rsi.iloc[i+j] for j in range(-5, 6)):
            peaks.append({'idx': i, 'rsi': rsi.iloc[i], 'price': highs[i], 'vol': volumes[i]})

    msg_list = []
    bull_score, bear_score = 0, 0

    if len(valleys) >= 2:
        v1, v2 = valleys[-2], valleys[-1]
        is_conf = v2['vol'] < v1['vol']
        if v2['price'] < v1['price'] and v2['rsi'] > v1['rsi']:
            msg_list.append(f"{'⭐' if is_conf else '⚠️'}일반상승")
            bull_score += 2 if is_conf else 1
        elif v2['price'] > v1['price'] and v2['rsi'] < v1['rsi']:
            msg_list.append(f"{'⭐' if is_conf else '⚠️'}히든상승")
            bull_score += 2 if is_conf else 1

    if len(peaks) >= 2:
        p1, p2 = peaks[-2], peaks[-1]
        # 주봉 강세 시 하락 신호 가중치 약화이다
        is_conf = (p2['vol'] < p1['vol']) and (curr_rsi_w < 55)
        if p2['price'] > p1['price'] and p2['rsi'] < p1['rsi']:
            msg_list.append(f"{'⭐' if is_conf else '⚠️'}일반하락")
            bear_score += 2 if is_conf else 1
        elif p2['price'] < p1['price'] and p2['rsi'] > p1['rsi']:
            msg_list.append(f"{'⭐' if is_conf else '⚠️'}히든하락")
            bear_score += 2 if is_conf else 1

    if bull_score > bear_score:
        verdict = "✅ 상승우위" if bull_score >= 2 else "🤔 상승관망"
    elif bear_score > bull_score:
        verdict = "🚨 하락우위" if bear_score >= 2 else "⚠️ 하락주의"
    else:
        verdict = "⚪ 중립"

    return verdict, "/".join(msg_list)

def analyze_ticker(ticker):
    try:
        df_d = yf.download(ticker, period='2y', interval='1d', progress=False)
        df_w = yf.download(ticker, period='2y', interval='1wk', progress=False)
        if len(df_d) < 100: return None
        if isinstance(df_d.columns, pd.MultiIndex): df_d.columns = df_d.columns.get_level_values(0)
        if isinstance(df_w.columns, pd.MultiIndex): df_w.columns = df_w.columns.get_level_values(0)

        cp = df_d['Close'].iloc[-1]
        rsi9 = calculate_wilder_rsi(df_d['Close'], 9)
        rsi14w = calculate_wilder_rsi(df_w['Close'], 14)
        
        curr_rsi9 = rsi9.iloc[-1]
        curr_rsi_w = rsi14w.iloc[-1]

        verdict, detail = detect_divergence_final(df_d, rsi9, curr_rsi_w)
        return f"• {ticker:5} | {cp:7.2f}$ | {verdict:7} [{' ' if not detail else detail}]"
    except: return None

def main():
    tickers = ['QQQ', 'TQQQ', 'SOXL', 'NVDA', 'AAPL', 'TSLA', 'PLTR', 'ORCL', 'AMAT', 'LRCX', 'MSFT', 'META']
    
    report = f"🏛️ [통합 분석 리포트 v176]이다\n{datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
    report += "="*25 + "\n"
    
    for t in tickers:
        line = analyze_ticker(t)
        if line: report += line + "\n"
    
    report += "="*25 + "\n※ ⭐확증, ⚠️주의(주봉 강세 시 하락신호 약화)이다."
    send_message(report)

if __name__ == "__main__":
    main()
