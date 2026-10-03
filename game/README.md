# 무기 전당포 — 첫날 플레이 및 한국어 UI

Godot **4.6.1 stable**, GDScript 전용 프로젝트입니다. `scenes/main.tscn`을 진입점으로
사용하며 Python을 게임 실행 중 호출하지 않습니다. Python simulator, 기존 tests,
output, config 및 저장소 루트 README는 수정하지 않았습니다.

## 실행

Godot 4.6.1에서 `game/project.godot`을 Import한 뒤 **F5**를 누르세요.
기준 화면은 **1920×1080**이고 viewport stretch와 keep aspect로 작은 창에서도
같은 배치를 비율 유지하여 표시합니다. 모든 플레이어 문구는 한국어입니다.

저장소 루트에서 로컬 엔진으로 실행할 수도 있습니다.

```powershell
& './game/tools/godot/Godot_v4.6.1-stable_win64.exe' --path game
& './game/tools/godot/Godot_v4.6.1-stable_win64.exe' --path game -- --seed=12352
```

기본 재현 번호는 12352입니다. 매입 여부와 실제 지출은 플레이어가 선택한 예상 가격과
손님의 수락 여부에 따라 달라집니다. 판매 성공을 강제하거나 손님을 재추첨하지
않습니다. 다른 번호에서는 재고와 적합도에 따라 구매자가 그냥 떠날 수 있습니다.
Godot과 Python은 RNG가 다르므로 같은 번호가 두 구현의 같은 무기를 뜻하지 않습니다.

## 스케치에 따른 화면 구조

- **메인**: 좌상단 날짜·자금·평판·재고, 중앙 왼쪽 손님 초상 영역, 아래 손님 이름과
  대화창, 오른쪽 무기 테이블과 감정하기, 우상단 재고 버튼입니다.
- **감정**: 별도 전체 화면입니다. 왼쪽 무기 이미지와 손님의 말, 중앙 이름·종류·직업·
  등급·공개 수치 및 7개 항목, 오른쪽 가치 판단과 요구 가격·예상 가격·거래 버튼입니다.
- **재고**: 두 보관 테이블 위에 10칸씩 총 20칸을 배치합니다. 시작 10칸은 열려 있고
  나머지는 잠겨 있습니다. 중앙에 선택 무기의 매입가·현재 감정가·획득일·능력치와
  상세 감정/고물상 버튼이 있습니다. 좌상단 복귀, 우상단 수동 확장입니다.
- **정산**: 손님 8명 응대 후 한 화면 정산서로 전환합니다. 수익·원가·손실·확장비와
  거래 횟수를 구분하며 스크롤이 필요 없습니다.

실제 아트 대신 Control/Panel/Label/Button을 사용합니다. 세로 ScrollContainer는
제거했습니다. `main.tscn`의 진입 scene는 그대로이고 화면 계층은 각 UI 스크립트에서
생성합니다. 기존 데이터/시스템/컨트롤러/UI 책임 구분은 유지합니다.

## 감정 → 판단 → 가격 반영

1. 메인에서 무기 또는 **감정하기**를 누릅니다.
2. 기본/상위 능력치와 모든 concrete 숫자는 처음부터 공개됩니다.
3. 고유 속성·강화·제련·증폭·안정도는 중앙의 해당 항목을 클릭하면 0.3초 동안
   도구로 확인하는 문구가 표시되고 정확한 결과를 공개합니다.
4. 공개된 항목을 클릭하면 오른쪽에서 항목별 판단을 선택합니다. 강화/제련/안정도와 기본/상위 능력치는
   **낮음 / 무난 / 좋음 / 매우 좋음**, 고유 속성은 **없음 / 있음 / 높음**,
   증폭은 **미적용 / 0줄 / 1줄 낮음 / 1줄 높음 / 2줄 낮음 / 2줄 높음 / 3줄 낮음 / 3줄 높음**입니다.
