---
name: incident-triage
description: 모니터링 알람으로 열린 장애 채팅에서 운영자가 "지금 상태가 어때?", "언제부터야?", "원인이 뭐야?"처럼 상황 파악을 요청하거나, 메트릭 조회 결과를 해석해야 할 때 사용한다. 정해진 순서로 장애를 1차 분석하고, 메트릭 변화를 계산하고, 화이트리스트 안에서만 조치를 추천한다.
compatibility: Python 3.8 이상 (표준 라이브러리만 사용). 조회 도구 get_incident, query_metrics, search_logs가 Agent에 연결되어 있어야 한다.
metadata:
  project: ai-agent-portal-poc
  version: "0.1"
---

# 장애 1차 분석 (incident-triage)

알람으로 열린 장애 1건을 정해진 순서로 분석해서 운영자에게 보고한다.
조치는 **추천과 요청까지만** 한다. 직접 실행하지 않는다.

## 1. 분석 순서

반드시 이 순서를 지킨다. 앞 단계 결과가 없으면 다음 단계로 넘어가지 않는다.

1. **장애 정보 확인**: `get_incident`로 장애 정보를 조회한다.
   - 확인할 것: `rule_id`, 대상 서비스와 호스트, 감지 시각(`detected_at`), 스냅샷
2. **메트릭 확인**: `query_metrics`로 감지 시각 **전 30분 ~ 현재**를 조회한다.
   - 조회 결과를 `metrics.json`으로 저장한 뒤 아래 스크립트로 요약한다.
     ```bash
     python scripts/summarize_metrics.py metrics.json --event-time <detected_at>
     ```
   - 스크립트가 계산한 숫자(기준값, 최고값, 변화율, 임계치 초과 시작 시각과 지속 시간)를 그대로 쓴다. **숫자를 직접 추정하지 않는다.**
3. **로그 확인**: `search_logs`로 같은 시간대의 `ERROR`, `FATAL` 로그를 조회한다.
   - 메시지별 건수와 처음 나온 시각만 정리한다. 로그 원문은 3줄 이내로 인용한다.
4. **변경 이력 확인**: 배포 이력 도구가 있으면 감지 시각 전 2시간 동안의 배포를 확인한다. 도구가 없으면 "배포 이력 확인 불가"라고 적는다.
5. **과거 사례 확인**: 연결된 지식 검색에서 같은 `rule_id`나 비슷한 증상의 과거 장애와 런북을 찾는다.
6. **판단**: 원인 추정과 확신도를 정한다. 판단 기준은 [references/judgement-guide.md](references/judgement-guide.md)를 따른다.
7. **보고**: [assets/triage-report.md](assets/triage-report.md) 형식으로 답한다.

## 2. 조치 추천 규칙

- 조치 ID는 [references/action-whitelist.md](references/action-whitelist.md)에 있는 것만 쓴다. 목록에 없는 조치나 셸 명령은 만들지 않는다.
- 맞는 조치가 없거나 확신도가 0.5 미만이면 `NONE`을 추천하고, 운영자가 확인할 항목을 적는다.
- 운영자가 조치 진행을 요청하면 `request_action`을 호출한다. 이 호출은 **승인 대기 요청을 만들 뿐 실행하지 않는다.** 답변에서 "실행했다"고 말하지 않는다.
  - 올바른 답: "RESTART_SERVICE 요청을 등록했습니다. 화면의 승인 카드에서 승인하면 실행됩니다."
- 승인 후 결과는 `get_action_status`로 확인해서 알려준다.

## 3. 답변 원칙

- 첫 줄에 **한 문장 요약**을 쓴다. 예: "order-api CPU가 10:40 배포 직후부터 92%로 올라 15분째 지속 중입니다."
- 사실(조회 결과)과 추정(판단)을 구분해서 쓴다. 추정에는 "추정"이라고 붙인다.
- 근거로 쓴 조회 결과는 시각과 값을 함께 적는다.
- 모르는 것은 모른다고 쓰고, 무엇을 조회하면 알 수 있는지 제안한다.

## 4. 이 스킬을 쓰지 않는 경우

- 다른 Agent로 넘기는 인계 요약을 만들 때: `incident-handoff` 스킬을 쓴다.
- 장애와 관계없는 일반 질문.
