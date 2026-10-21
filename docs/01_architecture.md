# AI 모니터링 에이전트 아키텍처

> 상태: 초안 (2026-10-21)
> 출발 문서: [claude_code_prompt_specification.md](claude_code_prompt_specification.md) (Gemini 작성본)
> 관련 문서: [02_dify_agent_prerequisites.md](02_dify_agent_prerequisites.md) · [03_dify_agent_registration_guide.md](03_dify_agent_registration_guide.md)

---

## 1. 레거시 방식과 AI 에이전트 방식의 차이

### 1.1 레거시 흐름

```mermaid
flowchart LR
    A["상시 모니터링"] --> B{"임계치(정량)<br/>1분 이상 지속?"}
    B -- 아니오 --> A
    B -- 예 --> C["수신자 목록 조회<br/>(DB/파일)"]
    C --> D["메일 / 대시보드 /<br/>이벤트 전파"]
    D --> E["👤 사람이 시스템 접속<br/>원인 파악"]
    E --> F["👤 사람이 조치"]

    classDef human fill:#fde2e2,stroke:#c0392b,color:#1a1a1a;
    class E,F human;
```

이 흐름에서 시스템이 하는 일은 **"알린다"** 까지다. 무슨 일이 일어났고, 왜 일어났고, 무엇을 해야 하는지는 메일을 받은 사람이 직접 알아내야 한다.

### 1.2 AI 에이전트가 들어오면 바뀌는 지점

에이전트가 레거시 파이프라인을 대체하지는 않는다. **감지는 그대로 두고, 그 다음 단계를 맡는다.** 사람이 메일을 받고 나서 하던 일, 즉 접속하고, 로그를 보고, 원인을 추정하고, 조치 방법을 고르는 일을 에이전트가 먼저 해 둔다.

| 단계 | 레거시 | AI 에이전트 도입 후 |
|---|---|---|
| 감지 | 고정 임계치 (CPU > 90%, 1분 지속) | 고정 임계치는 **유지**하고, 추세·변화율·로그 패턴 같은 정성 신호를 추가 |
| 판단 | 없음 (넘었다/안 넘었다) | 맥락 해석: 배포 직후인지, 배치 시간대인지, 다른 지표와 함께 움직이는지 |
| 원인 분석 | 사람이 접속해서 로그를 확인 | 에이전트가 관련 로그·메트릭·최근 변경 이력을 직접 조회하고 원인을 요약 |
| 알림 대상 | 고정 목록 (DB/파일) | 목록은 유지하고, 심각도와 원인 영역에 따라 대상·채널을 고름 |
| 알림 내용 | "CPU 92% 초과" | "CPU 92%. 10:40 배포 후 GC가 급증했고 OOM 로그 3건이 있음. 추정 원인은 X. 권장 조치는 Y." |
| 조치 | 사람이 직접 수행 | 에이전트가 조치를 제안하고 사람이 승인하면 실행. 위험도가 낮은 조치는 자동 실행 |
| 사후 | 사람이 장애 보고서 작성 | 타임라인과 조치 이력을 바탕으로 보고서 초안 자동 작성 |
| 학습 | 임계치를 수동으로 튜닝 | 과거 장애·조치 이력을 지식베이스(RAG)에 쌓아 다음 판단에 활용 |

정리하면, **알림을 보내는 시스템**이 **1차 대응까지 하고 사람에게 넘기는 시스템**으로 바뀐다. 사람이 하는 일은 "원인 찾기"에서 "에이전트의 판단을 검토하고 승인하기"로 옮겨간다.

### 1.3 바뀌지 않아야 하는 것 (설계 원칙)

1. **정량 임계치 판정은 코드가 한다.** "CPU > 90%가 1분 지속"은 결정론적 규칙이므로 LLM에 맡기면 안 된다. LLM은 숫자 비교를 틀릴 수 있고 비용도 든다. Gemini 원문 §2.A의 Analysis Rule 1을 프롬프트에 넣는 방식은 수정이 필요하다.
2. **LLM은 매 주기마다 호출하지 않는다.** 원문은 Cron이 돌 때마다 Dify를 호출하는 구조인데, 그러면 정상 상태에서도 토큰을 계속 쓴다. 규칙 엔진이 이벤트(임계치 초과 또는 추세 경고)를 만들었을 때만 에이전트를 호출한다.
3. **에이전트는 자유 형식 명령을 실행하지 않는다.** `recommended_action`에는 셸 명령 문자열이 아니라 **사전에 등록된 조치 ID**(예: `RESTART_SERVICE`, `CLEAR_CACHE`)만 허용한다.
4. **기존 알림 경로는 대체 경로로 남겨 둔다.** Dify나 LLM이 장애일 때도 레거시 알림은 나가야 한다.

