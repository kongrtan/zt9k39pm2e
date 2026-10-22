# Dify 에이전트 등록 사전 준비 사항

> 상태: 작성 중 (계속 추가)
> 상위 문서: [01_architecture.md](01_architecture.md)
> 범례: `[ ]` 미착수 · `[~]` 진행 중 · `[x]` 완료 · **담당**은 확정되면 기입

---

## 0. 필수 입력값 요약

Dify에 실제로 넣어야 하는 값들이다. 이 값들이 모두 준비되어야 등록을 시작할 수 있다. 구조 설명은 [04 플랫폼 구조](04_dify_platform_structure.md)에 있다.

| 구분 | 항목 | 예시 | 필수 | 입력 위치 |
|---|---|---|---|---|
| **Dify 서버** | 접속 URL (콘솔 / API) | `https://dify.internal`, `https://dify.internal/v1` | 필수 | 설치 시 `.env` |
| | DB · Redis · Vector DB · 파일 저장소 접속 정보 | PostgreSQL, Redis, Weaviate/pgvector, MinIO | 필수 | 설치 시 `.env` |
| | `SECRET_KEY` (자격증명 암호화 키) | 랜덤 문자열 | 필수 | `.env`. **분실하면 저장된 키를 복호화할 수 없음** |
| | SMTP | 내부 메일 릴레이 | 선택 | `.env` (초대 메일 등) |
| **LLM** | 공급자 유형 | OpenAI-API-compatible / Azure OpenAI / Anthropic 등 | 필수 | Settings → Model Provider |
| | 엔드포인트 URL | `http://llm-gw.internal/v1` | 필수 | 〃 |
| | 모델 이름 (정확한 model ID) | `gpt-4.1`, `qwen3-32b` | 필수 | 〃 |
| | API Key | | 필수 (서버가 요구하면) | 〃 |
| | 컨텍스트 길이 · 최대 출력 토큰 | 128000 / 4096 | 필수 | 〃 (OpenAI 호환일 때 직접 입력) |
| | 기능 지원 여부: Function calling, Structured output, Streaming, Vision | | 필수 | 〃 (Agent 노드와 Structured Output 사용 가능 여부가 여기서 정해짐) |
| **Embedding** | 엔드포인트 · 모델 이름 · API Key | `bge-m3` | Knowledge 사용 시 필수 | Model Provider + System Model |
| | 벡터 차원 · 최대 입력 토큰 | 1024 / 8192 | 〃 | 〃. **나중에 바꾸면 재인덱싱 필요** |
| **Rerank** | 엔드포인트 · 모델 이름 | `bge-reranker-v2-m3` | 선택 (권장) | 〃 |
| **Custom Tool** | API base URL | `https://monitoring-api.internal` | 필수 | Tools → Custom |
| | OpenAPI 3.0 스펙 | YAML/JSON | 필수 | 〃 |
| | 인증 방식과 키 (헤더 이름, Bearer/Basic, Query) | `X-API-Key: ...` | 필수 | 〃 |
| | 응답 크기 제한 파라미터 | `limit=100` | 권장 | 스펙에 포함 |
| **MCP** | 서버 URL (HTTP 방식) | `https://mcp.internal/monitoring/mcp` | MCP 사용 시 필수 | Tools → MCP |
| | Server ID (영소문자·숫자·`_`·`-`, 24자 이내) | `monitoring_mcp` | 〃 | 〃 |
| | 인증 (헤더 또는 OAuth) | | 〃 | 〃 |
| **네트워크** | Dify → LLM / Embedding 엔드포인트 | | 필수 | 방화벽 |
| | Dify → 자체 API / MCP 서버 (**ssrf_proxy 허용 설정**) | 사설 IP 대역 | 필수 | `ssrf_proxy` Squid 설정 + 방화벽 |
| | 오케스트레이터 → Dify API | | 필수 | 방화벽 |
| **앱 (Workflow)** | 입력 변수 목록 · 출력 JSON Schema · 시스템 프롬프트 · 조치 ID 목록 | [01 §3](01_architecture.md) | 필수 | 앱 편집기 |
| **연동** | 앱 API Key | `app-...` | 필수 | 앱 → API Access. 오케스트레이터 Vault에 보관 |
| | Knowledge API Key (문서 자동 등록 시) | `dataset-...` | 선택 | Knowledge → API |
| | `user` 식별자 규칙 · 타임아웃 · 재시도 | `system:order-api`, 60초 | 필수 | 오케스트레이터 설정 |

