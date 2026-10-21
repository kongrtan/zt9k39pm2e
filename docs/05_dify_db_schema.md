# Dify DB 스키마 (등록 관련)

> 상태: 초안 (2026-10-21)
> 출처: Dify 소스 `api/models/*.py` (SQLAlchemy ORM), **태그 1.17.1** (2026-09-10) 기준으로 직접 추출
> 관련: [04 플랫폼 구조 §3](04_dify_platform_structure.md)
>
> **이 문서는 이해를 돕기 위한 참고용이다.** 테이블과 컬럼은 버전마다 바뀌고(마이그레이션 220개 이상), 공식 계약이 아니다. 이 DB를 직접 조회하거나 수정하는 연동은 만들지 않는다 ([02 결정 로그](02_dify_agent_prerequisites.md)).

---

## 1. 등록 단계별로 저장되는 테이블

| 등록 단계 ([03](03_dify_agent_registration_guide.md)) | 테이블 | 저장 내용 |
|---|---|---|
| 워크스페이스 | `tenants` | 워크스페이스. `encrypt_public_key`(자격증명 암호화용 공개키) |
| ① 모델 공급자 | `providers` | 워크스페이스별 공급자 (`provider_name`, 유효 여부, 현재 사용 중인 자격증명 `credential_id`) |
| | `provider_credentials` | 공급자 자격증명 (`encrypted_config`: 엔드포인트, API Key 등) |
| | `provider_models`, `provider_model_credentials` | 직접 추가한 모델(OpenAI 호환 등)과 모델별 자격증명 |
| | `tenant_default_models` | System Model Settings (기본 LLM / Embedding / Rerank) |
| ② Custom Tool | `tool_api_providers` | OpenAPI 스키마 원문(`schema`), 파싱된 Tool 목록(`tools_str`), 인증 정보(`credentials_str`) |
| ② MCP | `tool_mcp_providers` | `server_url`, `server_identifier`, `encrypted_headers`, `encrypted_credentials`, `timeout`, `sse_read_timeout`, 가져온 Tool 목록(`tools`) |
| ③ Knowledge | `datasets` | Knowledge 설정: `embedding_model`, `embedding_model_provider`, `indexing_technique`, `retrieval_model`(JSON) |
| | `documents` | 업로드한 문서와 처리 상태 (`indexing_status`, 단계별 완료 시각, 토큰 수) |
| | `document_segments` | 청크 텍스트(`content`)와 벡터 DB 노드 ID(`index_node_id`) |
| | `dataset_collection_bindings` | 어떤 Embedding 모델이 어떤 **벡터 DB 컬렉션**에 대응하는지 |
| | `upload_files` | 원본 파일 메타데이터. 실제 파일은 파일 저장소의 `key` 경로에 있음 |
| ④ 앱 생성 | `apps` | 앱 기본 정보: `mode`(workflow / advanced-chat / agent-chat 등), `workflow_id`, `enable_site`, `enable_api` |
| ⑤ 노드 구성 | `workflows` | **워크플로 그래프 전체**(`graph`, JSON 텍스트), 환경변수, `version` |
| | `app_dataset_joins` | 앱 ↔ Knowledge 연결 |
| ⑦ 게시 | `workflows` | 게시할 때마다 행이 하나씩 추가됨 (아래 §3) |
| | `api_tokens` | 앱 API Key (`type`=app, `app_id`) 또는 Knowledge API Key (`type`=dataset) |
| | `sites` | Web App 설정 (`code` = 공개 URL 경로, 제목, 테마, 사용자 지정 도메인) |
| | `app_mcp_servers` | 앱을 MCP 서버로 공개할 때 (`server_code` = URL 경로, `status`) |
| | `tool_workflow_providers` | Workflow를 Tool로 게시할 때 |
| 실행 | `workflow_runs` | 실행 1건: `inputs`, `outputs`, `status`, `elapsed_time`, `total_tokens` |
| | `workflow_node_executions` | 노드별 실행 결과: `node_type`, `inputs`, `outputs`, `process_data`, `elapsed_time` |
| | `workflow_app_logs` | 앱 로그 목록 (`created_from`: service-api / web-app 등) |
| | `end_users` | API의 `user` 파라미터 값(`session_id`)과 Web App 사용자 |

