import yfinance as yf
import pandas as pd

def calculate_smma(series, period):
    # SMMA(Smoothed Moving Average)는 EMA(2 * period - 1)과 계산 방식이 동일하다
    return series.ewm(span=2 * period - 1, adjust=False).mean()

def get_stock_status(ticker_symbol):
    try:
        # 데이터 가져오기 (최근 40일치)
        ticker = yf.Ticker(ticker_symbol)
        df = ticker.history(period="40d")
        
        if len(df) < 20:
            return "데이터 부족", 0, 0

        # 지표 계산
        df['ma20'] = df['Close'].rolling(window=20).mean()
        df['smma7'] = calculate_smma(df['Close'], 7)
        
        current_price = df['Close'].iloc[-1]
        curr_ma20 = df['ma20'].iloc[-1]
        curr_smma7 = df['smma7'].iloc[-1]
        
        # 이전 종가 대비 변동률 (간소화)
        prev_price = df['Close'].iloc[-2]
        change_pct = ((current_price - prev_price) / prev_price) * 100
        
        # 근접도 및 추세 판별 로직 (사용자 제안 반영)
        gap_ratio = (curr_smma7 - curr_ma20) / curr_ma20
        
        # 판별 조건
        if curr_smma7 < curr_ma20:
            status = "(데드크로스/하락 가능성 큼)"
        elif gap_ratio <= 0.0015: # 0.15% 이내 근접 시 데드크로스로 간별
            status = "(데드크로스/하락 가능성 큼)"
        else:
            status = "🔥"
            
        return status, current_price, change_pct
    except Exception as e:
        return f"오류: {e}", 0, 0

# 분석할 종목 리스트
groups = {
    "슈퍼 종목군": ["MU"],
    "눌림 종목군": ["NVDA", "TSLA", "AAPL", "META", "PLTR", "TSM"],
    "대기 종목군": ["MSFT", "AMZN", "AMD", "AVGO"],
    "위험 종목군": ["MSTR", "COIN"]
}

print("🏛️ 다우 구조 및 데드크로스 분석 리포트 (v113)")
print("=========================")
print("💡 가이드: 🔥는 정배열 상태, 데드크로스 문구는 단기 추세 약화를 의미한다이다.\n")

for group_name, tickers in groups.items():
    print(f"🚀{group_name}" if group_name == "슈퍼 종목군" else f"💎{group_name}" if group_name == "눌림 종목군" else f"📦{group_name}" if group_name == "대기 종목군" else f"🚨{group_name}")
    
    for t in tickers:
        status, price, change = get_stock_status(t)
        print(f"{t}: {price:.1f}$ ({change:+.1f}%) {status}")
    
    print("-" * 20)
    print()

print("=========================")