## A. Dify 환경

- [x] Dify 배포 형태 → **Self-hosted** (2026-10-21)
- [ ] 설치 버전 결정 및 기록 (Docker Compose / Kubernetes 중 설치 방식 포함). **1.14 이상 권장** (Human Input 노드 + HITL Service API), 1.15 이상이면 `difyctl` 사용 가능. 2026-10 기준 최신 태그는 **1.17.1**
- [ ] Human Input을 Email 방식으로 쓴다면 Dify SMTP 설정 (기존 메일 서버 릴레이 사용 가능 여부)
- [ ] 폐쇄망이면 플러그인(모델 공급자, Agent Strategy) 오프라인 설치 패키지(.difypkg) 확보
- [ ] Self-hosted 인프라 준비: 서버 사양, PostgreSQL, Redis, 벡터 DB(Weaviate/pgvector 등), 파일 저장소
- [ ] 라이선스 확인 (단일 조직 사용, 자체 포탈 연동) → [01_architecture.md §2.3](01_architecture.md)
- [ ] 워크스페이스 및 본인 권한 확인 (앱 생성, Tool 등록, Knowledge 생성 권한)
- [ ] 개발 / 운영 워크스페이스 분리 여부 결정
- [ ] Self-hosted인 경우: Dify 서버에서 자체 API(로그·메트릭·조치 API)로 네트워크 연결이 되는지 확인
- [ ] Code 노드 샌드박스(dify-sandbox) 동작 여부 및 사용 가능한 Python 패키지 확인

## B. LLM 모델 공급자

- [ ] 사용할 모델 결정 (분석용 고성능 모델 / 분류용 경량 모델 구분 검토)
- [ ] Model Provider에 API Key 등록 (Settings → Model Provider)
- [ ] 사외 LLM으로 로그를 보내도 되는지 보안 검토 (호스트명, IP, 개인정보 마스킹 정책)
- [ ] 호출량·비용 상한 추정 (이벤트 발생 빈도 × 호출당 토큰)

## C. 외부 Tool (에이전트가 호출할 API)

에이전트가 맥락을 스스로 수집하려면 아래 API가 **OpenAPI(Swagger) 스펙으로 준비**되어 있어야 Dify Custom Tool로 등록할 수 있다.

| Tool | 용도 | API 존재 여부 | 스펙 | 인증 방식 |
|---|---|---|---|---|
| 메트릭 시계열 조회 | 이벤트 전후 N분 지표 | **있음** | ? | ? |
| 로그 조회 | 호스트·서비스·시간 범위별 에러 로그 | **있음** | ? | ? |
| 배포/변경 이력 조회 | 최근 배포, 설정 변경 | ? | ? | ? |
| 서비스 토폴로지 조회 | 연관 서비스 파악 | ? | ? | ? |
| Kubernetes 조회 | Pod 상태·재시작·로그·이벤트 (`kubectl get po` 수준) | k8s API 서버 | 작은 스펙 직접 작성 또는 조회 어댑터 ([06 §5.1](06_dify_agent_configuration.md)) | 읽기 전용 ServiceAccount 토큰 |
| Grafana 조회 (선택) | 배포 주석, 알림 상태, 대시보드 링크 | Grafana (있으면) | 공식 OpenAPI에서 필요한 작업만 추린 작은 스펙 ([06 §5.1](06_dify_agent_configuration.md)) | 서비스 계정 토큰 (Viewer) |
| 조치 실행 | 화이트리스트 조치 (승인 후에만) | ? | ? | ? |

