# RPG Weapon Pawnshop — Python reference implementation

Python reference와 `game/`의 Godot 4.6.1 Day 1 프로젝트입니다.
최신 규칙과 변수명은 [규칙 변경 기록](game/docs/RULE_CHANGES.md)을 참고하세요.
기존 seller/buyer 생성, buyer fit, 가격, 주간 시장, reputation/progression 계산을 유지합니다.
Python 3.10 이상, 표준 라이브러리만 사용합니다.

## 실행

```bash
python -m unittest discover -s tests -v
python -m simulator.main --economy-only --economy-trials 100 --economy-weeks 12 --seed 12345 --skip-economy-comparisons --economy-output-dir output/reference_sanity
```

이번 100-trial 실행은 regression/sanity 확인이며 밸런스 결론을 내리지 않습니다.
실행 결과 요약: [SANITY_SUMMARY.md](output/reference_sanity/SANITY_SUMMARY.md).
링크된 과거 sanity 결과는 당시 규칙의 기록입니다. 현재 검증 결과는 game/tests/VERIFICATION.md를 참고하세요.
일반 CLI 기본 경제 분석은 config에 설정된 12주/500회입니다.
`--starting-cash`, `--economy-weeks`, `--economy-trials`, `--config`로 실험을 재현할 수 있습니다.
현재 debt가 비활성화되어 있으므로 양수 `--starting-debt`는 오류입니다.

무기 생성/가격/평판 분석은 기존 명령도 사용할 수 있습니다.

```bash
python -m simulator.main --count 10000 --seed 12345 --economy-trials 0
```

## GAME RULE — 현재 확정된 규칙

| 항목 | 규칙 |
|---|---|
| 시작 현금 | 100,000 G |
| 부채 | 없음: starting_debt = 0, 상환/이자 없음 |
| 순자산 | cash + inventory current appraised value |
| 시간 | 1주 = 7일, 1개월 = 4주 |
| 운영비 | 2,000 × week G; 12주 합계 156,000 G |
| 정산 | 일요일 마지막 고객과 해당 주 처리 종료 후 운영비, 이후 checkpoint |
| 재고 | 시작 10칸, 최대 20칸; 가득 차면 신규 매입 불가 |
| 확장 | 플레이어가 선택; 매번 10,000 G로 정확히 1칸 추가 |
| 구매자 예산 | 없음; 기존 fit/interest/listing/price ceiling/haggle 사용 |
| 기본 공개 | tier와 생성된 모든 concrete RPG stat 수치는 항상 정확 |
| 감정 대상 | reinforcement, refining, amplification, stability, unique property |
| 도구 없는 감정 | 각 속성 50% 정확한 추측, 50% 유효한 다른 값 |
| 도구 사용 | 해당 도구 보유 후 명시적으로 사용한 속성만 정확히 공개 |
| 고물상 | 플레이어 선택; 실제 매입가의 50%에 즉시 처분 |

확장 비용은 `economy.inventory_expansion_cost` 단일 값입니다. 이전 단계별 TEMPORARY
비용표는 제거했습니다. 현금이 확장비보다 적거나 이미 20칸이면 확장하지 않습니다.
Python 일반 방문은 최초 4명 seller, 이후 seller/buyer 55:45입니다.
Godot Day 1은 1~4 seller, 5~7 buyer, 8번째만 50:50입니다.
구매 호환은 buyer의 무기 pool에 item_type이 있는지로 판정합니다.
required_class는 시장·스탯 생성 기준 직업이며 독점적인 구매 직업 제한이 아닙니다.
시장 두 축은 각각 -20%/0/+20%이며 안정도에는 영향을 주지 않습니다. 특수 속성은 폐기했습니다.

## SIMULATION-ONLY POLICY

`config/balance.json`의 `simulation_policies`에 게임 규칙과 별도로 저장합니다.
다음은 플레이어의 선택을 대신하는 TEMPORARY heuristic입니다.

- 자동 매입: asking price가 true appraisal 이하이고 현금/공간 조건을 만족하면 매입.
- 자동 판매: 기존 buyer fit 및 offer/가격 하한 정책 유지.
- 자동 확장: `EXPAND_IF_BLOCKED_AND_AFFORDABLE`. 가득 찼을 때 확장비와 해당 매입비를
  모두 감당할 수 있어야 확장. `MANUAL_ONLY`로 자동 확장을 끌 수 있습니다.
- 운영비 부족: negative cash를 허용하고 계속 실행. cash <= 0이면 새 매입은 불가,
  기존 재고 판매로 현금 회복 가능. 실제 게임의 부족 현금 처리는 플레이 테스트 후 결정합니다.
- 고물상: `MANUAL_ONLY`. baseline은 자동 처분하지 않습니다.

자동 매입은 true appraisal을 참조합니다. 따라서 이 baseline은 플레이어의 오판에 따른
매입 손실을 모델링하지 않습니다. 잘못 표시된 값은 실제 가치나 기존 거래 정책을 바꾸지 않습니다.

## 감정 데이터와 Godot 전달 경계

`WeaponTrueState`는 실제 아이템 상태, `WeaponKnownState`는 저장되는 플레이어 지식입니다.
`KnownField`의 `knowledge_state`, `displayed_value`를 UI에 전달합니다.
`known_exact_value`는 EXACT일 때만 채웁니다. 기존 min/max/UNKNOWN 구조는 호환성을 위해
유지하지만 현재 생성된 tier/stat은 EXACT, 숨은 속성은 UNAPPRAISED_GUESS로 시작합니다.

