"""METIS-F2 멀티 심볼 데이터 흐름 진단.

BTC + XRP 둘 다 진짜 데이터로 흘러가는지 검증.
- ADX, RSI 등 지표가 0/50 default 값이 아닌지
- MTF (1D + 4H + 15m) 모든 심볼에 정상 들어오는지
- regime + signal 결정이 코드 default 아닌지
"""
import json
from config import TRADING
from core import data_fetcher
from core.regime_engine import determine_regime, generate_signal


def check_symbol(symbol: str):
    print(f"\n{'='*80}")
    print(f"심볼: {symbol}")
    print('='*80)

    data = data_fetcher.collect_all_data(symbol=symbol)
    ai_input = data_fetcher.prepare_ai_input(data)

    # 1. 가격 / 지표
    futures = ai_input.get("futures", {})
    indicators = ai_input.get("indicators", {})
    print(f"\n[가격] {futures.get('last_price', 0):.4f}")
    print(f"[1H 지표] RSI={indicators.get('rsi', 0):.2f} ADX={indicators.get('adx', 0):.2f} "
          f"+DI={indicators.get('plus_di', 0):.2f} -DI={indicators.get('minus_di', 0):.2f}")
    macd = indicators.get('macd', {})
    print(f"[MACD] hist={macd.get('histogram', 0):.4f} line={macd.get('macd', 0):.4f} signal={macd.get('signal', 0):.4f}")
    bb = indicators.get('bollinger', {})
    print(f"[BB] width={bb.get('width', 0):.2f} upper={bb.get('upper', 0):.2f} lower={bb.get('lower', 0):.2f}")
    atr = indicators.get('atr', {})
    print(f"[ATR] {atr.get('percentage', 0):.3f}%")

    # 2. MTF
    mtf = ai_input.get("multi_timeframe", {})
    print(f"\n[MTF 키] {list(mtf.keys())}")
    for tf in ['1d', '4h', '15m']:
        d = mtf.get(tf, {})
        if d:
            print(f"  {tf}: RSI={d.get('rsi', 0):.1f} ADX={d.get('adx', 0):.1f} "
                  f"ema_bullish={d.get('ema_20_50_bullish')} price_vs_ema20={d.get('price_vs_ema20')}")
        else:
            print(f"  {tf}: 누락 ❌")

    # 3. price_levels (S/R)
    pl = indicators.get('price_levels', {})
    print(f"\n[Levels] 24h H/L: {pl.get('high_24h')}/{pl.get('low_24h')} "
          f"3d H/L: {pl.get('high_3d')}/{pl.get('low_3d')}  "
          f"24h pos%: {pl.get('position_in_24h_range_pct')}")

    # 4. trend_analysis
    trend = ai_input.get('trend_analysis', {})
    print(f"\n[Trend] {trend.get('trend')} strength={trend.get('strength')}")

    # 5. regime + signal
    regime = determine_regime(indicators, mtf.get("4h", {}))
    print(f"\n[Regime] {regime.regime.value} 확신도={regime.confidence}")
    print(f"  근거: {regime.details.get('reason')}")

    signal = generate_signal(regime, indicators)
    print(f"[Signal] {signal.signal.value} score={signal.score}")
    print(f"  근거: {signal.reason}")

    # 6. 이상치 검사
    issues = []
    if indicators.get('adx', 0) == 0:
        issues.append("⚠️ ADX=0 (default일 수도)")
    if indicators.get('rsi', 50) == 50.0:
        issues.append("⚠️ RSI=50 (default일 수도)")
    if not mtf.get('1d'):
        issues.append("❌ 1D 데이터 누락")
    if not mtf.get('4h'):
        issues.append("❌ 4H 데이터 누락")
    if futures.get('last_price', 0) == 0:
        issues.append("❌ 가격 0")

    if issues:
        print(f"\n🚨 이슈: {issues}")
    else:
        print(f"\n✅ {symbol} 데이터 정상 (실제 시장 데이터)")


def main():
    print("METIS-F2 멀티 심볼 데이터 흐름 진단")
    print(f"SYMBOLS = {TRADING.SYMBOLS}")
    print(f"SYMBOL_SPECS = {TRADING.SYMBOL_SPECS}")

    for symbol in TRADING.SYMBOLS:
        try:
            check_symbol(symbol)
        except Exception as e:
            print(f"\n❌ {symbol} 검증 실패: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()