- [ ] 기존 로그·메트릭 API의 OpenAPI 3.0 스펙 확보. 없으면 작성 (Dify Custom Tool은 OpenAPI 스키마를 넣어서 등록함)
- [ ] 기존 API 응답을 LLM이 읽기 좋은 형태로 줄이는 방법 결정: (1) 기존 API에 요약 파라미터 추가, (2) Tool 앞에 얇은 어댑터 API 추가, (3) Dify Code 노드에서 후처리
- [ ] Dify 서버에서 기존 API로 가는 네트워크 경로와 방화벽 허용
- [ ] **ssrf_proxy(Squid)가 사설 IP 대역 요청을 막는지 확인하고, 필요한 자체 API 대역만 허용** ([04 §2](04_dify_platform_structure.md))
- [ ] (선택, MCP를 쓸 때만) 여러 에이전트·AI 도구에서 같이 쓸 API라면 MCP 서버로 감싸는 방안 검토 (Dify는 HTTP 방식 MCP만 지원). 1단계는 Swagger API(Custom Tool)만으로 충분하다
  - [ ] MCP 서버를 만든다면 Streamable HTTP + 공식 SDK 사용. 설치한 Dify가 지원하는 MCP 프로토콜 버전과 호환되는지 확인 (2026-07-28 스펙에서 stateless로 크게 바뀜, [04 §6.2-1](04_dify_platform_structure.md))
  - [ ] stdio로만 되는 MCP 서버(예: Postgres)는 HTTP를 지원하는 서버로 바꾸거나 HTTP로 띄운다. (참고, 이번 범위 제외: LiteLLM MCP 게이트웨이로 HTTP 변환하는 방법도 있음. `LITELLM_ENABLE_MCP_STDIO=true`, Dify 전용 가상 키에 해당 서버만 허용, DB는 읽기 전용 계정 + Replica ([06 §5.1](06_dify_agent_configuration.md)))
- [ ] Tool 전용 인증 키 발급 (읽기 전용 / 조치용 분리)
  - Dify Custom Tool의 인증은 등록할 때 **미리 넣어 두는 고정 키**뿐이다: 없음 / 헤더(`Authorization`이나 직접 정한 헤더 이름, 접두어 Basic·Bearer·없음) / 쿼리 파라미터 (1.17.1 `core/tools/custom_tool/tool.py`)
  - OAuth나 만료되는 토큰(JWT 등)의 자동 갱신은 없다. 만료가 긴 서비스 키를 발급하거나, 앞단 게이트웨이가 토큰을 붙이게 한다
  - 키는 도구 공급자(스키마) 단위로 하나다. 모든 Agent 호출이 같은 서비스 계정으로 나가므로 "누가 조회했는지"는 `incident_id`와 포탈 기록으로 추적한다
  - 키를 교체하면 Dify 도구 설정도 바꿔야 한다. 교체 주기와 담당자를 정한다
  - **키 권한이 곧 Agent 사용자의 권한이 된다** ([01 §2.4.2-9](01_architecture.md)). 권한 그룹별로 Agent와 키를 나누고, 그룹별 허용 API 목록을 정리한다
- [ ] 응답 크기 제한 (로그 최대 줄 수, 페이로드 크기): LLM 컨텍스트 한도 고려
- [ ] **조치 실행 Tool은 Dify에 직접 등록하지 않는 방안 검토**: Dify는 조치 ID만 출력하고, 실제 실행은 오케스트레이터가 승인 후 수행

## D. Knowledge (RAG)

- [ ] 런북(장애 유형별 대응 절차) 문서 수집
- [ ] 과거 장애 보고서 수집 및 민감 정보 정리
- [ ] 조치 ID 정의서 (ID, 설명, 파라미터, 위험도, 승인 필요 여부)
- [ ] 시스템 구성도 / 서비스 의존 관계 문서
- [ ] Embedding 모델 결정 및 Knowledge 생성, 청크 전략 결정

## E. 프롬프트 · 출력 계약

- [ ] 시스템 프롬프트 확정 (Gemini 원문에서 정량 임계치 판정 규칙은 제거: [01_architecture.md §1.3](01_architecture.md))
- [ ] Workflow 입력 변수 목록 확정 ([01_architecture.md §3.1](01_architecture.md))
- [ ] 출력 JSON 스키마 확정 ([01_architecture.md §3.2](01_architecture.md)), Structured Output 사용 여부
- [ ] 심각도 분류 기준 문서화 (NORMAL / WARNING / CRITICAL 판정 예시)

## F. 연동 (오케스트레이터 · 기존 메일 · 포탈)