- `weapon_generator.generate_weapon`은 true state와 known state를 함께 반환합니다.
- `known_state.player_view()`는 JSON 직렬화 가능한 플레이어용 데이터만 반환합니다.
  stat의 internal grade/category/relevance와 true price는 포함하지 않습니다.
- 모든 기존 concrete stat line은 공개합니다. unique/amplification에서 생성된 수치도
  공개하지만 그 속성의 상태/등급은 별도의 감정 필드입니다.
- unique property는 현재 존재하는 property enum을 사용합니다. 새로운 효과 목록이나
  수치 범위를 발명하지 않습니다. normal/high stat의 EXCELLENT/ADEQUATE 등 내부 등급은 숨깁니다.
- `appraisal.create_player_knowledge`: 각 속성마다 0.5 확률로 true value, 아니면 config의
  유효 domain에서 true value를 제외한 값을 균등 선택합니다. 정답 추측도 GUESS로 저장합니다.
- 추측값은 생성 시 한 번 저장하며 화면을 다시 열어도 재추첨하지 않습니다. generation RNG를
  소모하지 않는 파생 RNG를 사용하여 기존 생성/거래 흐름을 보존합니다.
- `appraisal.apply_appraisal_tool(config, weapon, known, property_name, owned_tools)`:
  config의 필요 도구를 확인하고 해당 known field만 EXACT로 갱신합니다. 보유만으로 공개하지
  않으며 true state를 변경하지 않습니다. 도구가 없으면 PermissionError입니다.
- `price_calculator`는 항상 true state를 사용합니다. `PriceResult.true_appraised_price`는
  기존 appraised_price의 명시적인 별칭입니다.

디버그 CSV에는 true state도 포함됩니다. Godot 플레이어 UI에는 디버그 레코드 전체를
넘기지 말고 `player_view()`만 전달하세요. `player_visible_json` 필드로 해당 경계를 확인할 수 있습니다.

## 수동 재고 액션

`economy_simulation.expand_inventory(config, state, day=None)`는 성공 시 True를 반환하며
현금/슬롯/확장 통계를 갱신합니다. 실제 게임은 플레이어 요청 시 이 액션을 호출합니다.

`economy_simulation.scrap_inventory_item(config, state, item_id, day=None)`는 보유 아이템을
찾아 `round(final_purchase_price * 0.5)`를 현금에 더하고 재고에서 제거합니다.
기존 가격과 같은 Python round 규칙입니다(101 G → 50 G, 103 G → 52 G).
존재하지 않거나 이미 처분한 item_id는 ValueError이며 상태를 바꾸지 않습니다.

별도 `scrap_count`, `scrap_revenue`, `scrap_cost_basis`, `scrap_realized_loss`를 누적합니다.
손실은 매입가 - 처분가입니다. reputation, shop/seller/buyer trade count, 시장,
일반 판매 횟수/수익/margin/holding-day 통계에 섞이지 않습니다.
`inventory_actions`와 첫 trial의 `inventory_actions.csv`에 수동 확장/고물상 액션을 기록합니다.

## 재사용할 핵심 파일

- `config/balance.json`: 규칙, 확률/가격표, 감정 도구 매핑, simulation policy 구분.
- `simulator/models.py`: true/known/stat/price 모델과 player_view 직렬화 경계.
- `simulator/appraisal.py`: 유효 domain, 저장되는 추측, 도구 사용 액션.
- `simulator/economy_simulation.py`: ShopState/InventoryItem, 거래, 수동 확장/고물상, 주간 정산.
- `simulator/weapon_generator.py`, `guest_generator.py`, `price_calculator.py`, `buyer_fit.py`:
  기존 생성/가치/수요 로직. `reputation_simulation.py` 등 기존 progression 로직도 유지합니다.
- `simulator/config.py`: config 검증; `tests/`: 이식 시 회귀 검증 기준.
- `rpg_weapon_pawnshop_core_system_spec_v0_2.txt`: 이전 시스템 명세. 최신 변경은 game/docs/RULE_CHANGES.md와 현재 config/source를 우선합니다.

## 과거 실험과 TODO

`output/economy_12_weeks`, `output/economy_debt_policies`, `output/economy_no_debt` 등 기존
결과는 historical results로 보존합니다. 그 안의 시작 자금/슬롯/부채/확장표는 현재 규칙이 아닙니다.
과거 부채 비교 코드는 재현을 위해 남겨 두었지만 기본 `debt_repayment.enabled = false`로
mandatory/optional 모두 비활성화됩니다. 역사적 실험은 별도 config에서 명시적으로 켜야 합니다.
현재 게임에 상환/이자 시스템을 추가하지 않습니다.

TODO: 실제 게임의 운영비 부족/게임오버 처리, 감정 도구 획득/비용/사용 UX, 아직 미정인
unique 효과 세부 데이터, 실제 플레이어 매입/판매 선택 연결. buyer budget은
플레이 테스트에서 필요성이 확인될 때만 검토합니다. 이벤트는 미구현이며 향후 기존 변수의
일시 modifier로 확장 가능합니다. 기존 미확정 생성/수치/진행 밸런스는 config의
`metadata.temporary_values` 표시를 유지합니다. 이번 작업에서 추가 밸런스 튜닝은 하지 않습니다.
