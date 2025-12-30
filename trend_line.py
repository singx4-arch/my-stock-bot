import yfinance as yf
import pandas as pd
import requests
import os

token = os.getenv('TELEGRAM_TOKEN')
chat_id = os.getenv('TELEGRAM_CHAT_ID')

def send_message(text):
    if not token or not chat_id: return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    params = {'chat_id': chat_id, 'text': text, 'parse_mode': 'Markdown'}
    requests.get(url, params=params)

ticker_map = { 
    'NVDA': '엔비디아', 'AAPL': '애플', 'MSFT': '마이크로소프트', 'TSLA': '테슬라', 
    'AMZN': '아마존', 'META': '메타', 'GOOGL': '구글', 'AVGO': '브로드컴', 
    'AMD': 'AMD', 'TSM': 'TSMC', 'ASML': 'ASML', 'COST': '코스트코', 
    'QCOM': '퀄컴', 'ARM': 'ARM', 'TQQQ': '나스닥3배레버', 'SOXL': '반도체3배레버',
    'PLTR': '팔란티어', 'MU': '마이크론', 'ORCL': '오라클', 'DELL': '델', 'QQQ': 'QQQ'
}

trend_alerts = []

for symbol, name in ticker_map.items():
    try:
        # 1. 일봉 분석 (200일선 및 일봉 추세선 리테스트)이다
        df_d = yf.download(symbol, period='1y', interval='1d', progress=False)
        if len(df_d) < 200: continue
        if isinstance(df_d.columns, pd.MultiIndex): df_d.columns = df_d.columns.get_level_values(0)

        curr_p = float(df_d['Close'].iloc[-1])
        prev_p = float(df_d['Close'].iloc[-2])
        curr_low = float(df_d['Low'].iloc[-1])
        curr_high = float(df_d['High'].iloc[-1])
        idx_d = len(df_d) - 1
        
        # 200일 이평선 돌파 확인이다
        ma200_series = df_d['Close'].rolling(window=200).mean()
        ma200 = ma200_series.iloc[-1]
        prev_ma200 = ma200_series.iloc[-2]
        
        if curr_p > ma200 and prev_p <= prev_ma200:
            trend_alerts.append(f"🏰 {name}({symbol}): [장기] 200일선 상향 돌파! (강력 신호)")

        # 일봉 하락 추세선 리테스트 지지 확인 (매수 타점)이다
        df_d['PH'] = df_d['High'][(df_d['High'] == df_d['High'].rolling(window=11, center=True).max())]
        phs = df_d.dropna(subset=['PH'])
        if len(phs) >= 2:
            p1, p2 = phs.iloc[-2], phs.iloc[-1]
            x1, y1 = df_d.index.get_loc(p1.name), p1['PH']
            x2, y2 = df_d.index.get_loc(p2.name), p2['PH']
            m_h = (y2 - y1) / (x2 - x1)
            if m_h < 0:
                line_val = m_h * (idx_d - x1) + y1
                # 돌파 후 지지: 이전 종가는 선 위, 현재 저가는 선 근처, 현재 종가도 선 위이다
                if prev_p > line_val and curr_low <= line_val * 1.005 and curr_p >= line_val:
                    trend_alerts.append(f"💎 {name}({symbol}): [리테스트] 돌파 후 지지 확인! (매수 타점)")

        # 일봉 상승 추세선 리테스트 저항 확인 (매도 타점)이다
        df_d['PL'] = df_d['Low'][(df_d['Low'] == df_d['Low'].rolling(window=11, center=True).min())]
        pls = df_d.dropna(subset=['PL'])
        if len(pls) >= 2:
            p1, p2 = pls.iloc[-2], pls.iloc[-1]
            x1, y1 = df_d.index.get_loc(p1.name), p1['PL']
            x2, y2 = df_d.index.get_loc(p2.name), p2['PL']
            m_l = (y2 - y1) / (x2 - x1)
            if m_l > 0:
                line_val = m_l * (idx_d - x1) + y1
                # 이탈 후 저항: 이전 종가는 선 아래, 현재 고가는 선 근처, 현재 종가도 선 아래이다
                if prev_p < line_val and curr_high >= line_val * 0.995 and curr_p <= line_val:
                    trend_alerts.append(f"⚠️ {name}({symbol}): [리테스트] 이탈 후 저항 확인! (매도 타점)")

        # 2. 주봉 분석 (장기 추세선)이다
        df_w = yf.download(symbol, period='2y', interval='1wk', progress=False)
        if len(df_w) < 30: continue
        if isinstance(df_w.columns, pd.MultiIndex): df_w.columns = df_w.columns.get_level_values(0)

        df_w['PH'] = df_w['High'][(df_w['High'] == df_w['High'].rolling(window=21, center=True).max())]
        phs_w = df_w.dropna(subset=['PH'])
        if len(phs_w) >= 2:
            p1_w, p2_w = phs_w.iloc[-2], phs_w.iloc[-1]
            xw1, yw1 = df_w.index.get_loc(p1_w.name), p1_w['PH']
            xw2, yw2 = df_w.index.get_loc(p2_w.name), p2_w['PH']
            mw_h = (yw2 - yw1) / (xw2 - xw1)
            if mw_h < 0:
                w_line = mw_h * (len(df_w) - 1 - xw1) + yw1
                if curr_p > w_line and prev_p <= w_line:
                    trend_alerts.append(f"🏛️ {name}({symbol}): [초장기] 주봉 하락 추세선 돌파!")

    except Exception as e:
        print(f"Error analyzing {symbol}: {e}")
        continue

if trend_alerts:
    msg = "⚖️ [추세 및 리테스트 알림] 시장의 주요 변곡점 포착이다\n" + "-" * 20 + "\n" + "\n\n".join(trend_alerts)
    send_message(msg)
