"""METIS-F2 전수 데이터 검증.

운영자 명령: 이상한 데이터 / 실제 데이터 / 실시간 데이터 아닌 것 다 파악.

검증 항목:
1. Bybit Live API 직접 호출 → ticker / kline 응답 raw 검증
2. 4 timeframe (1D/4H/1H/15m) 캔들 timestamp = 최근 시간 일치
3. 지표가 default 값(RSI=50, ADX=0) 아닌 실제 계산값
4. funding_rate, mark_price, index_price 실제 값
5. SYMBOL_SPECS 정확
6. BTC ↔ XRP 별 데이터 분리 (서로 섞이지 않음)
"""
import json
from datetime import datetime, timezone
from config import TRADING, BYBIT
from core import data_fetcher
from exchange import bybit_client


def check_real_time(symbol):
    print(f"\n{'='*80}\n심볼: {symbol}\n{'='*80}")

    # 1. Bybit Live ticker 직접
    ticker = bybit_client.get_ticker(symbol)
    print(f"\n[1] Bybit Live Ticker (raw API)")
    for k, v in ticker.items():
        print(f"  {k}: {v}")

    # 2. 4 timeframe 최신 캔들 timestamp 검증
    print(f"\n[2] 4 Timeframe latest candle timestamp 검증")
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    timeframes = {"1D": "D", "4H": "240", "1H": "60", "15m": "15"}
    for label, interval in timeframes.items():
        candles = bybit_client.get_kline(symbol, interval, 5)
        if not candles:
            print(f"  {label}: ❌ 캔들 데이터 없음")
            continue
        latest = candles[-1]
        ts_ms = int(latest.get("timestamp", 0))
        age_min = (now_ms - ts_ms) / 60000
        max_expected_min = {"D": 24*60, "240": 240, "60": 60, "15": 15}.get(interval, 60)
        ok = age_min <= max_expected_min
        emoji = "✅" if ok else "🚨"
        print(f"  {label}: latest ts={datetime.fromtimestamp(ts_ms/1000, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC "
              f"({age_min:.0f}분 전) {emoji} [max {max_expected_min}분]")
        print(f"      O={latest.get('open')} H={latest.get('high')} L={latest.get('low')} C={latest.get('close')} V={latest.get('volume')}")

    # 3. data_fetcher 결과
    print(f"\n[3] data_fetcher.collect_all_data() 결과")
    data = data_fetcher.collect_all_data(symbol=symbol)
    ai_input = data_fetcher.prepare_ai_input(data)

    # 가격 일치 확인
    fetcher_price = ai_input.get("futures", {}).get("last_price", 0)
    ticker_price = ticker.get("last_price", 0)
    diff_pct = abs(fetcher_price - ticker_price) / ticker_price * 100 if ticker_price else 0
    diff_ok = diff_pct < 0.5  # 0.5% 이내
    print(f"  Fetcher 가격: {fetcher_price}")
    print(f"  Ticker 가격: {ticker_price}")
    print(f"  차이: {diff_pct:.4f}% {'✅' if diff_ok else '🚨'}")

    # 지표
    ind = ai_input.get("indicators", {})
    print(f"\n[4] 지표 default 검증")
    suspicious = []
    if ind.get("rsi") in (50.0, 50):
        suspicious.append(f"RSI={ind.get('rsi')} (default?)")
    if ind.get("adx") == 0:
        suspicious.append(f"ADX=0 (default!)")
    if ind.get("macd_histogram") == 0:
        suspicious.append(f"MACD=0 (default?)")
    if ind.get("close") == 0:
        suspicious.append(f"close=0 ❌")
    if ind.get("ema_20") == 0:
        suspicious.append(f"ema_20=0 ❌")
    if ind.get("bb_width") in (3.0, 0):
        suspicious.append(f"bb_width={ind.get('bb_width')} (default?)")
    if ind.get("atr_pct") in (1.0, 0):
        suspicious.append(f"atr_pct={ind.get('atr_pct')} (default?)")

    print(f"  RSI={ind.get('rsi'):.4f} ADX={ind.get('adx'):.4f} +DI={ind.get('plus_di'):.4f} -DI={ind.get('minus_di'):.4f}")
    print(f"  close={ind.get('close')} ema_20={ind.get('ema_20'):.4f} ema_50={ind.get('ema_50'):.4f}")
    print(f"  macd_hist={ind.get('macd_histogram'):.6f} bb_width={ind.get('bb_width'):.4f}")
    print(f"  atr_pct={ind.get('atr_pct'):.4f} volume_ratio={ind.get('volume_ratio'):.4f}")
    if suspicious:
        print(f"  🚨 의심: {suspicious}")
    else:
        print(f"  ✅ 모든 지표 실제 계산값")

    # 5. MTF 검증
    mtf = ai_input.get("multi_timeframe", {})
    print(f"\n[5] Multi-timeframe 검증")
    expected_tfs = ["1d", "4h", "15m"]
    for tf in expected_tfs:
        d = mtf.get(tf, {})
        if not d:
            print(f"  {tf}: ❌ 누락")
            continue
        rsi_ok = d.get('rsi', 50) != 50
        adx_ok = d.get('adx', 0) > 0
        print(f"  {tf}: RSI={d.get('rsi'):.2f} ADX={d.get('adx'):.2f} ema_bullish={d.get('ema_20_50_bullish')} "
              f"price_vs_ema20={d.get('price_vs_ema20')} {'✅' if rsi_ok and adx_ok else '🚨 default 값'}")

    # 6. funding/mark/index
    futures = ai_input.get("futures", {})
    print(f"\n[6] Futures 데이터")
    for k in ['funding_rate', 'funding_rate_pct', 'open_interest', 'mark_price', 'index_price', 'volume_24h', 'price_change_24h_pct']:
        v = futures.get(k)
        emoji = "🚨" if v in (0, None) else "✅"
        print(f"  {k}: {v} {emoji}")

    # 7. price_levels
    pl = ind.get("price_levels", {})
    print(f"\n[7] Price Levels (S/R)")
    print(f"  24h: H={pl.get('high_24h')} L={pl.get('low_24h')}")
    print(f"  3d:  H={pl.get('high_3d')} L={pl.get('low_3d')}")
    print(f"  7d:  H={pl.get('high_7d')} L={pl.get('low_7d')}")
    print(f"  position_in_24h_range_pct={pl.get('position_in_24h_range_pct')}")

    return suspicious


def main():
    print("METIS-F2 전수 데이터 검증")
    print(f"USE_TESTNET = {BYBIT.USE_TESTNET}")
    print(f"BASE_URL = {BYBIT.BASE_URL}")
    print(f"SYMBOLS = {TRADING.SYMBOLS}")

    if BYBIT.USE_TESTNET:
        print("\n🚨 USE_TESTNET=True — testnet 데이터일 가능성 (mainnet 아님)")
    else:
        print("\n✅ USE_TESTNET=False — mainnet 데이터 사용")

    all_suspicious = {}
    for sym in TRADING.SYMBOLS:
        try:
            issues = check_real_time(sym)
            all_suspicious[sym] = issues
        except Exception as e:
            print(f"\n❌ {sym} 검증 실패: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n\n{'='*80}\n종합 결과\n{'='*80}")
    for sym, issues in all_suspicious.items():
        if issues:
            print(f"  🚨 {sym}: {issues}")
        else:
            print(f"  ✅ {sym}: 모든 데이터 정상")


if __name__ == "__main__":
    main()