---

## 2. 목표 아키텍처

```mermaid
flowchart TB
    subgraph LEGACY["기존 영역 (유지 · 재사용)"]
        direction LR
        COL["수집기 / APM"] --> RULE["규칙 엔진<br/>임계치 · 지속시간 · 변화율"]
        RULE --> BUS["이벤트 버스"]
        MAIL["메일 발송 시스템 (구축됨)<br/>수신자 목록 · 발송"]
        RULE -. "대체 경로 (Dify 장애 시)" .-> MAIL
    end

    subgraph ORCH["오케스트레이터 (Backend)"]
        direction TB
        DEDUP["이벤트 중복 제거 / 묶기<br/>(연쇄 알림 억제)"]
        VALID["응답 JSON 스키마 검증"]
        POLICY["조치 정책 테이블<br/>(승인 필요 여부 최종 결정)"]
        GW["승인 게이트웨이 (HITL)<br/>+ 감사 로그"]
    end

    subgraph DIFY["Dify Self-hosted · Workflow (본인 담당)"]
        direction TB
        S["① Start<br/>이벤트 payload"] --> T["② Custom Tool<br/>로그 / 메트릭 시계열 / 배포 이력"]
        T --> CODE["③ Code (Python)<br/>변화율 · 추세 계산"]
        CODE --> KB["④ Knowledge Retrieval<br/>과거 장애 · 런북 (RAG)"]
        KB --> LLM["⑤ LLM<br/>원인 추정 · 심각도 · 조치 ID 선택"]
        LLM --> OUT["⑥ End<br/>Structured Output (JSON)"]
    end

    subgraph EXT["자체 API (Tool 대상)"]
        LOGAPI["로그 조회 API (구축됨)"]
        METAPI["메트릭 조회 API (구축됨)"]
        DEPAPI["배포 이력 API (확인 필요)"]
    end

    PORTAL["운영 포탈 (신규)<br/>승인 페이지 · 분석 상세 · 이력"]
    MSG["직접 구현한 메신저<br/>(버튼 · 콜백 없음)"]

    BUS -- "이벤트 발생 시에만" --> DEDUP
    DEDUP -- "POST /v1/workflows/run" --> S
    T <--> LOGAPI & METAPI & DEPAPI
    OUT -- "결과 JSON" --> VALID
    VALID --> POLICY

    POLICY -- "분석 요약 + 포탈 링크" --> MAIL
    POLICY -- "조치 제안" --> GW
    GW -- "승인 토큰 발급<br/>(UUID + 만료시각, DB 저장)" --> TOKDB[("승인 요청 DB")]
    GW -- "토큰 링크 메시지 발송" --> MSG
    MSG --> ADMIN["👤 승인자"]
    ADMIN -- "링크 열기 (SSO 로그인)" --> PORTAL
    PORTAL -- "토큰 검증 · 승인 / 거절 (POST)" --> GW
    GW <--> TOKDB
    GW -- "승인 확정" --> ACT["조치 API<br/>화이트리스트 조치 ID만 실행"]
    GW -- "결과 메시지 발송" --> MSG
    MAIL --> ADMIN
    PORTAL -. "Dify Service API<br/>(실행 로그 · 대화형 질의)" .-> DIFY

    classDef dify fill:#e3f2fd,stroke:#1565c0,color:#1a1a1a;
    classDef human fill:#fde2e2,stroke:#c0392b,color:#1a1a1a;
    classDef legacy fill:#f5f5f5,stroke:#757575,color:#1a1a1a;
    classDef new fill:#e8f5e9,stroke:#2e7d32,color:#1a1a1a;
    class S,T,CODE,KB,LLM,OUT dify;
    class ADMIN human;
    class COL,RULE,BUS,MAIL,LOGAPI,METAPI legacy;
    class PORTAL,TOKDB new;
    class MSG legacy;
```