> 2차(Chatflow / Agent)에서는 `conversations`, `messages`, `message_agent_thoughts` 테이블에 대화와 Agent의 Tool 호출 과정이 저장된다.

---

## 2. 관계도 (주요 컬럼만)

```mermaid
erDiagram
    tenants ||--o{ apps : "has"
    tenants ||--o{ providers : "has"
    tenants ||--o{ provider_credentials : "has"
    tenants ||--o{ tenant_default_models : "has"
    tenants ||--o{ tool_api_providers : "has"
    tenants ||--o{ tool_mcp_providers : "has"
    tenants ||--o{ datasets : "has"

    providers }o--|| provider_credentials : "credential_id"

    apps ||--o{ workflows : "app_id (draft + 게시 버전들)"
    apps |o--|| workflows : "workflow_id (현재 게시 버전)"
    apps ||--o{ api_tokens : "app_id"
    apps ||--o| sites : "app_id"
    apps ||--o| app_mcp_servers : "app_id"
    apps ||--o{ app_dataset_joins : "app_id"
    datasets ||--o{ app_dataset_joins : "dataset_id"

    datasets ||--o{ documents : "dataset_id"
    documents ||--o{ document_segments : "document_id"
    datasets }o--o| dataset_collection_bindings : "collection_binding_id"

    workflows ||--o{ workflow_runs : "workflow_id"
    workflow_runs ||--o{ workflow_node_executions : "workflow_run_id"
    workflow_runs ||--o| workflow_app_logs : "workflow_run_id"

    tenants {
        uuid id PK
        string name
        text encrypt_public_key
    }
    providers {
        uuid id PK
        uuid tenant_id FK
        string provider_name
        bool is_valid
        uuid credential_id FK
    }
    provider_credentials {
        uuid id PK
        uuid tenant_id FK
        string provider_name
        string credential_name
        text encrypted_config
    }
    tenant_default_models {
        uuid id PK
        uuid tenant_id FK
        string provider_name
        string model_name
        enum model_type
    }
    tool_api_providers {
        uuid id PK
        uuid tenant_id FK
        string name
        text schema "OpenAPI 원문"
        text tools_str
        text credentials_str
    }
    tool_mcp_providers {
        uuid id PK
        uuid tenant_id FK
        string server_identifier
        text server_url
        text encrypted_headers
        text tools
        float timeout
    }
    apps {
        uuid id PK
        uuid tenant_id FK
        string name
        enum mode
        uuid workflow_id FK
        bool enable_site
        bool enable_api
    }
    workflows {
        uuid id PK
        uuid app_id FK
        string version "draft 또는 게시 시각"
        text graph "노드·엣지 JSON"
        text environment_variables
    }
    api_tokens {
        uuid id PK
        uuid app_id FK
        uuid tenant_id FK
        enum type "app / dataset"
        string token "app-... (평문)"
        datetime last_used_at
    }
    sites {
        uuid id PK
        uuid app_id FK
        string code "Web App URL 경로"
    }
    app_mcp_servers {
        uuid id PK
        uuid app_id FK
        string server_code
        enum status
    }
    datasets {
        uuid id PK
        uuid tenant_id FK
        string embedding_model
        enum indexing_technique
        json retrieval_model
    }
    documents {
        uuid id PK
        uuid dataset_id FK
        string name
        enum indexing_status
    }
    document_segments {
        uuid id PK
        uuid document_id FK
        text content
        string index_node_id "벡터 DB 노드 ID"
    }
    workflow_runs {
        uuid id PK
        uuid workflow_id FK
        text inputs
        text outputs
        enum status
        float elapsed_time
        bigint total_tokens
    }
    workflow_node_executions {
        uuid id PK
        uuid workflow_run_id FK
        string node_id
        string node_type
        text inputs
        text outputs
        enum status
    }
```

---

## 3. 알아두면 좋은 동작