5. 그 항목 옆 **가격 반영**을 체크해야 예상 가격에 들어갑니다.
6. **이 가격으로 매입 제안** 또는 **매입 거절**을 선택합니다. 제안 버튼은 현재
   예상 가격을 전달합니다. 거절 후 기회가 남으면 판단과 체크를 조정해 재제안할 수 있습니다. 감정 화면을 나갔다 돌아와도
   감정 지식과 판단·체크는 유지됩니다. 감정 중 나가면 진행 중인 도구 동작만 취소됩니다.

감정 결과가 판단을 자동 선택하거나 가격 반영을 체크하지 않습니다. 미감정 항목은
판단과 체크가 비활성이고, 판단하지 않은 항목은 체크할 수 없습니다. 이미 체크한
항목의 판단을 바꾸면 예상 가격을 즉시 갱신합니다. 체크를 해제하면 판단은 저장하되
가격에서는 제외합니다. 공개된 기본/상위 능력치도 각각 판단과 체크가 필요합니다.

`WeaponTrueState`는 실제 상태, `WeaponKnownState`는 감정 지식입니다. 새
`PlayerJudgement`는 별도로 `{grade: 선택지 인덱스, included: bool}`를 항목별 저장합니다.
`grade=-1`은 미선택입니다. reveal 상태는 known에서 확인합니다. 기존 50/50 도구 없는
추측 상태는 모델에 유지하지만 이번 UI에서는 미감정값을 `???`로 가립니다.

결과의 청록/황토/보라/붉은 색은 단순 관찰 힌트입니다. 실제 결과 문자열과 수치는
표시하지만 내부 normal/high grade 또는 정답 판단을 표시하지 않습니다. 중앙에
표시되는 '내 판단'은 오직 플레이어가 고른 값입니다.

## 예상 가격의 별도 매핑

`data/player_estimate.json`은 플레이어 등급을 기존 balance 가격표의 대표 항목에
대응시키는 **데모용 판단 매핑**입니다. balance 값을 여러 GDScript에 복사하지 않습니다.
아래 key는 개발자 설명이며 플레이어 화면에는 표시하지 않습니다.

| 판단 대상 | 낮음 | 무난 | 좋음 | 매우 좋음 |
|---|---|---|---|---|
| 기본 능력치 | NONE | MIXED | ADEQUATE | EXCELLENT |
| 상위 능력치 | NONE | LOW | ADEQUATE | EXCELLENT |
| 강화 | BAD | MIXED | GOOD | PERFECT |
| 제련 | 1단계 대표값 | 4단계 대표값 | 7단계 대표값 | 10단계 대표값 |
| 안정도 | 20% 대표값 | 60% 대표값 | 80% 대표값 | 100% 대표값 |

고유 속성은 없음/있음/높음이 각각 `unique_values`의 NONE/LOW/HIGH에 대응합니다.
증폭 8개 선택지는 순서대로 `amplification_values`의 UNAPPLIED, ZERO_LINE,
ONE_LINE_LOW, ONE_LINE_HIGH, TWO_LINE_LOW, TWO_LINE_HIGH, THREE_LINE_LOW,
THREE_LINE_HIGH에 대응합니다. 실제 속성이 무엇이든 플레이어 선택을 사용합니다.

예상 가격은 항상 tier 기본가에서 시작합니다. 공개되어 있고, 판단을 선택하고,
가격 반영을 체크한 항목만 기여합니다. 실제 수치나 true grade를 통해 판단을 자동
추론하지 않습니다. 실제 결과를 공개해도 선택한 판단이 같으면 예상 기여는 같습니다.

제련은 기존 0.4/0.6 시너지 공식을 사용하되 체크된 기본/상위 판단의 계수를 사용합니다.
체크되지 않은 능력치 계수는 중립값 1.0입니다. 안정도는 선택한 대표값으로 기존
안정도 배율표를 적용하며, 미체크 시 배율은 1.0입니다. 최소 가격 하한과 돈 반올림은
기존 공식을 사용합니다. 시장과 특수 속성은 예상 가격에 포함하지 않습니다.
따라서 예상 가격은 실제 가치와 다를 수 있고, 잘못된 선택도 그대로 반영합니다.