- [ ] 기존 메일 발송 시스템의 호출 방식 확인 (API / 메시지 큐 / DB insert)
- [ ] 메일 본문에 분석 요약(status, root_cause_summary, evidence)과 포탈 링크를 넣을 수 있는지 확인. 템플릿 수정 범위
- [ ] 기존 수신자 목록을 그대로 쓸지, 심각도별 수신자를 나눌지 결정
- [ ] 운영 포탈이 쓸 Dify Service API 목록 확정 (chat-messages, conversations, messages, workflow run, 실행 로그 조회)

- [ ] Dify 앱 API Key 발급 (앱별 발급, 저장 위치: Vault 또는 환경변수)
- [ ] 호출 방식 결정: blocking / streaming, 타임아웃, 재시도 정책
- [ ] Dify 장애 시 대체 동작 (레거시 알림만 발송)
- [ ] `user` 파라미터 규칙 (예: `system:<source_system>`): Dify 로그 추적용

## F-1. 메신저 승인

직접 구현한 메신저로 승인을 요청한다. 메신저는 **버튼과 콜백이 없고 링크는 넣을 수 있다** (2026-10-21 확인). 그래서 **유효기간이 있는 UUID 토큰 링크를 보내고, 포탈 승인 페이지에서 승인**한다. 설계는 [01 §3.3](01_architecture.md)에 있다.

메신저
- [x] 메신저 제품 → 직접 구현한 메신저
- [x] 버튼 / 콜백 → **없음**
- [x] 메시지에 링크 → **가능**
- [ ] 메시지 발송 API와 인증 방식 (봇 계정, 발송 API 스펙)
- [ ] 발송 대상 지정 방식: 개인(사번) / 그룹 채팅방
- [ ] 메시지 길이 제한, 줄바꿈과 서식 지원 여부
- [ ] 링크 미리보기(URL 사전 접속) 여부

승인 페이지 (포탈)
- [ ] SSO 적용 가능 여부. 토큰만으로는 승인되지 않게 로그인 사용자와 대상 승인자를 대조함
- [ ] 메신저 사용자 ↔ 사번 ↔ 승인 권한 매핑 (조직도 / 권한 DB)
- [ ] 승인 페이지에 보여줄 내용: 요약, 근거, 조치 ID와 파라미터, 남은 시간, 같은 이벤트의 다른 승인자 상태
- [ ] 모바일에서 열리는지 (메신저 앱 안의 브라우저 포함)

토큰 · 정책
- [ ] 토큰 생성 방식: CSPRNG 기반 UUID v4. DB에는 해시만 저장
- [ ] 심각도·조치별 유효기간 (예: CRITICAL 15분, WARNING 60분)
- [ ] 승인자가 여러 명일 때: 사람마다 토큰 발급, 먼저 한 결정 하나만 유효
- [ ] 위험도가 높은 조치는 2인 승인이 필요한지
- [ ] 만료 시 에스컬레이션 대상과 재발급 규칙
- [ ] 메신저 장애 시: 메일로 같은 링크 발송 (기존 메일 시스템)

## F-2. 알람 → Agent 채팅 (적용 1단계)

설계는 [01 §2.4](01_architecture.md)에 있다.

Agent
- [ ] 장애 유형별 1차 Agent 목록 (예: 앱 응답 지연, 리소스 과다, 배치 실패)
- [ ] 전문 Agent 목록 (예: DB, 네트워크, 미들웨어)과 전환 가능 관계
- [ ] 라우팅 표: `rule_id` / 서비스 → 1차 Agent
- [ ] Agent 형태: Agent v2([06](06_dify_agent_configuration.md)) / Chatflow. 각 Agent의 Service API Key 발급
- [ ] 인계 요약 형식 (전문 Agent로 넘길 때 무엇을 담을지)

오케스트레이터 API (Agent 도구로 등록)
- [ ] `get_incident(incident_id)`: 장애 정보 조회
- [ ] `request_action(incident_id, action_id, params, reason)`: 승인 대기 요청 생성. **실행하지 않음**
- [ ] `get_action_status(request_id)`: 조치 상태와 결과
- [ ] 위 API의 OpenAPI 스키마와 Agent 전용 인증 키 (조치 실행 권한 없음)

