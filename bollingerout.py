// breakout.gs (v279 신호별 개별 쿨다운 적용 버전)이다

function runAutomaticMonitor() {
  var now = new Date();
  // 한국 시간(KST) 기준으로 현재 시와 분을 가져온다이다
  var kstDate = new Date(now.toLocaleString("en-US", {timeZone: "Asia/Seoul"}));
  var hour = kstDate.getHours();
  var minute = kstDate.getMinutes();

  // 1. 미국 장 운영 시간 판별이다 (한국 시간 밤 10시 ~ 새벽 6시)
  // 서머타임을 고려하여 범위를 넉넉하게 잡았다이다.
  var isMarketOpen = (hour >= 22 || hour < 6);

  // 2. 장외 시간(낮)일 경우의 필터링 로직이다
  if (!isMarketOpen) {
    // 장이 닫혀 있는 낮 시간에는 매시 0분 ~ 5분 사이의 요청만 처리한다이다.
    // 이렇게 하면 5분 트리거가 돌아가도 결과적으로 1시간에 딱 한 번만 실행된다이다.
    if (minute > 5) {
      Logger.log("현재 시간(" + hour + ":" + minute + ")은 장외 시간이므로 할당량 절약을 위해 종료한다이다.");
      return; 
    }
  }

  // 3. 조건이 맞으면(장이 열렸거나, 낮 시간의 정각이거나) 실제 분석을 시작한다이다
  processAllSignals(false);
}

function checkStatusNow() {
  processAllSignals(true);
}

function checkBollingerOnlyNow() {
  var tickerMap = getTickerMap();
  var tickers = Object.keys(tickerMap);
  var bbData = {};
  sendTelegramMessage(MY_GROUP_ID, "🔎 [실시간 볼린저 이탈 전수조사]를 시작한다이다.");

  for (var i = 0; i < tickers.length; i++) {
    var symbol = tickers[i];
    var displayName = tickerMap[symbol] + "(" + symbol + ")";
    try {
      var resH = UrlFetchApp.fetch("https://query1.finance.yahoo.com/v8/finance/chart/" + symbol + "?range=1mo&interval=1h", getFetchOptions());
      var dataH = JSON.parse(resH.getContentText());
      if (dataH.chart && dataH.chart.result) {
        analyzeHourly(symbol, displayName, getCategory(symbol), dataH.chart.result[0], { bollinger: bbData }, true);
      }
      Utilities.sleep(200);
    } catch (e) { Logger.log(symbol + " 조회 실패다이다."); }
  }

  var msg = "📊 볼린저 이탈 실시간 현황 (1H 주기로 업데이트)\n--------------------\n";
  var hasBB = false;
  var sectorOrder = ["💠 반도체 및 장비 섹터", "🤖 AI 및 소프트웨어 섹터", "⚡ 에너지 및 전력 인프라", "📈 지수 및 기타 주요 종목"];
  
  sectorOrder.forEach(s => {
    if (bbData[s]) {
      msg += "\n[" + s + "]\n";
      Object.keys(bbData[s]).forEach(t => { msg += "• " + t + ": " + bbData[s][t].join(", ") + "\n"; });
      hasBB = true;
    }
  });
  sendTelegramMessage(MY_GROUP_ID, hasBB ? msg.trim() : "✅ 현재 감지된 볼린저 이탈 종목이 없다이다.");
}

function processAllSignals(isForced) {
  var lock = LockService.getScriptLock();
  try {
    if (!lock.tryLock(30000)) return;

    var tickerMap = getTickerMap();
    var tickers = Object.keys(tickerMap);
    var reportData = { breakout: {}, bollinger: {}, volumeBurst: {} };

    for (var i = 0; i < tickers.length; i++) {
      var symbol = tickers[i];
      var name = tickerMap[symbol];
      var category = getCategory(symbol);
      var displayName = name + "(" + symbol + ")";

      try {
        var options = getFetchOptions();
        
        var resD = UrlFetchApp.fetch("https://query1.finance.yahoo.com/v8/finance/chart/" + symbol + "?range=3mo&interval=1d", options);
        var dataD = JSON.parse(resD.getContentText());
        if (dataD.chart && dataD.chart.result) analyzeDaily(symbol, displayName, category, dataD.chart.result[0], reportData, isForced);

        Utilities.sleep(200);
        var resH = UrlFetchApp.fetch("https://query1.finance.yahoo.com/v8/finance/chart/" + symbol + "?range=1mo&interval=1h", options);
        var dataH = JSON.parse(resH.getContentText());
        if (dataH.chart && dataH.chart.result) analyzeHourly(symbol, displayName, category, dataH.chart.result[0], reportData, isForced);

        Utilities.sleep(200);
        var resM = UrlFetchApp.fetch("https://query1.finance.yahoo.com/v8/finance/chart/" + symbol + "?range=1d&interval=1m", options);
        var dataM = JSON.parse(resM.getContentText());
        if (dataM.chart && dataM.chart.result) analyzeVolumeBurst(symbol, displayName, category, dataM.chart.result[0], reportData, isForced);

      } catch (e) { Logger.log(symbol + " 분석 오류 스킵이다."); }
      Utilities.sleep(300);
    }
    sendUnifiedMessage(reportData, isForced);
  } catch (e) {
    Logger.log("전체 실행 오류: " + e.message);
  } finally {
    lock.releaseLock();
  }
}

