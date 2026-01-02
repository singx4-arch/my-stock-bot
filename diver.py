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
    # 메시지가 길어질 수 있으므로 나누어 보내는 처리가 필요할 수 있음
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
    in_low, in_high = False, False
    curr_v, curr_p = None, None

    # 해결책 1: RSI 탐색 범위를 40/60으로 넓혀서 신호 포착 민감도를 높였다이다
    for i in range(max(0, length - 120), length):
        r = rsi.iloc[i]
        if r < 40:
            if not in_low:
                in_low = True
                curr_v = {'idx': i, 'rsi': r, 'price': lows[i], 'vol': volumes[i]}
            elif r < curr_v['rsi']:
                curr_v = {'idx': i, 'rsi': r, 'price': lows[i], 'vol': volumes[i]}
        else:
            if in_low: valleys.append(curr_v); in_low = False
        
        if r > 60:
            if not in_high:
                in_high = True
                curr_p = {'idx': i, 'rsi': r, 'price': highs[i], 'vol': volumes[i]}
            elif r > curr_p['rsi']:
                curr_p = {'idx': i, 'rsi': r, 'price': highs[i], 'vol': volumes[i]}
        else:
            if in_high: peaks.append(curr_p); in_high = False

    msg = ""
    bull_score, bear_score = 0, 0

    if len(valleys) >= 2:
        v1, v2 = valleys[-2], valleys[-1]
        if (v2['idx'] - v1['idx']) < 60:
            is_conf = v2['vol'] < v1['vol']
            icon = "⭐" if is_conf else "⚠️"
            if v2['price'] < v1['price'] and v2['rsi'] > v1['rsi']:
                msg += f"{icon} 일반 상승\n"
                bull_score += 2 if is_conf else 1
            elif v2['price'] > v1['price'] and v2['rsi'] < v1['rsi']:
                msg += f"{icon} 히든 상승\n"
                bull_score += 2 if is_conf else 1

    if len(peaks) >= 2:
        p1, p2 = peaks[-2], peaks[-1]
        if (p2['idx'] - p1['idx']) < 60:
            is_conf = p2['vol'] < p1['vol']
            # 해결책 2: 주봉 RSI가 50 이상이면 하락 신호의 신뢰도를 낮춘다이다
            if curr_rsi_w > 50:
                is_conf = False
            
            icon = "⭐" if is_conf else "⚠️"
            if p2['price'] > p1['price'] and p2['rsi'] < p1['rsi']:
                msg += f"{icon} 일반 하락\n"
                bear_score += 2 if is_conf else 1
            elif p2['price'] < p1['price'] and p2['rsi'] > p1['rsi']:
                msg += f"{icon} 히든 하락\n"
                bear_score += 2 if is_conf else 1

    # 최종 판정
    if bull_score > bear_score:
        verdict = "✅ 상승 우위" if bull_score >= 2 else "🤔 상승 관망"
    elif bear_score > bull_score:
        verdict = "🚨 하락 우위" if bear_score >= 2 else "⚠️ 하락 주의"
    else:
        verdict = "⚪ 중립/신호없음"

    return verdict, msg.strip()

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
        
        # 통합 리포트를 위한 한 줄 요약 형식이다
        line = f"• {ticker} | {cp:.2f}$ | RSI: {curr_rsi9:.1f}/{curr_rsi_w:.1f}\n"
        line += f"  판정: {verdict} {('[' + detail + ']') if detail else ''}\n"
        return line
    except:
        return None

def main():
    tickers = ['QQQ', 'TQQQ', 'SOXL', 'NVDA', 'AAPL', 'TSLA', 'PLTR', 'ORCL', 'AMAT', 'LRCX', 'MSFT', 'META']
    
    # 해결책 3: 모든 리포트를 하나로 통합한다이다
    combined_report = "🏛️ [전 종목 통합 분석 리포트 v175]이다\n"
    combined_report += f"분석 일시: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
    combined_report += "====================\n\n"
    
    for t in tickers:
        report_line = analyze_ticker(t)
        if report_line:
            combined_report += report_line + "\n"
    
    combined_report += "--------------------\n"
    combined_report += "※ RSI: (일봉9d/주봉14w) 수치이다.\n"
    combined_report += "※ ⭐확증, ⚠️거짓(주봉 강세 시 하락신호 무시)이다."
    
    send_message(combined_report)

if __name__ == "__main__":
    main()