### 2.0 이벤트 1건의 처리 순서

```mermaid
sequenceDiagram
    autonumber
    participant R as 규칙 엔진
    participant O as 오케스트레이터
    participant D as Dify Workflow
    participant API as 자체 API (Tool)
    participant N as 메일 발송 시스템 (기존)
    participant M as 직접 구현한 메신저 (버튼 없음)
    actor A as 승인자
    participant P as 운영 포탈
    participant X as 조치 API

    R->>O: 이벤트 (rule_id, host, snapshot)
    O->>O: 중복 제거 / 묶기
    O->>D: POST /v1/workflows/run
    D->>API: 로그 · 메트릭 · 배포 이력 조회
    API-->>D: 조회 결과
    D->>D: 추세 계산 → RAG → LLM 분석
    D-->>O: 결과 JSON (status, root_cause, action_id)
    O->>O: 스키마 검증 + 정책 테이블로 승인 필요 여부 결정
    par 알림
        O->>N: 분석 요약 메일 (+ 포탈 상세 링크)
        N->>A: 메일
    and 승인 요청
        O->>O: 승인 토큰 발급 (UUID, 만료시각, 대상 승인자, 상태=PENDING)
        O->>M: 요약 + 승인 링크 (https://portal/approve/{token})
        M->>A: 메신저 알림
    end
    A->>P: 링크 열기
    P->>P: SSO 로그인 (승인자 본인 확인)
    P->>O: 토큰 조회 (GET, 상태 변경 없음)
    O-->>P: 요청 내용 · 근거 · 조치 ID · 남은 시간
    alt 승인
        A->>P: [승인] 클릭 (확인 단계 포함)
        P->>O: POST 승인 (token, 로그인 사용자)
        O->>O: 토큰 유효·만료·미사용 확인, 사용자 = 대상 승인자 확인, 상태=APPROVED (1회용 소진), 감사 로그
        O->>X: 조치 ID 실행
        X-->>O: 실행 결과
        O->>M: 결과 메시지 (승인자 · 실행 결과)
    else 거절
        A->>P: [거절] 클릭 (사유 입력)
        P->>O: POST 거절
        O->>O: 상태=REJECTED, 감사 로그, 수동 대응으로 전환
        O->>M: 결과 메시지 (거절됨)
    else 만료
        O->>O: 만료시각 경과 → 상태=EXPIRED
        O->>M: 만료 메시지 + 에스컬레이션 대상에게 새 토큰 발송
    end
    Note over O,D: Dify 장애·타임아웃 시 기존 형식의 레거시 메일만 발송
```

### 2.1 구성요소별 책임

| 구성요소 | 책임 | 담당 |
|---|---|---|
| 수집기 / APM | 메트릭·로그 수집. **조회 API 구축됨** | 기존 |
| 규칙 엔진 | 정량 임계치, 지속시간, 변화율 기반 1차 감지. 이벤트 생성 | Backend |
| 오케스트레이터 | 이벤트를 받아 Dify 호출, 결과 검증, 라우팅, 승인 처리 | Backend |
| **Dify Workflow / Agent** | 맥락 수집(Tool), 분석, 원인 요약, 조치 제안 | **본인 (Dify 등록)** |
| 메일 발송 시스템 | 수신자 목록 관리, 발송 (**구축됨, 재사용**). 본문에 분석 요약과 포탈 링크 추가 | 기존 |
| 승인 게이트웨이 | 승인 토큰 발급·검증·소진, 만료 처리, 승인자 권한 확인, 감사 로그, 메신저 메시지 발송 | Backend |
| 직접 구현한 메신저 | **승인 요청 전달 채널**. 버튼과 콜백이 없어서 토큰 링크가 담긴 메시지만 보냄 | 기존 |
| 운영 포탈 | **승인 페이지**(토큰 링크로 진입, SSO 로그인 후 승인/거절), 분석 근거 상세, 이력, 대시보드 | 신규 |
| 조치 API | 화이트리스트 조치만 실행 | 인프라 / Backend |

### 2.2 Dify 앱 형태 선택

