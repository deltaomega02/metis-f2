"""METIS-F2 Testnet 정리 스크립트.

가동 전 1회 실행. testnet의 기존 활성 포지션을 모두 청산하고
잔고/포지션 상태를 출력. 실거래(MAINNET) 환경에서는 거부.

사용:
    python3 cleanup_testnet.py

위험 안전장치:
- BYBIT_USE_TESTNET이 true가 아니면 즉시 거부
- 청산 직전 사용자 확인 (CONFIRM 입력)
"""

import sys
from config import BYBIT, TRADING, get_logger
from exchange import bybit_client

logger = get_logger("cleanup")


def main():
    print("=" * 60)
    print("METIS-F2 Testnet 정리 스크립트")
    print("=" * 60)
    print()

    # 안전장치: testnet 모드 강제
    if not BYBIT.USE_TESTNET:
        print("❌ BYBIT_USE_TESTNET=true 아닙니다. 실거래 환경에서는 실행 거부.")
        print("   .env 파일에서 BYBIT_USE_TESTNET=true 로 변경 후 재실행.")
        sys.exit(1)

    print(f"환경: TESTNET ({BYBIT.BASE_URL})")
    print(f"심볼: {TRADING.SYMBOL}")
    print()

    # 1. 잔고 조회
    print("--- 1. 잔고 조회 ---")
    try:
        balance_info = bybit_client.get_wallet_balance()
        print(f"  USDT 잔고 (전체): {balance_info.get('total_balance', 0):.4f}")
        print(f"  USDT 가용: {balance_info.get('available_balance', 0):.4f}")
        print(f"  미실현 PnL: {balance_info.get('unrealized_pnl', 0):+.4f}")
    except Exception as e:
        print(f"  잔고 조회 실패: {e}")

    print()

    # 2. 활성 포지션 조회
    print("--- 2. 활성 포지션 조회 ---")
    try:
        position = bybit_client.get_position(TRADING.SYMBOL)
        if not position or position.get("size", 0) == 0:
            print(f"  {TRADING.SYMBOL}: 활성 포지션 없음 ✓")
            print()
            print("정리 완료 (포지션 없음). METIS-F2 가동 가능.")
            sys.exit(0)
        print(f"  {TRADING.SYMBOL}: {position.get('side')} size={position.get('size')} "
              f"entry={position.get('entry_price')} "
              f"unrealized_pnl={position.get('unrealized_pnl', 0):+.4f}")
    except Exception as e:
        print(f"  포지션 조회 실패: {e}")
        sys.exit(1)

    print()
    print("--- 3. 사용자 확인 ---")
    auto = "--auto" in sys.argv
    if auto:
        print("⚠️  --auto 모드: 위 활성 포지션을 시장가로 즉시 청산합니다.")
    else:
        print("⚠️  위 활성 포지션을 시장가로 즉시 청산합니다.")
        answer = input("진행하려면 'CONFIRM' 입력: ").strip()
        if answer != "CONFIRM":
            print("취소됨.")
            sys.exit(0)

    print()
    print("--- 4. 포지션 청산 ---")
    try:
        side = position.get("side")
        direction = "LONG" if side == "Buy" else "SHORT"
        result = bybit_client.close_position(TRADING.SYMBOL, direction)
        print(f"  청산 주문 결과: {result}")
    except Exception as e:
        print(f"  청산 실패: {e}")
        sys.exit(1)

    print()
    print("--- 5. 청산 후 상태 ---")
    import time
    time.sleep(2)
    try:
        position = bybit_client.get_position(TRADING.SYMBOL)
        if not position or position.get("size", 0) == 0:
            print(f"  {TRADING.SYMBOL}: 청산 완료 ✓")
        else:
            print(f"  {TRADING.SYMBOL}: 잔여 포지션 {position}")

        balance_info = bybit_client.get_wallet_balance()
        print(f"  잔고: {balance_info.get('available_balance', 0):.4f} USDT")
    except Exception as e:
        print(f"  최종 확인 실패: {e}")

    print()
    print("정리 완료. METIS-F2 가동 가능.")


if __name__ == "__main__":
    main()