포탈 채팅 화면
- [ ] 채팅 링크 대상 결정: 포탈 채팅 화면(권장) / Dify Web App 직접(PoC 한정)
- [ ] SSO 적용, 장애 채팅 열람 권한 (장애 관계자만)
- [ ] `incident_id ↔ conversation_id` 저장, Service API `user` 규칙 (`incident-<incident_id>`)
- [ ] 스트리밍 응답(SSE) 표시, 대화 이력, 승인 카드, 전문 Agent 전환 버튼
- [ ] 발화자(SSO 사용자) 기록, 감사 로그
- [ ] Dify 장애 시 화면: 장애 정보와 "수동 대응" 안내만 표시

메신저 알람
- [ ] 알람 메시지 형식: 요약 한두 줄 + 채팅 링크 (상세 정보는 링크 안에서만)
- [ ] 알람 대상: 개인 / 장애 채팅방. 조치 결과를 같은 곳에 다시 보낼지
- [ ] 초기 분석을 알람과 동시에 돌릴지, 첫 질문 때 돌릴지

## G. 테스트 · 평가 데이터

- [ ] 과거 실제 장애 이벤트 샘플 (입력 payload + 그때 실제 원인 + 실제 조치) 최소 10건
- [ ] 정상인데 임계치만 넘은 오탐 사례 샘플
- [ ] 평가 기준: 원인 일치율, 조치 ID 정확도, 응답 시간, 호출당 비용

## H. 운영 · 거버넌스

- [ ] Dify 앱 버전 관리 방식 (DSL export를 이 저장소에 커밋)
- [ ] 프롬프트 변경 시 리뷰·승인 절차
- [ ] 감사 로그: 누가 어떤 조치를 승인했는지
- [ ] Dify 백업: **PostgreSQL과 파일 저장소를 함께** 백업 (자격증명 복호화용 개인키가 파일 저장소에 있음, [05 §3.2](05_dify_db_schema.md))
- [ ] Dify DB와 백업 파일 접근 권한 관리 (앱 API Key가 평문으로 저장됨, [05 §3.3](05_dify_db_schema.md)). 호출 주체별로 키를 분리하고 주기적으로 교체
- [ ] 실행 로그(`workflow_runs`, `workflow_node_executions`) 보관 기간과 정리 정책
- [ ] Agent Secret 환경 변수가 DB(`agent_config_snapshots.config_snapshot`)에 평문으로 남는지 설치본에서 확인 ([05 §3.6](05_dify_db_schema.md))
- [ ] 모니터링 대상: Dify 자체 응답 시간, 실패율, 토큰 사용량

---

## 열린 결정

- [x] **승인 상태를 어디서 관리할지** → **(나) 오케스트레이터 DB** (결정 로그 참고)
  - (가) Dify Human Input 노드: 워크플로가 멈춘 채 대기한다. Human Input의 전달 방식은 Email과 Web app만 있어서, 메신저로 승인하려면 Web app 방식을 쓰고 우리 백엔드가 `form_token`을 받아 메신저 카드를 보내고 콜백이 오면 HITL API로 제출해야 한다. 메신저 연동은 어차피 직접 만들어야 하고, Dify와 메신저 사이의 상태를 맞추는 일만 더 늘어난다.
  - (나) 오케스트레이터 DB: Dify는 분석 결과를 출력하고 끝난다. 오케스트레이터가 메신저 카드 발송, 콜백, 만료, 감사 로그를 한곳에서 처리한다. 엔진과 독립적이다.
  - 어느 쪽이든 실제 조치 실행은 오케스트레이터가 화이트리스트로 검증한 뒤에 함

- [ ] **채팅 링크 대상** (권장: 포탈 채팅 화면)
  - (W) Dify Web App 직접: 개발이 없지만 Self-hosted Web App은 URL만 알면 누구나 접속 가능(접근 제어는 Enterprise). 사용자 식별·승인·감사 불가
  - (P) 포탈 채팅 화면: SSO, 장애 정보·대화·승인 카드를 한 화면에. 채팅 화면 개발 필요