| 형태 | 적합한 경우 | 이 프로젝트에서 |
|---|---|---|
| Workflow | 입력과 출력이 정해진 단발 처리. 단계가 고정 | **기본 분석 파이프라인** (이벤트 1건 → 분석 결과 1건) |
| Agent (Chatflow + Agent 노드) | 상황에 따라 어떤 도구를 부를지 LLM이 결정 | 원인이 불명확할 때 도구를 반복 호출하는 심층 분석, 운영자 대화형 질의 |

1차 범위는 Workflow로 시작하고, 운영자가 "왜 그렇게 판단했어?"라고 묻는 대화형 기능은 2차에서 Chatflow Agent로 추가한다.

### 2.3 플랫폼 구성 방안

검토 대상은 세 가지다.

| 방안 | 내용 | 장점 | 단점 |
|---|---|---|---|
| **A. Dify Self-hosted** | Dify를 자체 서버에 설치하고 Dify 콘솔에서 에이전트를 등록·운영 | 바로 시작 가능. Workflow·Tool·RAG·로그가 기본 제공됨 | 승인 화면이나 장애 이력 같은 운영 기능은 Dify에 없음 |
| **B. Dify와 비슷한 플랫폼 자체 개발** | LangGraph 같은 프레임워크로 워크플로·도구·RAG 엔진을 직접 구현 | 완전히 통제 가능. 라이선스 제약 없음 | 개발·유지보수 비용이 큼. Dify가 이미 제공하는 기능을 다시 만드는 셈 |
| **C. A + Dify API 기반 별도 포탈** | 엔진은 Dify Self-hosted. 운영자용 화면은 Dify Service API를 호출하는 자체 포탈로 구성 | 엔진은 그대로 쓰고, 운영 기능(승인·이력·대시보드)만 직접 만듦 | 포탈 개발이 필요함 |

```mermaid
flowchart LR
    subgraph ROLE["역할 분리 (방안 C)"]
        direction TB
        DEV["👤 에이전트 담당 (본인)"] -- "앱 · Tool · Knowledge 등록<br/>프롬프트 수정 · DSL export" --> CONSOLE["Dify 콘솔"]
        OPS["👤 운영자 / 승인자"] -- "분석 결과 확인 · 승인 · 이력 조회" --> PORTAL["운영 포탈"]
        PORTAL -- "Service API<br/>(앱 API Key)" --> ENGINE["Dify 엔진"]
        CONSOLE --> ENGINE
    end
```

**권장: 방안 C (A로 시작해서 포탈을 붙임)**

- 에이전트 등록과 수정은 Dify 콘솔에서 한다. 운영자는 Dify 콘솔에 접근하지 않고 포탈만 사용한다.
- 포탈은 **공식 Service API**(`/v1/workflows/run`, `/v1/chat-messages`, `/v1/workflows/logs` 등, 앱별 API Key)만 사용한다. Dify 콘솔 내부 API(`/console/api/...`)로 앱을 생성하거나 수정하는 기능은 공식 계약이 아니어서 Dify를 업그레이드하면 깨질 수 있으므로 포탈 범위에서 제외한다.
- 승인 상태, 장애 이력, 감사 로그는 Dify가 아니라 **오케스트레이터와 포탈의 DB**에 저장한다. 나중에 엔진을 B안으로 바꾸더라도 포탈과 데이터는 그대로 쓸 수 있다. 다만 Dify 1.13부터는 Human Input 노드로 Dify 안에서 승인 대기를 처리할 수 있어서 이 부분을 재검토하고 있다 ([02 열린 결정](02_dify_agent_prerequisites.md), [03 §5.7](03_dify_agent_registration_guide.md)).
- B안은 Dify 라이선스나 기능 제약 때문에 막힐 때만 검토한다. 이를 위해 오케스트레이터가 엔진을 호출하는 인터페이스(§3 데이터 계약)를 Dify에 종속되지 않게 유지한다.

> **라이선스 확인 필요**: Dify는 Apache 2.0을 기반으로 추가 조건을 붙인 자체 라이선스를 쓴다. 알려진 조건은 (1) 멀티테넌트 SaaS로 운영할 때 상용 라이선스 필요, (2) Dify 콘솔 프론트엔드의 로고·저작권 표시 제거 금지다. 단일 조직용 설치와 Service API를 호출하는 자체 포탈은 문제없을 것으로 보이지만, 사용하는 버전의 LICENSE 파일을 법무와 함께 확인한다.