### 3.1 초안과 게시 버전 (`workflows`)
- 편집기에서 수정하면 `version = 'draft'`인 행 **하나**가 계속 갱신된다.
- **Publish**를 누르면 그래프를 복사해서 `version = 게시 시각 문자열`인 **새 행**을 만들고, `apps.workflow_id`가 이 행을 가리키게 바뀐다.
- Service API는 `apps.workflow_id`가 가리키는 게시 버전을 실행한다. 그래서 편집 중인 초안은 운영 호출에 영향을 주지 않는다.
- 이전 게시 버전이 행으로 남아 있으므로 콘솔에서 버전 이력을 보고 되돌릴 수 있다.

### 3.2 자격증명 암호화
- LLM API Key, Tool 인증 정보, MCP 헤더 같은 비밀값은 **워크스페이스별 RSA 키 + AES**로 암호화해서 저장한다.
- 공개키는 `tenants.encrypt_public_key`에, **개인키는 파일 저장소의 `privkeys/<tenant_id>/private.pem`**에 있다 (`api/libs/rsa.py`).
- **백업할 때 PostgreSQL과 파일 저장소를 반드시 같이 백업한다.** 파일 저장소를 잃어버리면 DB가 남아 있어도 등록한 자격증명을 모두 다시 입력해야 한다.

### 3.3 앱 API Key는 평문으로 저장된다
- `api_tokens.token`에는 `app-` + 랜덤 24자가 **해시 없이** 저장되고, 조회 속도를 위해 Redis에도 캐시된다 (`controllers/console/apikey.py`, `controllers/service_api/wraps.py`).
- 따라서 **DB나 백업 파일에 접근할 수 있으면 API Key도 볼 수 있다.** DB 접근 권한과 백업 파일을 관리하고, 키는 주기적으로 교체한다.
- 앱마다 키를 여러 개 발급할 수 있다. 오케스트레이터용과 포탈용처럼 **호출하는 주체별로 키를 나누면** 키 하나를 폐기해도 다른 쪽에 영향이 없다.

### 3.4 실행 로그 용량
- `workflow_runs`와 `workflow_node_executions`의 `inputs`와 `outputs`에는 **전체 내용이 텍스트로 저장된다.** 로그 수백 줄을 Tool로 가져오면 그 내용이 실행할 때마다 DB에 쌓인다.
- 보관 기간과 정리 정책을 정하고, 로그 마스킹은 Code 노드에서 **LLM에 넘기기 전에** 한다 (마스킹 전 원문은 Tool 노드의 출력으로 저장되므로, 민감 정보가 많다면 자체 API 쪽에서 마스킹하는 것이 더 안전하다).

### 3.5 Dify DB에 없는 것
- **플러그인 설치 정보**는 `plugin_daemon`이 별도의 DB에 저장한다 (Docker Compose 기본 설정에서는 같은 PostgreSQL 서버의 별도 데이터베이스. 설치본의 `.env`에서 확인).
- **벡터**는 Vector DB에, **원본 파일과 개인키**는 파일 저장소에 있다.

---

## 4. 설치본에서 실제 스키마 확인하기

버전마다 다르므로, 정확한 스키마는 설치한 DB에서 직접 뽑는다. (읽기 전용으로만 사용)

```bash
# 테이블 목록
docker compose exec db_postgres psql -U postgres -d dify -c '\dt'

# 특정 테이블 구조
docker compose exec db_postgres psql -U postgres -d dify -c '\d workflows'

# 전체 스키마를 파일로 (데이터 제외)
docker compose exec db_postgres pg_dump -U postgres -d dify --schema-only > dify_schema_$(date +%Y%m%d).sql

# 현재 마이그레이션 버전
docker compose exec db_postgres psql -U postgres -d dify -c 'select * from alembic_version'
```

> 서비스 이름(`db_postgres`), 사용자, DB 이름은 설치본의 `docker-compose.yaml`과 `.env`에 맞게 바꾼다.

---

## 변경 이력

| 날짜 | 내용 |
|---|---|
| 2026-10-21 | 초안 작성. 1.17.1 소스 기준 등록 관련 테이블, ERD, 암호화·API Key 저장 방식 |
