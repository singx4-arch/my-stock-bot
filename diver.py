import yfinance as yf
import pandas as pd
import requests
import os
import numpy as np

token = os.getenv('TELEGRAM_TOKEN') or '7971022798:AAFGQR1zxdCq1urZKgdRzjjsvr3Lt6T9y1I'
chat_id = os.getenv('TELEGRAM_CHAT_ID')

def send_message(text):
    if not token or not chat_id: return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    params = {'chat_id': chat_id, 'text': text, 'disable_notification': 'true'}
    try: requests.get(url, params=params, timeout=10)
    except: pass

def calculate_wilder_rsi(series, period=14):
    delta = series.diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    avg_gain = up.ewm(com=period-1, min_periods=period).mean()
    avg_loss = down.ewm(com=period-1, min_periods=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def detect_divergence_final(df, rsi):
    lows = df['Low'].values
    highs = df['High'].values
    volumes = df['Volume'].values
    length = len(df)
    
    valleys, peaks = [], []
    in_low, in_high = False, False
    curr_v, curr_p = None, None

    # 자바스크립트와 동일하게 최근 120개 캔들 분석이다
    start_idx = max(0, length - 120)
    for i in range(start_idx, length):
        r = rsi.iloc[i]
        # 저점 탐색 (RSI < 35)이다
        if r < 35:
            if not in_low:
                in_low = True
                curr_v = {'idx': i, 'rsi': r, 'price': lows[i], 'vol': volumes[i]}
            elif r < curr_v['rsi']:
                curr_v = {'idx': i, 'rsi': r, 'price': lows[i], 'vol': volumes[i]}
        else:
            if in_low:
                valleys.append(curr_v)
                in_low = False
        
        # 고점 탐색 (RSI > 65)이다
        if r > 65:
            if not in_high:
                in_high = True
                curr_p = {'idx': i, 'rsi': r, 'price': highs[i], 'vol': volumes[i]}
            elif r > curr_p['rsi']:
                curr_p = {'idx': i, 'rsi': r, 'price': highs[i], 'vol': volumes[i]}
        else:
            if in_high:
                peaks.append(curr_p)
                in_high = False

    msg = ""
    bull_score, bear_score = 0, 0

    # 상승 다이버전스 판정 로직이다
    if len(valleys) >= 2:
        v1, v2 = valleys[-2], valleys[-1]
        if (v2['idx'] - v1['idx']) < 60:
            is_conf = v2['vol'] < v1['vol']
            icon = "⭐" if is_conf else "⚠️"
            txt = "(신뢰: 매도 소진)" if is_conf else "(거짓: 매도 압력 잔존)"
            if v2['price'] < v1['price'] and v2['rsi'] > v1['rsi']:
                msg += f"{icon} 일반 상승 다이버전스 {txt}\n"
                bull_score += 2 if is_conf else 1
            elif v2['price'] > v1['price'] and v2['rsi'] < v1['rsi']:
                msg += f"{icon} 히든 상승 다이버전스 {txt}\n"
                bull_score += 2 if is_conf else 1

    # 하락 다이버전스 판정 로직이다
    if len(peaks) >= 2:
        p1, p2 = peaks[-2], peaks[-1]
        if (p2['idx'] - p1['idx']) < 60:
            is_conf = p2['vol'] < p1['vol']
            icon = "⭐" if is_conf else "⚠️"
            txt = "(신뢰: 매수세 약화)" if is_conf else "(거짓: 매수세 잔존)"
            if p2['price'] > p1['price'] and p2['rsi'] < p1['rsi']:
                msg += f"{icon} 일반 하락 다이버전스 {txt}\n"
                bear_score += 2 if is_conf else 1
            elif p2['price'] < p1['price'] and p2['rsi'] > p1['rsi']:
                msg += f"{icon} 히든 하락 다이버전스 {txt}\n"
                bear_score += 2 if is_conf else 1

    # 최종 판정 로직 (자바스크립트 v172와 동일하게 수정)이다
    verdict = ""
    if bull_score > bear_score:
        verdict = "✅ [상승 우위] 바닥 매수 에너지가 더 강력하다이다." if bull_score >= 2 else "🤔 [관망] 반등 징후가 있으나 확심이 부족하다이다."
    elif bear_score > bull_score:
        verdict = "🚨 [하락 우위] 천장 매도 압력이 더 강력하다이다." if bear_score >= 2 else "⚠️ [주의] 조정 징후가 포착되나 속임수일 수 있다이다."
    elif bull_score > 0 and bull_score == bear_score:
        verdict = "⚖️ [중립/혼조] 힘의 균형이 팽팽하다. 지지선 대응이 최선이다이다."
    else:
        verdict = "⚪ 현재 뚜렷한 다이버전스 신호가 포착되지 않는다이다."

    return msg, verdict

def analyze_ticker(ticker):
    try:
        # 1. 일봉 데이터 (2년치) 가져오기이다
        df_d = yf.download(ticker, period='2y', interval='1d', progress=False)
        if len(df_d) < 100: return None
        if isinstance(df_d.columns, pd.MultiIndex): df_d.columns = df_d.columns.get_level_values(0)

        # 2. 주봉 데이터 (2년치) 가져오기이다
        df_w = yf.download(ticker, period='2y', interval='1wk', progress=False)
        if isinstance(df_w.columns, pd.MultiIndex): df_w.columns = df_w.columns.get_level_values(0)

        cp = df_d['Close'].iloc[-1]
        
        # RSI 계산 (일봉 9일, 주봉 14주)이다
        rsi9 = calculate_wilder_rsi(df_d['Close'], 9)
        rsi14w = calculate_wilder_rsi(df_w['Close'], 14)
        
        curr_rsi9 = rsi9.iloc[-1]
        curr_rsi_w = rsi14w.iloc[-1]

        # 다이버전스 분석 호출이다
        div_msg, verdict = detect_divergence_final(df_d, rsi9)
        
        res = f"🏛️ [{ticker} 통합 분석 리포트 v172-Py]이다\n"
        res += f"현재가: {cp:.2f}$\n"
        res += "--------------------\n\n"
        res += f"📢 [다이버전스 최종 분석 판정]이다\n{verdict}\n\n"
        
        if div_msg:
            res += f"🔍 [상세 신호 모니터링]이다\n{div_msg}\n"
            
        res += f"RSI(9d): {curr_rsi9:.2f} / RSI(14w): {curr_rsi_w:.2f}\n"
        res += "--------------------\n"
        res += "※ ⭐는 신뢰도가 높은 신호, ⚠️는 거짓 신호 가능성이 있다이다."
        
        return res
    except Exception as e:
        print(f"{ticker} 오류: {e}")
        return None

def main():
    tickers = ['PLTR', 'ORCL', 'NVDA', 'TSLA', 'AAPL', 'AMAT', 'LRCX']
    for t in tickers:
        report = analyze_ticker(t)
        if report:
            send_message(report)

if __name__ == "__main__":
    main()