---

## 3. 데이터 계약 (초안)

### 3.1 오케스트레이터 → Dify (Workflow inputs)

```json
{
  "event_id": "evt-20261021-0001",
  "source_system": "order-api",
  "host": "prd-app-03",
  "rule_id": "CPU_HIGH_1M",
  "detected_at": "2026-10-21T10:41:00+09:00",
  "metric_snapshot": "{\"cpu\": 92.4, \"mem\": 71.0, \"tps\": 1830}",
  "window_minutes": 15
}
```

> Dify Workflow 입력 변수는 문자열·숫자 위주이므로 중첩 객체는 JSON 문자열로 넘기고 Code 노드에서 파싱한다. (확인 필요: 사용하는 Dify 버전에서 object 타입 입력을 지원하는지)

### 3.2 Dify → 오케스트레이터 (출력)

```json
{
  "status": "NORMAL | WARNING | CRITICAL",
  "trend_analysis": "string",
  "root_cause_summary": "string (2~3문장)",
  "evidence": ["근거로 삼은 로그/지표 요약"],
  "recommended_action_id": "RESTART_SERVICE | CLEAR_CACHE | SCALE_OUT | NONE",
  "action_params": { "service": "order-api" },
  "requires_approval": true,
  "confidence": 0.0
}
```

원문 대비 변경점:
- `recommended_action`(자유 문자열) → `recommended_action_id` + `action_params` (화이트리스트)
- `evidence`, `confidence` 추가: 승인자가 판단 근거를 확인할 수 있게 함
- `requires_approval`은 LLM이 정하지 않고 **조치 ID별 정책 테이블**로 오케스트레이터가 최종 결정한다 (LLM 값은 참고용)

### 3.3 승인 토큰

직접 구현한 메신저는 버튼과 콜백이 없고 링크는 넣을 수 있다. 그래서 **유효기간이 있는 1회용 토큰을 링크로 보내고, 승인은 포탈 승인 페이지에서** 한다.

**메시지 예시**
```
[CRITICAL] order-api / prd-app-03
원인 추정: 10:40 배포 후 힙 사용량 급증, OOM 3건
제안 조치: RESTART_SERVICE (order-api)
승인 링크 (10:56까지 유효): https://portal.internal/approve/3f8c2a1e-7b4d-4e0a-9c55-1d2e6f7a8b90
```

**토큰 테이블 (승인 요청 DB)**

| 컬럼 | 설명 |
|---|---|
| `token_hash` | 토큰의 SHA-256 해시. **원문은 저장하지 않는다** (DB가 유출되어도 링크로 쓸 수 없게) |
| `event_id` / `analysis_id` | 어떤 분석 결과에 대한 승인인지 |
| `action_id`, `action_params` | 승인 대상 조치 (발급 시점에 고정. 승인 페이지에서 바꿀 수 없음) |
| `approver_id` | 대상 승인자 (사번). 승인자가 여러 명이면 사람마다 토큰을 따로 발급 |
| `expires_at` | 만료시각. **서버 DB 값이 기준** |
| `status` | `PENDING` → `APPROVED` / `REJECTED` / `EXPIRED` / `SUPERSEDED` |
| `decided_by`, `decided_at`, `reason` | 실제 결정한 사람(SSO 사용자), 시각, 거절 사유 |