- [x] **LLM·MCP를 LiteLLM 경유로 붙일지** → **이번 범위에서 제외** (2026-10-22). LLM과 MCP는 Dify에 직접 연결한다. 아래는 나중에 검토할 때를 위한 참고
  - 겹치는 부분: 모델 공급자 키 관리, 사용량 기록은 Dify에도 있다
  - LiteLLM이 더하는 것: Dify 밖의 사용처(포탈, 다른 도구)까지 한곳에서 키·예산·사용량 관리, 모델 간 대체(fallback), 내부 모델과 외부 API 전환, 외부 반출 전 마스킹(guardrail), stdio MCP의 HTTP 변환
  - 비용: 설정 위치가 둘이 되고, 거치는 곳이 하나 늘어 장애점이 됨. Dify에서는 "OpenAI 호환" 공급자로 등록하므로 모델 기능(Function calling, Vision, Structured output, 컨텍스트 길이)을 직접 맞게 선언해야 함
  - 판단 기준: LLM을 Dify 하나만 쓰고 공급자도 하나면 직접 연결, 여러 곳에서 쓰거나 조직 단위 통제가 필요하면 LiteLLM

## 결정 로그

| 날짜 | 결정 | 근거 |
|---|---|---|
| 2026-10-21 | 정량 임계치 판정은 규칙 엔진(코드)에서 하고 LLM은 이벤트 발생 시에만 호출 | 정확성과 비용 |
| 2026-10-21 | LLM은 조치 ID만 출력하고 자유 형식 명령은 금지 | 안전성 |
| 2026-10-21 | ~~1차 범위는 Dify Workflow, 대화형 Agent는 2차~~ (아래 결정으로 변경) | 입력·출력이 고정된 단발 분석이 먼저 필요 |
| 2026-10-21 | Dify는 Self-hosted 전제. 권장 구성은 Dify 엔진 + Service API 기반 운영 포탈 (방안 C, 최종 결정 전) | 엔진 기능은 그대로 쓰고 운영 화면만 직접 만들 수 있음 |
| 2026-10-21 | 기존 로그·메트릭 조회 API와 메일 발송 시스템은 재사용 | 이미 구축되어 있음 |
| 2026-10-21 | 포탈은 Dify 콘솔 내부 API를 쓰지 않음. 에이전트 등록·수정은 Dify 콘솔에서 | 콘솔 API는 공식 계약이 아니어서 업그레이드 시 깨질 수 있음 |
| 2026-10-21 | 승인 요청 채널은 직접 구현한 메신저. 메일은 알림과 대체 경로로 유지 | 사용자 결정 |
| 2026-10-21 | 메신저에 버튼·콜백이 없으므로 유효기간 UUID 토큰 링크 → 포탈 승인 페이지(SSO)에서 승인. 링크를 여는 것만으로는 상태가 바뀌지 않고, 결정은 POST로만 함 | 메신저 기능 제약. 링크가 유출되거나 미리보기로 열려도 안전하게 하기 위함 |
| 2026-10-21 | 승인 상태는 오케스트레이터 DB에서 관리 (Dify Human Input 미사용, 1차) | 메신저 연동을 직접 만들어야 하므로 상태를 한곳에 둠 |
| 2026-10-21 | 에이전트 정의의 원본은 Git의 DSL. 운영 반영은 `difyctl import studio-app` 사용. 콘솔 내부 API와 Dify DB를 직접 쓰는 연동은 만들지 않음 | 공식 등록 API가 없음 (issue #27795 not planned). difyctl은 공식 CLI |
| 2026-10-21 | 적용 1단계: 메신저 알람 → 해당 Agent 채팅으로 이동 → 채팅으로 상황 파악 → 해당 Agent 또는 연결된 전문 Agent 채팅으로 해결. Workflow 분석은 초기 분석(선택)으로 사용 | 사용자 결정 |
| 2026-10-21 | 채팅에서 해결하더라도 Agent는 `request_action`으로 요청만 하고, 실행은 SSO 사용자의 승인(POST) 뒤 오케스트레이터가 함 | 설계 원칙 유지 (LLM 출력만으로 실행 금지) |
| 2026-10-22 | LiteLLM(LLM·MCP 게이트웨이)은 이번 범위에서 제외. LLM과 MCP는 Dify에 직접 연결. 방법과 판단 기준만 참고로 기록 | 범위 축소 (사용자 결정) |