## 보존 규칙과 명시적인 Godot 변경점

`../config/balance.json`이 원본이며 `data/balance.json`은 byte-for-byte 복사본입니다.
이번 UI 수정에서 두 파일 모두 변경하지 않았습니다. `Balance.load_config()`가 별도의
`player_estimate.json`을 읽어 메모리상의 config에 합칩니다.

- 방문 순서: 1–4 판매 손님, 5–7 구매 손님, 8번째는 독립된 seed RNG로 50/50.
- 시작 100,000 골드, 부채 없음. 재고 시작 10칸/최대 20칸/칸당 10,000 골드.
- 자동 확장 없음. 재고는 손님 사이에만 열 수 있습니다.
- 매입 제안은 현재 예상 가격입니다. 현재 요구가 이상이면 해당 **제안 금액**으로 수락합니다.
- 목적별 총 제안 횟수는 reference 명세 5.9의 급전 1회/장비 교체 2회/욕심 판매 2회입니다.
  요구가 미만이면 횟수 1회를 사용합니다. 남은 횟수가 없으면 거래가 결렬됩니다.
- counter-offer는 미확정 규칙의 deterministic 데모 정책입니다. 재제안 기회가 있으면
  현재 요구가를 5% 인하하되 거절한 제안가보다 최소 1골드 높게 유지합니다.
  HIGH 지식 또는 SCAMMER 손님은 요구가를 유지합니다. 최초 요구 가격의 purpose,
  knowledge 및 scammer 배율은 기존 공식을 그대로 사용합니다.
- 수락 시 제안가로 cash/매입 지출/원가를 기록하고 제안가 ÷ true price로 만족도와
  평판을 계산합니다. 거래 결렬은 매입 거절 통계와 기존 미거래 평판을 한 번 적용합니다.
- 자금/공간 부족은 제안을 전송하지 않으므로 횟수를 차감하지 않습니다.
- 현재 요구가/마지막 제안/남은 횟수를 표시합니다. 감정 화면 재진입은 흥정을 초기화하지 않습니다.
  정책은 `data/seller_negotiation.json`, 상태는 `scripts/data/seller_negotiation.gd`에 분리합니다.
- buyer fit, interest, listing, ceiling, haggle, 판매 하한, 평판과 progression은 유지합니다.
- 고물상은 매입가의 50%, Python식 ties-to-even 반올림을 사용합니다.
  평판·매입/판매/전체 거래 횟수·일반 판매 수익/이익은 바뀌지 않습니다.
- **특수 속성은 Godot 생성 결과·감정 필드·UI·실제 및 예상 가격 기여에서 제외했습니다.**
  기존 seed의 뒤쪽 생성 순서를 유지하기 위해 예전 특수 속성 RNG 추첨은 소모만 하고
  저장하지 않습니다. 원본 balance에 남은 특수 속성 표는 호환용이며 적용되지 않습니다.
- **시장 표시는 제거했지만 내부 실제 가격·생성 부하의 시장 보정은 유지했습니다.**
- true price는 플레이어 판단으로 바뀌지 않습니다. 특수 속성 기여 제외에 의한 이전
  데모와의 실제 가격 차이는 요청에 따른 의도된 차이입니다.
- Python 3.12의 compensated sum과 같은 합산 및 ties-to-even 경계 처리를 적용하여
  float 오차에 의한 1골드 대조 차이를 수정했습니다.

## 이번 작업의 파일 목록

새 파일 (Godot `.uid` sidecar 포함):

- `data/player_estimate.json`
- `scripts/data/player_judgement.gd`
- `scripts/data/text_catalog.gd`

수정 파일:

