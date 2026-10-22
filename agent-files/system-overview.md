# 주문·결제 시스템 구성 개요

> 이미지(`system-overview.png`)를 함께 올리더라도, Agent가 읽을 수 있도록 **같은 내용을 텍스트로** 둔다.

## 요청 흐름

```text
사용자 → L4 → order-api (3대) → order-db (Primary/Replica)
                            ├→ cache-svc (Redis)
                            └→ payment-api (2대) → payment-db
                                                 └→ ext-pg-gateway → 외부 결제대행사
정산: batch-settle (매일 02:00~04:00) → order-db, payment-db 읽기
```

## 알아둘 점

| 항목 | 내용 |
|---|---|
| 정기 작업 | `batch-settle`가 매일 02:00~04:00에 DB를 많이 읽는다. 이 시간대 DB 부하 알람은 배치 영향을 먼저 의심한다 |
| 배포 시간 | 정기 배포는 평일 10:00~11:00. 이 시간대 알람은 배포 이력을 먼저 확인한다 |
| 단일 장애점 | `ext-pg-gateway`는 1대다. 결제 타임아웃이 몰리면 이쪽을 먼저 의심한다 |
| 캐시 | `cache-svc` 장애 시 `order-api`가 DB로 직접 조회해서 `order-db` 부하가 같이 오른다 |
| 용량 | `order-api` 평시 TPS 1,500 내외, 행사 기간 최대 5,000 |