function sendUnifiedMessage(data, isForced) {
  var finalMsg = "";
  var sectorOrder = ["💠 반도체 및 장비 섹터", "🤖 AI 및 소프트웨어 섹터", "⚡ 에너지 및 전력 인프라", "📈 지수 및 기타 주요 종목"];

  var volMsg = "";
  var hasVol = false;
  sectorOrder.forEach(s => {
    if (data.volumeBurst[s]) {
      volMsg += "\n[" + s + "]\n";
      Object.keys(data.volumeBurst[s]).forEach(t => { volMsg += "• " + t + ": " + data.volumeBurst[s][t].join(", ") + "\n"; });
      hasVol = true;
    }
  });
  if (hasVol) finalMsg += "🚨 거래량 폭발 감지 (당일 1회)\n--------------------\n" + volMsg + "\n\n";

  var brkMsg = "";
  var hasBrk = false;
  sectorOrder.forEach(s => {
    if (data.breakout[s]) {
      brkMsg += "\n[" + s + "]\n";
      Object.keys(data.breakout[s]).forEach(t => { brkMsg += "• " + t + ": " + data.breakout[s][t].join(", ") + "\n"; });
      hasBrk = true;
    }
  });
  if (hasBrk) finalMsg += "🔥 전고점(20일) 돌파 현황이다\n--------------------\n" + brkMsg + "\n\n";

  var bbMsg = "";
  var hasBB = false;
  sectorOrder.forEach(s => {
    if (data.bollinger[s]) {
      bbMsg += "\n[" + s + "]\n";
      Object.keys(data.bollinger[s]).forEach(t => { bbMsg += "• " + t + ": " + data.bollinger[s][t].join(", ") + "\n"; });
      hasBB = true;
    }
  });
  if (hasBB) finalMsg += "📊 볼린저 이탈 실시간 현황 (1H 주기로 업데이트)\n--------------------\n" + bbMsg;

  if (finalMsg.trim() !== "") {
    sendTelegramMessage(MY_GROUP_ID, finalMsg.trim(), false);
  } else if (isForced) {
    sendTelegramMessage(MY_GROUP_ID, "✅ 현재 감지된 새로운 돌파/이탈/폭발 신호가 없다이다.", false);
  }
}

// --- 분석 로직 및 유틸리티이다 ---

function analyzeVolumeBurst(symbol, name, category, result, reportData, isForced) {
  var q = result.indicators.quote[0];
  var v = (q.volume || []).filter(x => x !== null), c = (q.close || []).filter(x => x !== null), o = (q.open || []).filter(x => x !== null);
  if (v.length < 40) return;
  var idx = v.length - 1, avgV = v.slice(idx - 31, idx).reduce((a, b) => a + b, 0) / 30;
  var ratio = v[idx] / avgV, pChange = ((c[idx] - o[idx]) / o[idx]) * 100;
  if (ratio >= 3.0 && pChange >= 0.5 && checkCooldown("VOL_UP_" + symbol, isForced)) addToReport(reportData.volumeBurst, category, name, "🔥 거래량 " + ratio.toFixed(1) + "배 폭발! 급등");
}

function analyzeDaily(symbol, name, category, result, reportData, isForced) {
  var q = result.indicators.quote[0], h = (q.high || []).filter(x => x !== null), c = getSafeCloses(result.indicators);
  if (c.length < 21 || h.length < 21) return;
  var cp = c[c.length - 1], pp = c[c.length - 2], maxH = Math.max.apply(null, h.slice(-21, -1));
  if (cp > maxH && (isForced || pp <= maxH) && checkCooldown("BRK_" + symbol, isForced)) addToReport(reportData.breakout, category, name, "🚀 20일 전고점 돌파");
  var bb = calculateBB_Breakout(c, 20, 2);
  if (cp > bb.upper && checkCooldown("BBD_UP_" + symbol, isForced)) addToReport(reportData.bollinger, category, name, "🚩 일봉 상단 돌파");
  if (cp < bb.lower && checkCooldown("BBD_DN_" + symbol, isForced)) addToReport(reportData.bollinger, category, name, "⚠️ 일봉 하단 이탈");
}

