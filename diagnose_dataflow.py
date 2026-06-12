"""METIS-F2 데이터 흐름 진단.

main.py 한 사이클의 모든 데이터를 직접 흘려보면서:
1. data_fetcher → ai_input 구조
2. indicators_1h 키/값
3. tf_4h 키/값
4. regime_engine 입력/출력
5. signal_engine 입력/출력
6. AI 필터 입력 데이터 (실제 prompt 데이터)
의 *모든 키-값* 출력. 데이터 mismatch 추적용.
"""
import json
import sys
from pprint import pformat

from config import TRADING
from core import data_fetcher
from core.regime_engine import determine_regime, generate_signal, SignalType


def safe_json(obj, max_depth=3, depth=0):
    """JSON 직렬화 안전화 (max_depth)"""
    if depth >= max_depth:
        return str(type(obj).__name__)
    if isinstance(obj, dict):
        return {k: safe_json(v, max_depth, depth + 1) for k, v in obj.items()}
    if isinstance(obj, list):
        if len(obj) > 5:
            return [safe_json(v, max_depth, depth + 1) for v in obj[:3]] + [f"... ({len(obj)} items)"]
        return [safe_json(v, max_depth, depth + 1) for v in obj]
    if isinstance(obj, (int, float, str, bool, type(None))):
        return obj
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    return str(type(obj).__name__)


def main():
    print("=" * 80)
    print("STEP 1: data_fetcher.collect_all_data()")
    print("=" * 80)

    data = data_fetcher.collect_all_data()
    ai_input = data_fetcher.prepare_ai_input(data)

    print("\n=== ai_input top-level keys ===")
    for k in ai_input.keys():
        v = ai_input[k]
        if isinstance(v, dict):
            sub_keys = list(v.keys())[:8]
            print(f"  {k}: dict with keys {sub_keys}{'...' if len(v) > 8 else ''}")
        elif isinstance(v, (str, int, float)):
            print(f"  {k}: {v}")
        else:
            print(f"  {k}: {type(v).__name__}")

    print("\n" + "=" * 80)
    print("STEP 2: indicators 구조 검사")
    print("=" * 80)

    indicators = ai_input.get("indicators", {})
    print(f"\nai_input['indicators'] 직접 사용 키 수: {len(indicators)}")
    print(f"키 목록: {list(indicators.keys())}")

    print(f"\n주요 값:")
    print(f"  rsi: {indicators.get('rsi')}")
    print(f"  adx: {indicators.get('adx')}")
    print(f"  plus_di: {indicators.get('plus_di')}")
    print(f"  minus_di: {indicators.get('minus_di')}")

    bb = indicators.get('bollinger', {})
    print(f"  bollinger.width: {bb.get('width') if bb else 'N/A'}")
    atr = indicators.get('atr', {})
    print(f"  atr.percentage: {atr.get('percentage') if atr else 'N/A'}")
    macd = indicators.get('macd', {})
    print(f"  macd.histogram: {macd.get('histogram') if macd else 'N/A'}")

    # main.py가 잘못 읽던 path
    print(f"\n[비교] main.py가 이전에 사용하던 잘못된 path:")
    print(f"  ai_input['indicators'].get('current', {{}}) → keys: {list(ai_input.get('indicators', {}).get('current', {}).keys())}")

    print("\n" + "=" * 80)
    print("STEP 3: multi_timeframe (4H) 구조")
    print("=" * 80)

    mtf = ai_input.get("multi_timeframe", {})
    print(f"\nmulti_timeframe top-level keys: {list(mtf.keys())}")
    tf_4h = mtf.get("4h", {})
    print(f"\n4H 키 목록: {list(tf_4h.keys())}")
    print(f"4H 주요 값:")
    print(f"  close: {tf_4h.get('close')}")
    print(f"  rsi: {tf_4h.get('rsi')}")
    print(f"  adx: {tf_4h.get('adx')}")
    print(f"  ema_20_50_bullish: {tf_4h.get('ema_20_50_bullish')}")
    print(f"  macd_direction: {tf_4h.get('macd_direction')}")
    print(f"  price_vs_ema20: {tf_4h.get('price_vs_ema20')}")
    print(f"  ATR%: {tf_4h.get('atr_pct')}")

    print(f"\n[비교] main.py 이전 path 'timeframe_4h':")
    print(f"  ai_input.get('timeframe_4h', {{}}) → {ai_input.get('timeframe_4h', '키 없음')}")

    print("\n" + "=" * 80)
    print("STEP 4: trend_analysis 구조")
    print("=" * 80)
    trend = ai_input.get("trend_analysis", {})
    print(f"trend_analysis 키: {list(trend.keys())}")
    for k, v in list(trend.items())[:8]:
        print(f"  {k}: {v}")

    print("\n" + "=" * 80)
    print("STEP 5: futures (선물 데이터) 구조")
    print("=" * 80)
    futures = ai_input.get("futures", {})
    for k, v in futures.items():
        print(f"  {k}: {v}")

    print("\n" + "=" * 80)
    print("STEP 6: regime_engine.determine_regime() 호출")
    print("=" * 80)

    regime = determine_regime(indicators, tf_4h)
    print(f"\nregime: {regime.regime.value}")
    print(f"confidence: {regime.confidence}")
    print(f"details: {json.dumps(regime.details, ensure_ascii=False, indent=2, default=str)}")

    print("\n" + "=" * 80)
    print("STEP 7: signal_engine.generate_signal() 호출")
    print("=" * 80)

    signal = generate_signal(regime, indicators)
    print(f"\nsignal: {signal.signal.value}")
    print(f"score: {signal.score}")
    print(f"reason: {signal.reason}")
    print(f"leverage: {signal.leverage}")
    print(f"stop_loss_pct: {signal.stop_loss_pct}")
    print(f"take_profit_pct: {signal.take_profit_pct}")

    print("\n" + "=" * 80)
    print("STEP 8: AI 프롬프트에 들어갈 market_data (직렬화 후)")
    print("=" * 80)
    # 그대로 ai_input이 prompt에 들어감
    print(f"\nmarket_data 사이즈: {len(json.dumps(ai_input, ensure_ascii=False, default=str))} chars")
    print(f"\n전체 구조 (depth 3):")
    print(json.dumps(safe_json(ai_input, max_depth=3), ensure_ascii=False, indent=2, default=str)[:4000])


if __name__ == "__main__":
    main()