- `project.godot`: 한국어 창 제목, 1920×1080, 비율 유지 viewport stretch.
- `scripts/ui/shop_screen.gd`: 메인 스케치 레이아웃, 감정 전체 화면 진입.
- `scripts/ui/item_detail_panel.gd`: 3열 감정, 별도 판단/체크, 색 힌트, 복귀/취소.
- `scripts/ui/inventory_screen.gd`: 2×10 슬롯, 선택 상세, 확장/처분/감정 복귀.
- `scripts/ui/daily_receipt.gd`: 한 화면 한국어 정산서.
- `scripts/ui/ui_factory.gd`: 한글 시스템 폰트, 공통 위치/패널/돈 표시.
- `scripts/data/weapon_data.gd`: 판단 상태 보유.
- `scripts/systems/appraisal_service.gd`: 특수 속성 감정 제외.
- `scripts/systems/weapon_generator.gd`: 특수 속성 결과 저장 제외.
- `scripts/systems/price_calculator.gd`: 특수 기여 제외, 독립 판단 기반 예상 가격.
- `scripts/systems/balance.gd`: 판단 매핑 로드 및 반올림/합산 경계.
- `scripts/systems/transaction_service.gd`: 결과 문구 한국어화, 거래 규칙 유지.
- `scripts/controllers/customer_controller.gd`: 손님 이름 한국어화.
- `scripts/controllers/day_controller.gd`: 대사 한국어화, 방문 상태 전환 유지.
- `tests/build_reference_cases.py`, `tests/reference_cases.json`: 특수 기여를 제외한
  메모리상 Python config로 기준 사례 생성. 원본 Python 파일은 수정하지 않습니다.
- `tests/run_tests.gd`, `tests/ui_smoke.gd`: 판단 분리·전체 UI/레이아웃 회귀 검증.
- `README.md`, `tests/VERIFICATION.md`: 현재 구현과 검증 결과.

## 검증 실행

저장소 루트에서:

```powershell
& './game/tools/godot/Godot_v4.6.1-stable_win64_console.exe' --headless --path game --editor --quit
& './game/tools/godot/Godot_v4.6.1-stable_win64_console.exe' --headless --path game --script res://tests/run_tests.gd
& './game/tools/godot/Godot_v4.6.1-stable_win64_console.exe' --headless --path game --script res://tests/ui_smoke.gd
& './game/tools/godot/Godot_v4.6.1-stable_win64_console.exe' --path game --script res://tests/ui_smoke.gd -- --screenshots
```

원본 config가 나중에 변경된 경우에만 복사본과 기준 사례를 갱신하세요:

```powershell
Copy-Item config/balance.json game/data/balance.json
python -B game/tests/build_reference_cases.py
```

일반 게임 실행은 Python/테스트 파일을 읽지 않습니다. 다운로드한 엔진, `.godot/`,
검증 캡처 PNG는 Git ignore 대상입니다. 기존 `scenes/main.tscn` 경로는 유효합니다.

## 제한 / 다음 단계

손님·무기 아트, 감정 효과, 대사, 영수증 사운드/팝업/도장 애니메이션은 placeholder입니다.
판단용 대표값은 데모 매핑이며 최종 밸런스가 아닙니다. 한국어 폰트는 시스템의
맑은 고딕/Noto Sans CJK KR 및 OS fallback을 사용합니다. 배포 전 라이선스가 확인된
한글 폰트를 프로젝트에 포함하는 작업이 필요합니다. Windows에서 렌더링을 검증했으며
다른 OS와 export 빌드는 이번 검증 범위 밖입니다. 저장/불러오기와 다일차는 없습니다.

## 추가 변경: 항목별 판정과 seller 제안

추가: `data/seller_negotiation.json`, `scripts/data/seller_negotiation.gd`,
`tests/negotiation_tests.gd`와 해당 UID.
수정: 판단 모델/문구/매핑, price calculator, balance loader, transaction service,
day controller, shop/detail UI, 기존 Godot 테스트 및 이 문서.

```powershell
& './game/tools/godot/Godot_v4.6.1-stable_win64_console.exe' --headless --path game --script res://tests/negotiation_tests.gd
```