**규칙**
1. **토큰 생성**: 암호학적으로 안전한 난수로 UUID v4를 생성한다 (`uuid.uuid4()`, `crypto.randomUUID()` 등). 순번이나 시간 기반 UUID(v1)는 추측할 수 있으므로 쓰지 않는다.
2. **유효기간은 서버에서 관리**한다. 만료시각을 토큰 문자열 안에 넣는다면 HMAC 서명을 붙여야 한다. 서명이 없으면 사용자가 값을 고쳐서 기한을 늘릴 수 있다. 가장 간단한 방법은 토큰에는 UUID만 넣고 만료시각은 DB에 두는 것이다.
3. **링크를 여는 것(GET)만으로는 아무것도 바뀌지 않는다.** 승인과 거절은 페이지 안의 버튼(POST)으로만 한다. 메신저의 링크 미리보기 기능이나 보안 스캐너가 링크를 먼저 열어 볼 수 있기 때문이다.
4. **토큰만으로 승인되지 않는다.** 승인 페이지는 SSO 로그인을 요구하고, 로그인한 사용자가 `approver_id`와 같거나 승인 권한이 있는지 확인한다. 링크가 다른 사람에게 전달되거나 채팅방에 노출되어도 대신 승인할 수 없게 하기 위해서다.
5. **1회용**: 결정이 나면 즉시 상태를 바꾸고(조건부 UPDATE `WHERE status='PENDING'`), 같은 이벤트에 대한 다른 승인자의 토큰은 `SUPERSEDED`로 바꾼다. 결정은 먼저 한 사람 것 하나만 유효하다.
6. **유효기간**: 조치 위험도와 장애 심각도에 따라 정한다 (예: CRITICAL 15분, WARNING 60분). 만료되면 에스컬레이션 대상에게 새 토큰을 발급한다.
7. **감사 로그**: 발급, 조회, 결정, 만료를 모두 기록한다 (토큰 원문은 기록하지 않음).

---

## 4. 열린 질문

- [x] ~~Dify 배포 형태~~ → Self-hosted (또는 자체 플랫폼, Dify API 기반 포탈). §2.3 참고
- [x] ~~로그·메트릭 조회 API 존재 여부~~ → **구축됨**
- [x] ~~레거시 알림~~ → 메일 발송 시스템 **어느 정도 구축됨**, 재사용
- [ ] Dify 버전 (설치 예정 버전 / 기존 설치본)
- [ ] 방안 A / B / C 최종 결정
- [ ] 사용할 LLM 모델과 외부 반출 가능 데이터 범위 (자체 호스팅 모델인지, 외부 API인지, 로그 마스킹 필요 여부)
- [ ] 기존 로그·메트릭 API의 스펙 문서 형태 (OpenAPI 유무), 인증 방식, 응답 크기 제한
- [ ] 기존 메일 시스템을 외부에서 호출할 수 있는지 (API / 큐 / DB insert), 본문 템플릿(HTML)을 바꿀 수 있는지
- [x] ~~메일 외 채널~~ → **승인은 직접 구현한 메신저**로 함 (2026-10-21)
- [x] ~~메신저 기능~~ → 직접 구현한 메신저. **버튼·콜백 없음, 링크는 가능**. 유효기간 + UUID 토큰 링크 발송 방식 (§3.3)
- [ ] 포탈 승인 페이지에 SSO를 적용할 수 있는지
- [x] ~~메시지에 링크를 넣을 수 있는지~~ → **가능**
- [ ] 메신저가 링크 미리보기(URL 사전 접속)를 하는지. 해도 문제는 없지만(§3.3 규칙 3) 접속 로그를 해석할 때 필요
- [ ] 배포 이력 API 존재 여부
- [ ] 규칙 엔진을 기존 모니터링 솔루션이 담당하는지, 새로 구현하는지
- [ ] 자동 실행을 허용할 조치 범위

---

## 변경 이력

| 날짜 | 내용 |
|---|---|
| 2026-10-21 | 초안 작성. 레거시 비교, 목표 아키텍처, 데이터 계약 초안 |
| 2026-10-21 | 아키텍처 다이어그램을 Mermaid로 전환 (레거시 흐름, 목표 아키텍처, 처리 시퀀스) |
| 2026-10-21 | Self-hosted 전제 반영. §2.3 플랫폼 구성 방안(A/B/C) 추가. 기존 로그·메트릭 API와 메일 시스템 재사용, 운영 포탈 추가 |
| 2026-10-21 | Human Input 노드(Dify 1.13+)를 승인 처리 대안으로 언급 |
| 2026-10-21 | 승인 채널을 직접 구현한 메신저로 확정. 다이어그램·시퀀스·책임표 반영 |
| 2026-10-21 | 메신저 버튼·콜백 없음 → 토큰 링크 + 포탈 승인 페이지 구조로 변경. §3.3 승인 토큰 추가 |
