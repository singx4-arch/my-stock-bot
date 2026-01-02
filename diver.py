import yfinance as yf
import pandas as pd
import requests
import os
import json
import numpy as np
from datetime import datetime

token = os.getenv('TELEGRAM_TOKEN') or '7971022798:AAFGQR1zxdCq1urZKgdRzjjsvr3Lt6T9y1I'
chat_id = os.getenv('TELEGRAM_CHAT_ID')
STATE_FILE = 'last_alerts.json'

def send_message(text):
    if not token or not chat_id: return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    params = {'chat_id': chat_id, 'text': text}
    try: requests.get(url, params=params, timeout=10)
    except: pass

def calculate_rsi_9_wilder(data, window=9):
    delta = data.diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    avg_gain = up.ewm(com=window-1, min_periods=window).mean()
    avg_loss = down.ewm(com=window-1, min_periods=window).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def detect_divergence_v174(df):
    df['in_low'] = df['RSI_9'] < 35
    df['in_high'] = df['RSI_9'] > 65
    df['low_group'] = (df['in_low'] != df['in_low'].shift()).cumsum()
    df['high_group'] = (df['in_high'] != df['in_high'].shift()).cumsum()
    
    valleys, peaks = [], []
    for g_id, group in df[df['in_low']].groupby('low_group'):
        if len(group) > 0:
            m_idx = group['RSI_9'].idxmin()
            valleys.append({'idx': m_idx, 'rsi': group['RSI_9'].min(), 'price': df['Low'].loc[m_idx], 'vol': df['Volume'].loc[m_idx]})
    for g_id, group in df[df['in_high']].groupby('high_group'):
        if len(group) > 0:
            m_idx = group['RSI_9'].idxmax()
            peaks.append({'idx': m_idx, 'rsi': group['RSI_9'].max(), 'price': df['High'].loc[m_idx], 'vol': df['Volume'].loc[m_idx]})

    sigs = []
    has_bull, has_bear = False, False

    if len(valleys) >= 2:
        v1, v2 = valleys[-2], valleys[-1]
        if (v2['idx'] - v1['idx']).days < 60:
            is_conf = v2['vol'] < v1['vol']
            icon = "⭐" if is_conf else "⚠️"
            if v2['price'] < v1['price'] and v2['rsi'] > v1['rsi']:
                sigs.append(f"{icon} 일반 상승 (바닥 반전)")
                has_bull = True
            elif v2['price'] > v1['price'] and v2['rsi'] < v1['rsi']:
                sigs.append(f"{icon} 히든 상승 (추세 지속)")
                has_bull = True

    if len(peaks) >= 2:
        p1, p2 = peaks[-2], peaks[-1]
        if (p2['idx'] - p1['idx']).days < 60:
            is_conf = p2['vol'] < p1['vol']
            icon = "⭐" if is_conf else "⚠️"
            if p2['price'] > p1['price'] and p2['rsi'] < p1['rsi']:
                sigs.append(f"{icon} 일반 하락 (천장 반전)")
                has_bear = True
            elif p2['price'] < p1['price'] and p2['rsi'] > p1['rsi']:
                sigs.append(f"{icon} 히든 하락 (추세 하락)")
                has_bear = True

    verdict = ""
    if has_bull and has_bear:
        verdict = "⚖️ [중립/혼조] 상승과 하락 에너지가 충돌 중이다. 지지선 대응이 핵심이다이다."
    elif has_bull:
        verdict = "✅ [상승 우위] 바닥 매수세가 더 강력하게 작용하고 있다이다."
    elif has_bear:
        verdict = "🚨 [하락 우위] 천장 매도 압력이 지배적인 구간이다이다."
    
    return sigs, verdict

def main():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            try: last_alerts = json.load(f)
            except: last_alerts = {}
    else: last_alerts = {}

    ticker_map = {
        'QQQ': '나스닥100', 'TQQQ': '나스닥3배', 'SOXL': '반도체3배', 'NVDA': '엔비디아', 
        'TSLA': '테슬라', 'PLTR': '팔란티어', 'AMAT': '어플라이드', 'LRCX': '램리서치',
        'GLW': '코닝', 'CCJ': '우라늄', 'CEG': '원자력'
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
            sigs, verdict = detect_divergence_v174(df)
            
            state_key = f"{symbol}_{''.join(sigs)}"
            if sigs and last_alerts.get(symbol) != state_key:
                stock_report = f"• {name}({symbol}) | RSI: {round(df['RSI_9'].iloc[-1], 2)}\n"
                stock_report += f"  신호: {', '.join(sigs)}\n"
                stock_report += f"  판정: {verdict}"
                report_content.append(stock_report)
                new_alerts[symbol] = state_key
                any_new_signal = True
        except: continue

    if any_new_signal:
        report = "🏛️ 통합 매집 분석 리포트 (v174 - 정밀 판정)\n"
        report += f"분석 일시: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        report += "="*20 + "\n\n"
        report += "\n\n".join(report_content)
        send_message(report)
        with open(STATE_FILE, 'w') as f: json.dump(new_alerts, f)

if __name__ == "__main__":
    main()
