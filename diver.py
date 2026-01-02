import yfinance as yf
import pandas as pd
import requests
import os
import json
import numpy as np
from datetime import datetime

# 환경 변수 설정이다
token = os.getenv('TELEGRAM_TOKEN') or '7971022798:AAFGQR1zxdCq1urZKgdRzjjsvr3Lt6T9y1I'
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

# 거래량 분석이 포함된 정밀 다이버전스 판독 함수이다
def detect_divergence_v173(df):
    df['in_low'] = df['RSI_9'] < 35
    df['in_high'] = df['RSI_9'] > 65
    df['low_group'] = (df['in_low'] != df['in_low'].shift()).cumsum()
    df['high_group'] = (df['in_high'] != df['in_high'].shift()).cumsum()
    
    valleys, peaks = [], []
    for g_id, group in df[df['in_low']].groupby('low_group'):
        if len(group) > 0:
            m_idx = group['RSI_9'].idxmin()
            valleys.append({
                'idx': m_idx, 
                'rsi': group['RSI_9'].min(), 
                'price': df['Low'].loc[m_idx],
                'vol': df['Volume'].loc[m_idx]
            })
    for g_id, group in df[df['in_high']].groupby('high_group'):
        if len(group) > 0:
            m_idx = group['RSI_9'].idxmax()
            peaks.append({
                'idx': m_idx, 
                'rsi': group['RSI_9'].max(), 
                'price': df['High'].loc[m_idx],
                'vol': df['Volume'].loc[m_idx]
            })

    results = []
    bull_score, bear_score = 0, 0

    if len(valleys) >= 2:
        v1, v2 = valleys[-2], valleys[-1]
        if (v2['idx'] - v1['idx']).days < 60:
            is_confirmed = v2['vol'] < v1['vol']
            icon = "⭐" if is_confirmed else "⚠️"
            vol_msg = "(신뢰: 매도 소진)" if is_confirmed else "(거짓: 매도 잔존)"
            score = 2 if is_confirmed else 1
            if v2['price'] < v1['price'] and v2['rsi'] > v1['rsi']:
                results.append(f"{icon} 일반 상승 {vol_msg}")
                bull_score += score
            elif v2['price'] > v1['price'] and v2['rsi'] < v1['rsi']:
                results.append(f"{icon} 히든 상승 {vol_msg}")
                bull_score += score

    if len(peaks) >= 2:
        p1, p2 = peaks[-2], peaks[-1]
        if (p2['idx'] - p1['idx']).days < 60:
            is_confirmed = p2['vol'] < p1['vol']
            icon = "⭐" if is_confirmed else "⚠️"
            vol_msg = "(신뢰: 매수 약화)" if is_confirmed else "(거짓: 매수 잔존)"
            score = 2 if is_confirmed else 1
            if p2['price'] > p1['price'] and p2['rsi'] < p1['rsi']:
                results.append(f"{icon} 일반 하락 {vol_msg}")
                bear_score += score
            elif p2['price'] < p1['price'] and p2['rsi'] > p1['rsi']:
                results.append(f"{icon} 히든 하락 {vol_msg}")
                bear_score += score

    # 최종 판정 문구 생성이다
    verdict = ""
    if bull_score > bear_score:
        verdict = "✅ [상승 우위] 바닥 매수 에너지가 더 강력하다이다." if bull_score >= 2 else "🤔 [상승 관망] 징후는 있으나 힘이 약하다이다."
    elif bear_score > bull_score:
        verdict = "🚨 [하락 우위] 천장 매도 압력이 더 강력하다이다." if bear_score >= 2 else "⚠️ [하락 주의] 조정 가능성이 감지된다이다."
    elif bull_score > 0 and bull_score == bear_score:
        verdict = "⚖️ [중립/혼조] 힘의 균형이 팽팽한 대립 구간이다이다."
    
    return results, verdict

def main():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            try: last_alerts = json.load(f)
            except: last_alerts = {}
    else: last_alerts = {}

    ticker_map = {
        'QQQ': '나스닥100', 'TQQQ': '나스닥3배', 'SOXL': '반도체3배', 'SPY': 'S&P500',
        'NVDA': '엔비디아', 'TSLA': '테슬라', 'MSFT': '마이크로소프트', 'AAPL': '애플',
        'PLTR': '팔란티어', 'AMAT': '어플라이드', 'LRCX': '램리서치', 'MU': '마이크론',
        'GLW': '코닝', 'CCJ': '우라늄', 'CEG': '원자력', 'ALB': '리튬'
    }

    report_content = []
    new_alerts = last_alerts.copy()
    any_new_signal = False

    for symbol, name in ticker_map.items():
        try:
            df = yf.download(symbol, period='1y', interval='1d', progress=False)
            if len(df) < 50: continue
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            
            df['RSI_9'] = calculate_rsi_9_wilder(df['Close'])
            signals, verdict = detect_divergence_v173(df)
            
            # 신호가 존재하고 이전 상태와 변화가 있을 때만 리포트에 추가한다이다
            state_key = f"{symbol}_{''.join(signals)}"
            if signals and last_alerts.get(symbol) != state_key:
                curr_rsi = round(df['RSI_9'].iloc[-1], 2)
                stock_report = f"• {name}({symbol}) | RSI: {curr_rsi}\n"
                stock_report += f"  신호: {', '.join(signals)}\n"
                stock_report += f"  판정: {verdict}"
                report_content.append(stock_report)
                new_alerts[symbol] = state_key
                any_new_signal = True
            elif not signals:
                new_alerts[symbol] = None
        except: continue

    if any_new_signal:
        report = "🏛️ 통합 매집 및 다이버전스 판정 리포트 (v173)\n"
        report += f"분석 일시: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        report += "⭐는 신뢰도 높음, ⚠️는 거짓 신호 가능성이다.\n"
        report += "="*20 + "\n\n"
        report += "\n\n".join(report_content)
        
        send_message(report)
        with open(STATE_FILE, 'w') as f:
            json.dump(new_alerts, f)

if __name__ == "__main__":
    main()