function analyzeHourly(symbol, name, category, result, reportData, isForced) {
  var c = getSafeCloses(result.indicators);
  if (c.length < 21) return;
  var cp = c[c.length - 1], bb1h = calculateBB_Breakout(c, 20, 2);
  if (cp > bb1h.upper && checkCooldown("BBH_UP_" + symbol, isForced)) addToReport(reportData.bollinger, category, name, "🔴 1H 상단 이탈");
  if (cp < bb1h.lower && checkCooldown("BBH_DN_" + symbol, isForced)) addToReport(reportData.bollinger, category, name, "🔵 1H 하단 이탈");
  var c4h = [];
  for (var j = c.length - 1; j >= 0; j -= 4) { c4h.unshift(c[j]); if (c4h.length >= 21) break; }
  if (c4h.length >= 20) {
    var bb4h = calculateBB_Breakout(c4h, 20, 2);
    if (cp > bb4h.upper && checkCooldown("BB4H_UP_" + symbol, isForced)) addToReport(reportData.bollinger, category, name, "🔥 4H 상단 돌파");
    if (cp < bb4h.lower && checkCooldown("BB4H_DN_" + symbol, isForced)) addToReport(reportData.bollinger, category, name, "🌊 4H 하단 이탈");
  }
}

function getTickerMap() {
  return { 'NVDA': '엔비디아', 'TSLA': '테슬라', 'AAPL': '애플', 'MSFT': '마이크로소프트', 'AMZN': '아마존', 'META': '메타', 'GOOGL': '구글', 'PLTR': '팔란티어', 'TQQQ': 'TQQQ', 'SOXL': 'SOXL', 'AMD': 'AMD', 'TSM': 'TSMC', 'MU': '마이크론', 'MSTR': 'MSTR', 'COIN': '코인베이스', 'ASML': 'ASML', 'MRVL': '마벨', 'PANW': '팔로알토', 'APP': '앱러빈' };
}

function getCategory(s) {
  var semi = ['NVDA', 'AMD', 'TSM', 'ASML', 'AVGO', 'MU', 'MRVL', 'SOXL'];
  var aiTech = ['MSFT', 'GOOGL', 'AMZN', 'META', 'PLTR', 'PANW', 'APP'];
  var energy = ['CEG', 'VST', 'GEV', 'XOM', 'CVX', 'ENPH'];
  if (semi.indexOf(s) !== -1) return "💠 반도체 및 장비 섹터";
  if (aiTech.indexOf(s) !== -1) return "🤖 AI 및 소프트웨어 섹터";
  if (energy.indexOf(s) !== -1) return "⚡ 에너지 및 전력 인프라";
  return "📈 지수 및 기타 주요 종목";
}

function getSafeCloses(indicators) {
  var raw = [];
  if (indicators && indicators.adjclose && indicators.adjclose[0].adjclose) raw = indicators.adjclose[0].adjclose;
  else if (indicators && indicators.quote && indicators.quote[0].close) raw = indicators.quote[0].close;
  return raw.filter(function(val) { return val !== null; });
}

function calculateBB_Breakout(c, p, s) {
  var sl = c.slice(-p), ma = sl.reduce((a, b) => a + b, 0) / p;
  var sd = Math.sqrt(sl.reduce((a, b) => a + Math.pow(b - ma, 2), 0) / p);
  return { upper: ma + (s * sd), lower: ma - (s * sd) };
}

function checkCooldown(key, forced) {
  if (forced) return true;
  var p = PropertiesService.getScriptProperties();
  var k = key + "_" + Utilities.formatDate(new Date(), "GMT+9", "yyyyMMdd");
  if (p.getProperty(k)) return false;
  p.setProperty(k, "S"); return true;
}

function addToReport(obj, cat, tick, sig) {
  if (!obj[cat]) obj[cat] = {};
  if (!obj[cat][tick]) obj[cat][tick] = [];
  obj[cat][tick].push(sig);
}

function getFetchOptions() {
  return { "muteHttpExceptions": true, "headers": { "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" } };
}

function getNaverRealtimePrice(symbol) {
  var url = "https://polling.finance.naver.com/api/realtime/global/stock/" + symbol;
  try {
    var response = UrlFetchApp.fetch(url, { "muteHttpExceptions": true });
    var data = JSON.parse(response.getContentText());
    if (data && data.datas && data.datas.length > 0) {
      return parseFloat(data.datas[0].now);
    }
  } catch (e) {
    Logger.log(symbol + " 네이버 가격 조회 실패다이다.");
  }
  return null;
}
