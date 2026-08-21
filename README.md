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

## 상세 설계

DB 컬럼 정의·알림 우선순위·Phase 별 구현 내역 등 상세는 [docs/DESIGN.md](docs/DESIGN.md) 로 옮겼다.

## 알려진 한계 / 왜 대체되었나

- 이 세대는 **METIS v4~v7 로 대체**됐다(같은 계보의 후속). 여기 코드는 유지보수하지 않는다.
- 수익을 내지 못했다. 이 저장소는 성과가 아니라 **설계와 시행착오의 기록**으로 남긴다.
- 백테스트가 아니라 스펙 중심으로 만들어져, 파라미터의 근거가 데이터보다 판단에 기대고 있다.
- 아카이브 저장소다. 실행을 전제로 하지 말 것.
