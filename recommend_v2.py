import yfinance as yf
import pandas as pd
import requests
import os

token = os.getenv('TELEGRAM_TOKEN')
chat_id = os.getenv('TELEGRAM_CHAT_ID')

def send_message(text):
    if not token or not chat_id: return
    url = f"https://api.telegram.org/bot{token}_sendMessage" # 본인의 봇 API 주소이다
    params = {'chat_id': chat_id, 'text': text}
    requests.get(url, params=params)

ticker_map = { 
    'NVDA': '엔비디아', 'AAPL': '애플', 'MSFT': '마이크로소프트', 'TSLA': '테슬라', 
    'AMZN': '아마존', 'META': '메타', 'GOOGL': '구글', 'AVGO': '브로드컴', 
    'AMD': 'AMD', 'TSM': 'TSMC', 'ASML': 'ASML', 'COST': '코스트코', 
    'QCOM': '퀄컴', 'ARM': 'ARM', 'TQQQ': '나스닥3배레버', 'SOXL': '반도체3배레버',
    'PLTR': '팔란티어', 'MU': '마이크론', 'ORCL': '오라클', 'DELL': '델', 'QQQ': 'QQQ'
}

uptrend_gold = []
consolidation_gold = []

for symbol, name in ticker_map.items():
    try:
        df = yf.download(symbol, period='1y', interval='1d', progress=False)
        if len(df) < 50: continue
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['SMMA7'] = df['Close'].ewm(alpha=1/7, adjust=False).mean()
        
        # 10일 기준 구간 분석이다
        recent = df.iloc[-10:] 
        prev = df.iloc[-20:-10] 
        
        c_h, c_l = float(recent['High'].max()), float(recent['Low'].min()) # 최근 10일이다
        p_h, p_l = float(prev['High'].max()), float(prev['Low'].min()) # 이전 10일이다
        
        curr_p = float(df['Close'].iloc[-1])
        c_ma20 = float(df['MA20'].iloc[-1])
        c_smma7 = float(df['SMMA7'].iloc[-1])
        
        # 다우 이론 핵심 조건: HH와 HL이 모두 커야 한다이다
        is_hh = c_h > p_h
        is_hl = c_l > p_l
        is_gold = curr_p > c_ma20 and c_smma7 > c_ma20
        
        # 리포트에 보여줄 분석 데이터이다
        analysis_data = f"고점: {p_h:.1f} -> {c_h:.1f} ({'↑' if is_hh else '↓'})\n"
        analysis_data += f"저점: {p_l:.1f} -> {c_l:.1f} ({'↑' if is_hl else '↓'})"
        
        info = f"[{name} ({symbol})]\n{analysis_data}\n"
        info += f"현재가: {curr_p:.2f}$ | 손절: {c_l:.2f}$"

        if is_gold:
            if is_hh and is_hl:
                uptrend_gold.append("🚀 " + info)
            else:
                consolidation_gold.append("💤 " + info)

    except: continue

report = "📢 다우 이론 수치 분석 리포트이다\n" + "="*25 + "\n\n"
report += "🚀 상승추세 (HH + HL 만족)이다\n"
report += "\n\n".join(uptrend_gold) if uptrend_gold else "조건 만족 종목 없음이다"
report += "\n\n" + "-"*25 + "\n\n"
report += "💤 보합/주의 (조건 미달성)이다\n"
report += "\n\n".join(consolidation_gold) if consolidation_gold else "해당 종목 없음이다"
report += "\n\n" + "="*25 + "\n"
report += "💡 팁: 화살표가 둘 다 ↑ 여야 🚀 그룹에 들어간다이다"

send_message(report)
