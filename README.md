# METIS-F (Major-asset Estimation Trend Intelligence System - Futures)

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white) ![Google Gemini](https://img.shields.io/badge/Google_Gemini-8E75B2?style=for-the-badge&logo=googlegemini&logoColor=white)

AI 기반 비트코인 선물 자동매매 시스템. [metis-f](https://github.com/deltaomega02/metis-f)의 운영 개선판 — 멀티 심볼 진단 도구(diagnose_*.py)와 데이터 흐름 점검 스크립트가 추가되어 있다.

---

## 목차

1. [프로젝트 개요](#1-프로젝트-개요)
2. [시스템 아키텍처](#2-시스템-아키텍처)
3. [Phase별 상세 동작](#3-phase별-상세-동작)
4. [기술적 지표 및 분석](#4-기술적-지표-및-분석)
5. [리스크 관리 체계](#5-리스크-관리-체계)
6. [WebSocket 및 실시간 모니터링](#6-websocket-및-실시간-모니터링)
7. [데이터베이스 구조](#7-데이터베이스-구조)
8. [알림 시스템](#8-알림-시스템)
9. [환경 변수](#9-환경-변수)
10. [프로젝트 구조](#10-프로젝트-구조)

---

## 1. 프로젝트 개요

### 1.1 소개

METIS-F2는 Google Gemini 3.1 Pro (`gemini-3.1-pro-preview`)을 활용하여 암호화폐 선물 시장(BTC·XRP)을 분석하고, 롱/숏 양방향 포지션을 자동으로 운용하는 트레이딩 시스템이다. GCP e2-small (2GB RAM) 환경에서 24시간 무중단 운영을 목표로 설계되었다.

### 1.2 핵심 특징

| 항목 | 설명 |
|------|------|
| 거래소 | Bybit (USDT Perpetual) |
| 거래 대상 | **BTC/USDT + XRP/USDT** (`config/settings.py:47`) |
| 거래 방향 | 롱(Long) / 숏(Short) 양방향 |
| 레버리지 | 1x ~ **7x** (AI 확신도 기반 동적 결정, `MAX_LEVERAGE = 7`) |
| AI 엔진 | Google Gemini 3.1 Pro (`gemini-3.1-pro-preview`) |
| 분석 주기 | 1시간 타임프레임 기준 |
| 실시간 감시 | WebSocket + Dead Man's Switch |

### 1.3 운영 철학

**멀티 심볼**: BTC 에 XRP 를 더해 두 심볼을 병렬 운용한다. f2 가 존재하는 이유가 이것이고, 함께 들어온 진단 도구(`diagnose_*.py`)로 심볼별 데이터 흐름을 점검한다.

**Bidirectional Thinking**: 상승장과 하락장 모두 수익 기회로 활용

**Leverage-Aware Risk**: 레버리지에 따른 청산 리스크를 항상 인지하고 관리

**Strict Stop Loss**: 선물 거래에서 손절은 선택이 아닌 필수

---

## 2. 시스템 아키텍처

### 2.1 전체 구조

```
┌─────────────────────────────────────────────────────────────────┐
│                         METIS-F System                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│  │   Phase 1   │───▶│   Phase 2   │───▶│   Phase 3   │         │
│  │    Data     │    │  Direction  │    │  Strategy   │         │
│  │ Collection  │    │  Decision   │    │  Planning   │         │
│  └─────────────┘    └─────────────┘    └─────────────┘         │
│         │                                      │                │
│         │                                      ▼                │
│         │                              ┌─────────────┐         │
│         │                              │   Phase 4   │         │
│         │                              │  Execution  │         │
│         │                              │ & Monitoring│         │
│         │                              └─────────────┘         │
│         │                                      │                │
│         ▼                                      ▼                │
│  ┌─────────────────────────────────────────────────────┐       │
│  │                  External Services                   │       │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌────────┐ │       │
│  │  │  Bybit  │  │ Gemini  │  │Telegram │  │ SQLite │ │       │
│  │  │   API   │  │   AI    │  │   Bot   │  │   DB   │ │       │
│  │  └─────────┘  └─────────┘  └─────────┘  └────────┘ │       │
│  └─────────────────────────────────────────────────────┘       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 4단계 순환 구조

시스템은 4개의 Phase가 순환하며 동작한다:

1. **Phase 1 (Data Collection)**: 시장 데이터 수집 및 기술적 지표 계산
2. **Phase 2 (Direction Decision)**: AI가 롱/숏/관망 중 결정
3. **Phase 3 (Strategy Planning)**: 구체적인 진입 전략 수립
4. **Phase 4 (Execution & Monitoring)**: 포지션 실행 및 실시간 감시

---

## 3. Phase별 상세 동작

### 3.1 Phase 1: Data Collection

**역할**: 시장 데이터 수집, 기술적 지표 계산, 차트 이미지 생성

**데이터 소스**:
- Bybit REST API v5 (`/v5/market/kline`)
- 타임프레임: 1시간 (기본), 4시간, 15분 지원
- 캔들 수: 200개 (패턴 인식에 충분한 데이터량)

**수집 데이터**:

| 구분 | 항목 | 설명 |
|------|------|------|
| OHLCV | open, high, low, close, volume | 기본 캔들 데이터 |
| 선물 특화 | funding_rate | 펀딩비율 (8시간마다 정산) |
| 선물 특화 | open_interest | 미결제약정 |
| 선물 특화 | mark_price | 마크 가격 |
| 선물 특화 | index_price | 인덱스 가격 |

**계산되는 기술적 지표**:
- EMA (20, 50, 120, 200)
- RSI (14)
- MACD (12, 26, 9)
- Bollinger Bands (20, 2)
- ATR (14)
- ADX (14)

**차트 생성**:
- 캔들스틱 차트 + 볼륨 차트
- EMA 오버레이
- 볼린저 밴드 표시
- PNG 포맷, 메모리 버퍼 반환
- 해상도: 10x6 인치, DPI 100 (메모리 최적화)

**출력**: JSON 데이터 패키지 + 차트 이미지 바이트

---

### 3.2 Phase 2: Direction Decision

**역할**: AI가 시장 상황을 분석하여 거래 방향 결정

**입력**:
- Phase 1에서 생성된 JSON 데이터
- 캔들스틱 차트 이미지 (Vision 분석용)

**AI 분석 관점**:

1. **Market Regime 식별**
   - Trending (추세) vs Range-bound (박스권) 판단
   - ADX 25 이상이면 추세 추종 우선

2. **Confluence (신호 수렴) 확인**
   - 단일 지표가 아닌 복수 지표 일치 여부
   - EMA 배열, RSI 상태, MACD 방향 종합 판단

3. **Breakout vs Mean Reversion**
   - ADX > 25: 돌파 추종 전략
   - ADX < 20: 평균 회귀 전략 검토

**결정 유형**:

| 결정 | 조건 | 후속 액션 |
|------|------|----------|
| TRADE - LONG | 상승 신호 + 확신도 4점 이상 | Phase 3로 진행 |
| TRADE - SHORT | 하락 신호 + 확신도 4점 이상 | Phase 3로 진행 |
| WAIT | 방향성 불명확 또는 확신도 부족 | 대기 후 Phase 1 재실행 |

**확신도 스케일**: 1~10점 (정수)

**출력 예시**:
```json
{
  "decision": "TRADE",
  "direction": "LONG",
  "confidence_score": 7,
  "reason": "4시간봉 20 EMA 지지 확인, RSI 과매도 탈출...",
  "suggested_wait_hours": null
}
```

---

### 3.3 Phase 3: Strategy Planning

**역할**: 구체적인 거래 전략 수립 (레버리지, 손익절가, 포지션 사이즈)

**레버리지 결정 로직**:

| 확신도 | 레버리지 | 근거 |
|--------|----------|------|
| 9~10점 | 7x | 매우 강한 신호 |
| 7~8점 | 7x | 강한 신호 |
| 5~6점 | 5x | 중간 신호 |
| 3~4점 | 2x | 약한 신호 |
| 1~2점 | 진입 거부 | 불충분한 신호 |

**손절가 설정 원칙**:

1. **기술적 무효화 지점**: 매매 근거가 무효화되는 가격
2. **최소 거리 보장**: MAX(1.5 × ATR, 진입가 × 2.5%)
3. **청산가 마진**: 청산가보다 최소 2% 여유 확보

**익절가 설정 원칙**:

1. **기술적 목표가**: 다음 저항/지지선
2. **R:R 비율**: 최소 1:1.5 이상 확보
3. **수수료 감안**: 왕복 수수료 차감 후에도 수익 보장

**포지션 사이즈 계산**:

```
포지션 가치 = 가용 잔고 × 레버리지
주문 수량 = 포지션 가치 / 진입가
```

최소 주문 단위: 0.001 BTC

**청산가 계산** (Cross Margin 기준):

- 롱: `진입가 × (1 - 1/레버리지 + 0.004)`
- 숏: `진입가 × (1 + 1/레버리지 - 0.004)`

(0.004 = 유지마진율 0.4%)

**전략 검증 항목**:
- 손절가-청산가 마진 충분 여부
- R:R 비율 1.5 이상 여부
- 최소 주문 수량 충족 여부
- 잔고 충분 여부

---

### 3.4 Phase 4: Execution & Monitoring

**역할**: 포지션 진입 실행 및 실시간 감시

#### 3.4.1 포지션 진입

**실행 순서**:
1. 레버리지 설정 (`/v5/position/set-leverage`)
2. 시장가 주문 실행 (`/v5/order/create`)
3. 체결 확인 및 실제 진입가 조회
4. DB 기록 (포지션 UUID 생성)
5. WebSocket 감시 시작
6. 중간 점검 스케줄 등록

**체결 확인 프로세스**:
- 주문 후 1초 대기
- 최대 3회 재시도로 포지션/체결 내역 조회
- 실제 체결가, 수량, 수수료 확인

#### 3.4.2 실시간 감시

**감시 항목**:

| 조건 | 트리거 액션 |
|------|------------|
| 현재가 >= 익절가 (롱) | 시장가 청산 |
| 현재가 <= 손절가 (롱) | 시장가 청산 |
| 현재가 <= 익절가 (숏) | 시장가 청산 |
| 현재가 >= 손절가 (숏) | 시장가 청산 |
| 청산가 3% 이내 접근 | 긴급 알림 발송 |

**트레일링 스탑**:
- 활성화 조건: 수익률 2% 이상
- 추적 거리: 기준가 대비 1.5%
- API 호출 쿨다운: 30초

#### 3.4.3 중간 점검 (Recheck)

**실행 주기**: AI가 제안한 시간 (기본 1~2시간)

**점검 프로세스**:
1. 최신 시장 데이터 수집
2. 현재 포지션 상태 확인 (PnL, 경과 시간)
3. AI 재평가 요청
4. 결정에 따른 조치

**AI 결정 유형**:

| 결정 | 의미 | 조치 |
|------|------|------|
| HOLD | 현 상태 유지 | 다음 점검 예약 |
| MODIFY | 전략 수정 | 손절/익절가 변경 |
| EXIT | 즉시 청산 | 시장가 청산 실행 |

---

## 4. 기술적 지표 및 분석

### 4.1 추세 지표

**EMA (Exponential Moving Average)**:
- 20 EMA: 단기 추세
- 50 EMA: 중기 추세
- 120 EMA: 장기 추세
- 200 EMA: 초장기 추세

EMA 정배열 (20 > 50 > 120 > 200): 강한 상승 추세
EMA 역배열 (20 < 50 < 120 < 200): 강한 하락 추세

**ADX (Average Directional Index)**:
- 25 이상: 추세 존재 (추세 추종 전략 유효)
- 20 미만: 추세 부재 (평균 회귀 전략 검토)

### 4.2 모멘텀 지표

**RSI (Relative Strength Index)**:
- 70 이상: 과매수 구간
- 30 이하: 과매도 구간
- 다이버전스 감지에 활용

**MACD (Moving Average Convergence Divergence)**:
- MACD 라인: 12 EMA - 26 EMA
- 시그널 라인: MACD의 9 EMA
- 히스토그램: MACD - 시그널

골든크로스/데드크로스 신호 생성

### 4.3 변동성 지표

**Bollinger Bands**:
- 중심선: 20 SMA
- 상단/하단: 중심선 ± 2σ
- 밴드 폭으로 변동성 측정

**ATR (Average True Range)**:
- 14일 평균 True Range
- 손절가 거리 계산에 활용
- 변동성 기반 포지션 사이징 참고

### 4.4 추세 분석 결과

시스템은 위 지표들을 종합하여 추세 상태를 분류:

| 추세 상태 | 조건 |
|----------|------|
| STRONG_BULLISH | EMA 정배열 + 가격 > EMA + MACD 양수 |
| BULLISH | EMA 정배열 + 가격 > EMA |
| WEAK_BULLISH | 가격 > EMA만 충족 |
| NEUTRAL | 명확한 방향성 없음 |
| WEAK_BEARISH | 가격 < EMA만 충족 |
| BEARISH | EMA 역배열 + 가격 < EMA |
| STRONG_BEARISH | EMA 역배열 + 가격 < EMA + MACD 음수 |

---

## 5. 리스크 관리 체계

### 5.1 레버리지-손절 연동

높은 레버리지일수록 좁은 손절폭을 적용하여 실제 손실률을 일정하게 유지:

| 레버리지 | 청산까지 가격변동 | 권장 손절폭 | 실제 손실 |
|---------|------------------|------------|----------|
| 3x | -33% | -10% | -30% |
| 5x | -20% | -6% | -30% |
| 7x | -14% | -4% | -28% |
| 10x | -10% | -3% | -30% |

### 5.2 수수료 구조

**Bybit 수수료율**:
- Maker (지정가): 0.02%
- Taker (시장가): 0.055%

**레버리지별 왕복 수수료** (시장가 기준, 원금 대비):

| 레버리지 | 왕복 수수료 |
|---------|------------|
| 1x | 0.11% |
| 3x | 0.33% |
| 5x | 0.55% |
| 7x | 0.77% |
| 10x | 1.1% |

**손익분기점**: 왕복 수수료 / 레버리지

10x 레버리지의 경우, 가격이 0.11% 이상 움직여야 본전

### 5.3 청산 방어

**청산가 계산 공식** (Cross Margin):

```
롱 청산가 = 진입가 × (1 - 1/레버리지 + 유지마진율)
숏 청산가 = 진입가 × (1 + 1/레버리지 - 유지마진율)
```

유지마진율: 0.4% (BTC 기준)

**방어선 설정**:
- 손절가는 청산가보다 최소 2% 이상 마진 확보
- 청산가 3% 이내 접근 시 긴급 알림 발송

### 5.4 펀딩비 관리

**정산 시간**: UTC 00:00, 08:00, 16:00 (8시간마다)

**영향**:
- 양수 펀딩비: 롱 포지션이 숏에게 지불
- 음수 펀딩비: 숏 포지션이 롱에게 지불

포지션 청산 시 누적 펀딩비를 손익에 반영

---

## 6. WebSocket 및 실시간 모니터링

### 6.1 WebSocket 구조

**Public Stream** (`wss://stream.bybit.com/v5/public/linear`):
- 구독 토픽: `tickers.BTCUSDT`
- 수신 데이터: mark_price, last_price, funding_rate 등
- 용도: 실시간 가격 모니터링, 익절/손절 조건 체크

**Private Stream** (`wss://stream.bybit.com/v5/private`):
- 구독 토픽: `position`
- 인증 방식: HMAC SHA256 서명
- 용도: 강제청산 감지, 포지션 상태 변경 감지

### 6.2 연결 유지 메커니즘

**Ping/Pong Heartbeat**:
- 20초마다 ping 메시지 전송
- 연결 유지 확인

**자동 재연결**:
- 연결 종료 감지 시 5초 대기 후 재연결 시도
- 별도 스레드에서 비동기 처리

### 6.3 Dead Man's Switch

WebSocket 연결이 끊기거나 데이터 수신이 중단될 경우를 대비한 안전장치:

**동작 원리**:
1. WebSocket 데이터 수신 시마다 타이머 리셋 (heartbeat)
2. 60초간 데이터 미수신 시 트리거
3. REST API로 폴백하여 포지션 상태 확인
4. 손절/익절 조건 충족 시 긴급 청산

**상태 확인 항목**:
- 현재 포지션 존재 여부
- 현재가 대비 손절/익절가 도달 여부
- 청산가 근접 여부

### 6.4 강제청산 감지

Private WebSocket에서 포지션 크기가 0으로 변경되는 것을 감지:

**처리 플로우**:
1. `position` 토픽에서 size = 0 감지
2. 내부적으로 익절/손절 처리 중인지 확인
3. 외부 처리가 아니면 강제청산으로 판단
4. `LIQUIDATION` 사유로 청산 기록

---

## 7. 데이터베이스 구조

### 7.1 테이블 구조

**futures_positions**: 포지션 히스토리

| 컬럼 | 타입 | 설명 |
|------|------|------|
| position_uuid | TEXT | 고유 식별자 (PK) |
| direction | TEXT | LONG / SHORT |
| leverage | INTEGER | 레버리지 배수 |
| entry_price | REAL | 진입가 |
| entry_quantity | REAL | 진입 수량 |
| entry_timestamp | TEXT | 진입 시각 |
| stop_loss_price | REAL | 손절가 |
| take_profit_price | REAL | 익절가 |
| liquidation_price | REAL | 청산가 |
| confidence_score | INTEGER | AI 확신도 |
| ai_reason | TEXT | AI 판단 근거 |
| status | TEXT | ACTIVE / CLOSED / LIQUIDATED |
| exit_price | REAL | 청산가 |
| exit_timestamp | TEXT | 청산 시각 |
| exit_reason | TEXT | 청산 사유 |
| realized_pnl | REAL | 실현 손익 |
| entry_fee | REAL | 진입 수수료 |
| exit_fee | REAL | 청산 수수료 |
| total_fee | REAL | 총 수수료 |

**position_rechecks**: 중간 점검 로그

| 컬럼 | 타입 | 설명 |
|------|------|------|
| position_uuid | TEXT | 포지션 참조 (FK) |
| recheck_timestamp | TEXT | 점검 시각 |
| current_price | REAL | 점검 시 현재가 |
| unrealized_pnl | REAL | 미실현 손익 |
| ai_decision | TEXT | HOLD / MODIFY / EXIT |
| modifications_json | TEXT | 수정 내용 JSON |
| ai_reason | TEXT | AI 판단 근거 |

**funding_history**: 펀딩비 기록

| 컬럼 | 타입 | 설명 |
|------|------|------|
| position_uuid | TEXT | 포지션 참조 (FK) |
| funding_time | TEXT | 정산 시각 |
| funding_rate | REAL | 펀딩비율 |
| funding_fee | REAL | 실제 정산 금액 |

### 7.2 통계 쿼리

**거래 통계** (최근 7일):
- 총 거래 횟수
- 승/패 횟수 및 승률
- 누적 손익
- 평균 손익률
- 총 수수료

---

## 8. 알림 시스템

### 8.1 우선순위 체계

| 우선순위 | 카테고리 | 용도 | 예시 |
|---------|---------|------|------|
| P0 | EMERGENCY | 즉시 확인 필요 | 청산 근접, WebSocket 끊김 |
| P1 | TRADE | 거래 관련 | 포지션 진입/청산 |
| P2 | INFO | 정보성 | AI 분석 결과, 중간 점검 |
| P3 | STATUS | 상태 보고 | 시스템 시작/종료, 일일 리포트 |

### 8.2 알림 발송 시점

**시스템 이벤트**:
- 시스템 시작/재시작
- 시스템 오류 발생

**Phase 2**:
- TRADE 결정 (방향, 확신도, 레버리지)
- WAIT 결정 (다음 분석 시간)

**Phase 3**:
- 전략 수립 완료 (손익절가, R:R 비율)

**Phase 4**:
- 포지션 진입 완료 (체결가, 수수료)
- 중간 점검 결과 (HOLD/MODIFY/EXIT)
- 포지션 청산 완료 (손익 상세)
- 청산가 근접 경고
- WebSocket 끊김 감지
- Dead Man's Switch 실행 결과

**정기 리포트**:
- 일일 리포트 (매일 09:00 KST)

---

## 9. 환경 변수

`.env` 파일에 다음 항목 설정 필요:

| 변수명 | 설명 |
|--------|------|
| BYBIT_API_KEY | Bybit Production API 키 |
| BYBIT_SECRET | Bybit Production Secret |
| BYBIT_TESTNET_API_KEY | Bybit Testnet API 키 |
| BYBIT_TESTNET_SECRET | Bybit Testnet Secret |
| BYBIT_USE_TESTNET | Testnet 사용 여부 (true/false) |

> ⚠️ 실제로는 `config/settings.py:19` 의 `_USE_TESTNET = False` 가 하드코딩돼 있어 이 환경변수는 무시된다.
| TELEGRAM_BOT_TOKEN | 텔레그램 봇 토큰 |
| TELEGRAM_CHAT_ID | 텔레그램 채팅 ID |
| GEMINI_API_KEY | Google Gemini API 키 |

---

## 10. 프로젝트 구조

```
metis-futures/
│
├── main.py                     # 메인 엔트리 포인트, Phase 순환 루프
├── dashboard_app.py            # Streamlit 대시보드 (선택적)
├── requirements.txt            # Python 의존성
├── .env                        # 환경 변수 (gitignore)
│
├── config/                     # 설정 모듈
│   ├── __init__.py
│   ├── settings.py             # 전역 설정 상수
│   └── logging_config.py       # 로깅 설정
│
├── core/                       # 핵심 비즈니스 로직
│   ├── __init__.py
│   ├── data_fetcher.py         # Phase 1: 데이터 수집
│   ├── technical_analysis.py   # 기술적 지표 계산
│   ├── chart_generator.py      # 캔들스틱 차트 생성
│   ├── leverage_calculator.py  # 레버리지/청산가/포지션 계산
│   ├── position_manager.py     # 포지션 진입/청산 관리
│   ├── websocket_watcher.py    # 실시간 감시 + Dead Man's Switch
│   └── scheduler.py            # 중간 점검/일일 리포트 스케줄링
│
├── ai/                         # AI/LLM 연동
│   ├── __init__.py
│   ├── gemini_client.py        # Gemini API 클라이언트
│   └── prompts.py              # Phase별 프롬프트 템플릿
│
├── exchange/                   # 거래소 연동
│   ├── __init__.py
│   ├── bybit_client.py         # Bybit REST API 클라이언트
│   └── bybit_websocket.py      # Bybit WebSocket 핸들러
│
├── database/                   # 데이터 영속성
│   ├── __init__.py
│   ├── db_manager.py           # SQLite CRUD 및 통계 쿼리
│   └── schema.sql              # 테이블 스키마 정의
│
├── utils/                      # 유틸리티
│   ├── __init__.py
│   └── telegram_bot.py         # 텔레그램 알림 발송
│
└── logs/                       # 로그 파일 (gitignore)
    ├── app.log                 # 애플리케이션 로그
    ├── output.log              # 봇 실행 출력
    └── dashboard.out           # 대시보드 출력
```
