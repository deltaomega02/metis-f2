"""
SL/TP 데이터 흐름 전수조사

추적 경로:
1. DB raw query (futures_positions WHERE status=ACTIVE)
2. db_manager.get_active_position() 함수 호출
3. position_manager.get_current_position() 함수 호출
4. Bybit API /v5/position/list 원시 응답 (stopLoss / takeProfit 필드)
5. cycle log 최근 recheck의 prompt position_info와 비교

실행 위치: ~/metis-f2/
실행: ./venv/bin/python diagnose_sltp.py
"""
import os
import sys
import json
import sqlite3
import hmac
import hashlib
import time
import requests
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))


def section(title):
    print()
    print("=" * 70)
    print(f"  {title}")
    print("=" * 70)


def main():
    db_path = ROOT / "database" / "metis_f2.db"

    # ─────────────────────────────────────────────────────────────
    section("1. DB raw query — futures_positions WHERE status=ACTIVE")
    # ─────────────────────────────────────────────────────────────
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    cur = db.cursor()
    rows = cur.execute(
        "SELECT * FROM futures_positions WHERE status='ACTIVE'"
    ).fetchall()
    print(f"ACTIVE row count: {len(rows)}")
    active_uuid = None
    for r in rows:
        d = dict(r)
        active_uuid = d["position_uuid"]
        print(f"  uuid: {d['position_uuid'][:8]}...")
        print(f"  symbol: {d['symbol']}  direction: {d['direction']}  leverage: {d['leverage']}x")
        print(f"  entry_price: {d['entry_price']}")
        print(f"  stop_loss_price (DB col): {d['stop_loss_price']}")
        print(f"  take_profit_price (DB col): {d['take_profit_price']}")
        print(f"  status: {d['status']}")

    # ─────────────────────────────────────────────────────────────
    section("2. db_manager.get_active_position() 호출")
    # ─────────────────────────────────────────────────────────────
    from database.db_manager import db_manager
    db_pos = db_manager.get_active_position()
    if db_pos is None:
        print("  None 반환")
    else:
        print(f"  type: {type(db_pos).__name__}")
        print(f"  keys: {list(db_pos.keys())}")
        print(f"  stop_loss_price: {db_pos.get('stop_loss_price')}")
        print(f"  take_profit_price: {db_pos.get('take_profit_price')}")
        print(f"  entry_price: {db_pos.get('entry_price')}")

    # ─────────────────────────────────────────────────────────────
    section("3. position_manager.get_current_position() 호출")
    # ─────────────────────────────────────────────────────────────
    from core.position_manager import position_manager
    pos = position_manager.get_current_position()
    if pos is None:
        print("  None 반환")
    else:
        print(f"  type: {type(pos).__name__}")
        print(f"  keys: {list(pos.keys())}")
        print(f"  symbol: {pos.get('symbol')}")
        print(f"  direction: {pos.get('direction')}")
        print(f"  entry_price: {pos.get('entry_price')}")
        print(f"  stop_loss: {pos.get('stop_loss')}  ← prompt에 들어감")
        print(f"  take_profit: {pos.get('take_profit')}  ← prompt에 들어감")
        print(f"  mark_price: {pos.get('mark_price')}")
        print(f"  liquidation_price: {pos.get('liquidation_price')}")

    # ─────────────────────────────────────────────────────────────
    section("4. Bybit /v5/position/list 원시 응답 (stopLoss/takeProfit 필드)")
    # ─────────────────────────────────────────────────────────────
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    ak = os.getenv("BYBIT_API_KEY")
    sk = os.getenv("BYBIT_SECRET")
    ts = str(int(time.time() * 1000))
    qs = "category=linear&settleCoin=USDT"
    sig = hmac.new(sk.encode(), (ts + ak + "5000" + qs).encode(), hashlib.sha256).hexdigest()
    h = {
        "X-BAPI-API-KEY": ak,
        "X-BAPI-TIMESTAMP": ts,
        "X-BAPI-SIGN": sig,
        "X-BAPI-RECV-WINDOW": "5000",
    }
    r = requests.get(f"https://api.bybit.com/v5/position/list?{qs}", headers=h).json()
    for p in r.get("result", {}).get("list", []):
        if float(p.get("size", 0)) <= 0:
            continue
        print(f"  symbol: {p.get('symbol')}  side: {p.get('side')}")
        print(f"  avgPrice: {p.get('avgPrice')}")
        print(f"  stopLoss: {p.get('stopLoss')}  ← Bybit 실제 SL")
        print(f"  takeProfit: {p.get('takeProfit')}  ← Bybit 실제 TP")
        print(f"  trailingStop: {p.get('trailingStop')}")
        print(f"  size: {p.get('size')}")

    # ─────────────────────────────────────────────────────────────
    section("5. 최근 cycle log recheck input position_info")
    # ─────────────────────────────────────────────────────────────
    import glob
    files = sorted(
        glob.glob(str(ROOT / "logs/analysis/2026-05-08/*recheck*.json"))
    )[-3:]
    for f in files:
        d = json.load(open(f))
        rin = d.get("phases", {}).get("recheck_input", {})
        pi = rin.get("position_info", {})
        print(f"  {Path(f).name}")
        print(f"    SL={pi.get('stop_loss')} TP={pi.get('take_profit')} entry={pi.get('entry_price')}")

    # ─────────────────────────────────────────────────────────────
    section("6. 진단 결론")
    # ─────────────────────────────────────────────────────────────
    db_sl = rows[0]["stop_loss_price"] if rows else None
    db_tp = rows[0]["take_profit_price"] if rows else None
    pm_sl = pos.get("stop_loss") if pos else None
    pm_tp = pos.get("take_profit") if pos else None

    print(f"  DB raw       SL={db_sl} TP={db_tp}")
    print(f"  position_mgr SL={pm_sl} TP={pm_tp}")
    print()
    if db_sl == pm_sl and db_tp == pm_tp:
        print("  ✅ DB → position_manager 일치")
    else:
        print("  ❌ DB → position_manager 불일치 (여기서 버그)")
    print()

    # cycle log와 비교
    if files:
        last_log = json.load(open(files[-1]))
        log_pi = last_log.get("phases", {}).get("recheck_input", {}).get("position_info", {})
        log_sl = log_pi.get("stop_loss")
        log_tp = log_pi.get("take_profit")
        print(f"  최근 cycle log SL={log_sl} TP={log_tp}")
        if log_sl == pm_sl and log_tp == pm_tp:
            print("  ✅ position_manager → cycle log 일치 (현재값 기준)")
        else:
            print(f"  ⚠️ cycle log는 과거 시점 prompt 값 — 지금과 다른 건 정상일 수도 있음")

    db.close()


if __name__ == "__main__":
    main()
