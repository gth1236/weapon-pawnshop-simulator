# 현재 규칙과 변수 이름 — 2026-10-04

| 이전 | 현재 |
|---|---|
| guest_class | adventurer_class |
| level / guest_level (손님) | adventurer_level |
| power / guest_power (손님) | adventurer_power |
| tendency | equipment_tendency |
| knowledge (손님) | market_knowledge |
| purpose | selling_purpose |
| kindness | trade_attitude |
| title | title_rank |
| achievement | achievement_rank |
| class_power | class_balance |
| compatible (판매자와 무기) | seller_class_compatible |
| item_class | required_class |
| PlayerJudgement.grade | selected_value_tier |
| remaining_attempts | remaining_offer_attempts |

연결된 progression/가격 설정 키도 새 이름을 사용합니다. 제련 반복문의 level,
감정 지식 knowledge, Godot 창 제목 title은 별개 개념이므로 유지합니다.
새 CSV는 현재 모델 이름을 따릅니다. 과거 output과 이전 명세는 당시 기록으로 보존합니다.

## 실제 가격·생성

특수 속성의 모델/생성/감정/가격/config/난수 소비를 제거했습니다.
Python 기준 사례 생성의 특수 기여 임시 보정도 제거했습니다.
required_class는 시장·스탯 생성의 기준 직업입니다. 독점적인 구매 직업 제한이 아닙니다.
buyer의 class_weapon_pools에 item_type이 있으면 구매 가능합니다. staff는 MAGE/CLERIC
모두 호환됩니다. 다른 공유 무기도 pool만 수정하면 됩니다.
seller_class_compatible은 생성 당시 판매자 직업과의 호환 분기 기록입니다.

시장 상태 저장 순서는 [class_balance, class_popularity]입니다.
인기 UNPOPULAR/NORMAL/POPULAR와 밸런스 WEAK/NORMAL/STRONG은 각각 -0.20/0/+0.20입니다.
기준 직업의 시장 기여를 true price modifier에 합산합니다.

```
effective_refining = refining_value * (0.4 * normal_coefficient + 0.6 * high_coefficient)
modifier = class_balance + class_popularity + normal + high + unique + reinforcement + amplification + effective_refining
true_price = round(max(base * (1 + modifier) * stability_multiplier, base * 0.1))
```

안정도 생성 부하는 강화+제련+증폭만 사용합니다. 시장 부하 필드는 없습니다.
effective_processing_load는 processing_load와 같습니다. 최대 부하17이므로 도달 불가능한
18~20 설정 구간을 제거했으며 나머지 구간 확률은 유지했습니다.
특수 난수 추첨 제거로 과거 seed 결과는 달라집니다. 새 버전 내 재현성은 유지합니다.
Python과 Godot은 RNG가 다르므로 같은 seed가 아니라 같은 입력의 실제 가격을 비교합니다.

## 시장 판단과 힌트

PlayerJudgement는 true state 및 known state와 별개입니다. selected_value_tier는 선택지
인덱스(-1 미선택), included는 가격 반영 체크입니다. 시장 인기/직업 밸런스는 각각
3개 선택지이며 도구 감정 없이 선택할 수 있습니다. 체크한 판단만 -0.20/0/+0.20을
예상 가격에 합산합니다. 자동 선택/체크/실제 시장 대입은 하지 않습니다.

DayController.market는 실제 경제 상태입니다. MarketKnowledge.observations는 별도
직업별 시장 정보로 두 축이 null에서 시작합니다. 힌트는 {reported_value, source}로
기록할 수 있고 실제 시장이나 판단을 바꾸지 않습니다.
TODO: 메인 화면 라디오/TV로 힌트 표시. 아트와 방송 상호작용은 아직 구현하지 않습니다.

## 방문·거래

일반 role 설정은 seller55%/buyer45%입니다. Godot Day 1은 기존 4seller+3buyer+마지막50/50입니다.
초기 현금/재고, 감정, 매입 제안·흥정, buyer 판매, 수동 확장, 고물상, 8명 후 정산을 유지합니다.
remaining_offer_attempts는 최초 제안을 포함하는 남은 총 횟수입니다.
