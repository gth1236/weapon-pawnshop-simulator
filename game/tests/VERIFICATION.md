# UI 개편 검증 — 2026-10-03

엔진: Godot `4.6.1.stable.official.14d19694e`, Windows x64.
렌더링: OpenGL Compatibility, NVIDIA RTX 4060, 1920×1080.

## 결과

- Headless editor import: parse/missing-resource 오류 없이 완료.
- 규칙·Python 기준 대조: **14,200 checks / 0 failures**.
- 확장 UI smoke: **722 checks / 0 failures**, 실제 렌더링 포함.
- Python 기존 회귀 테스트: **90 tests passed** (`-B`, 기존 테스트/소스 수정 없음).
- 원본 및 runtime balance SHA-256 일치:
  `6A3EDDDF11FC44784D4D7C353F7B390FFAB1A808940A7A08C982711C40DF5436`.
- 기존 simulator/tests/output/config 및 루트 README의 git diff 없음.
- commit/push 없음.

## 규칙 및 대조 검증

시작 현금/부채/슬롯, 수동 확장, 최대 용량, 잔액 부족, 매입/거절/판매,
고물상 50% 반올림 및 평판/거래 통계 제외, 8명 종료, 20개 seed 전체 하루,
1,000개 seed 방문 순서, 1,000개 생성 무기 도메인을 검사했습니다.
8번째 손님은 1,000개 seed 중 판매 손님 491회입니다.
기본 seed의 거래 수는 이제 플레이어의 예상 가격 제안과 흥정 결과에 따라 달라집니다.

128개 Python 사례에서 실제 가격/요구 가격, buyer fit 각 성분, 거래 결과,
평판, progression을 비교합니다. 성공 판매 57개와 실패 사례를 포함합니다.
**이번 Godot 데모에서 제외한 특수 속성 기여만 메모리상의 Python config에서
0으로 둔 조건부 대조입니다.** 원본 config와 simulator는 수정하지 않았으며,
특수 기여가 있는 원래 Python 가격과 동일하다고 주장하지 않습니다.

검증 중 3개 사례에서 드러난 float 경계 가격 차이는 compensated sum과
정확한 ties-to-even 분기 처리로 수정했습니다. 기준 런타임은 Python 3.12.14입니다.

## 상호작용 및 레이아웃

- 실제 메인 scene 생성 및 감정하기 버튼에 포인터 이벤트 전달.
- 감정 전 판단/체크 비활성, 도구 지연 후 정확한 공개.
- 공개만/판단만 했을 때 가격 불변, 체크 후 반영, 체크 해제 시 제외.
- 잘못 선택한 플레이어 등급도 반영하며 true price는 불변.
- 실제 공개값을 바꿔도 동일 판단의 예상 기여는 바뀌지 않음.
- 화면 재진입 및 보유 재고 감정에서도 판단/체크 유지.
- 감정 도중 복귀 시 늦게 도착하는 reveal 취소.
- 특수 속성 및 시장 표시/체크 제거.
- 기본·상위 능력치 별도 판단, 5개 감정 항목 유지.
- 매입/거절, 재고 진입, 잠긴 슬롯/확장, 고물상 확인, 구매자 응대, 자동 정산.
- 표시 중인 Label/Button의 영문 누출 및 viewport 경계 검사.
- 스크롤 컨테이너 없음.
- 재고 20칸 모두 채운 화면, 능력치 7줄 무기의 공개 정보와 감정 행 겹침 검사.

생성·직접 확인한 로컬 캡처 (Git ignore):
`main_play.png`, `appraisal_before.png`, `appraisal_judged.png`,
`inventory_slots.png`, `inventory_full.png`, `appraisal_full_stats.png`,
`daily_receipt.png` — 모두 `game/tests/`에 있습니다.

자동 줄바꿈 Label이 처음의 좁은 폭으로 계산한 높이를 유지하는 문제를 수정했습니다.
초기 크기를 지정하고 최종 폭 적용 후 재배치하여 실제 control 경계도 화면 안에 유지합니다.

## 알려진 한계

현재 검증에서 진행을 막는 parse/runtime/레이아웃 문제는 발견되지 않았습니다.
실제 아트/효과/사운드, 저장/불러오기, 다일차, export 검증은 없습니다.
대표 등급 매핑은 임시 판단용이고 시스템 한글 폰트를 사용합니다.
OS별 폰트 fallback과 다양한 화면 배율은 별도 배포 검증이 필요합니다.

Sandbox 최초 import의 사용자 설정/cache 접근 제한은 승인된 실행으로 해결했으며,
최종 검증에는 해당 환경 오류가 없습니다.

## 항목별 판단 / seller negotiation 후속 검증

- 별도 흥정 검증: **79 checks / 0 failures**.
- 고유 3개/증폭 8개 모든 판정값의 예상 기여를 기존 가격표와 비교.
- 목적별 제안 횟수, 요구가 이상 즉시 수락, 5% counter와 요구가 유지 분기.
- 실제 scene 버튼을 통해 낮은 제안 → 대사/현재 요구가/남은 횟수 표시 → 판단 및
  체크 조정 → 재제안 → 수락까지 검증.
- 두 번의 낮은 제안 → 결렬, 중복 클릭 방지, 자금 부족 시 횟수 유지,
  화면 재진입 시 흥정 보존, 8번째 seller 결렬 시 자동 영수증 확인.
- 원가/현금/평판/고물상 기준이 요구가가 아닌 실제 수락된 제안가임을 확인.
- 가격/구매자/재고/정산 기존 규칙 검증 14,200개도 통과.
- 원본 Python 파일, tests, output, config는 수정하지 않음. commit/push 없음.

