# 무기 전당포 — Godot Day 1

Godot 4.6.1 stable, GDScript 전용, 1920×1080 한국어 placeholder UI입니다.
game/project.godot을 Import한 뒤 F5로 실행합니다. Python은 runtime에서 실행하지 않습니다.

[현재 규칙과 변수명](docs/RULE_CHANGES.md)에 공통 가격식·시장·호환·판단 구조를 정리했습니다.
원본 ../config/balance.json과 data/balance.json은 동일한 JSON 설정값을 사용합니다.
data/player_estimate.json과 data/seller_negotiation.json은 별도 Godot 판단·흥정 정책입니다.

## 플레이 흐름

- 첫날 1~4 seller, 5~7 buyer, 8번째만 seed 기반 50/50. 일반 방문 config는 55/45입니다.
- 시작 100,000 골드, 부채 없음. 재고 10칸/최대20칸/수동 확장 10,000 골드입니다.
- 무기를 클릭하면 감정 화면으로 이동합니다. 기본·상위와 구체 숫자는 처음부터 공개합니다.
- 강화·제련·증폭·고유·안정도는 클릭 후0.3초 도구 연출과 정확한 결과를 공개합니다.
- 공개 → 판단 선택 → 가격 반영 체크를 분리하며 자동 판단·체크하지 않습니다.
- 시장 인기와 직업 밸런스는 각각3개 선택지와 가격 반영 체크가 있습니다.
- 실제 시장과 판단은 분리하며 라디오/TV의 힌트 데이터와 TODO만 준비했습니다.
- 매입 제안 버튼은 현재 예상가를 전송합니다. 현재 요구가 이상이면 제안 금액 전체를 지급합니다.
- 총 제안 횟수는 급전1/교체2/욕심2입니다. 남은 기회가 있으면 요구가를5% 낮추되,
  거절한 제안보다1골드 높게 유지합니다. 높은 시장 지식·사기꾼은 요구가를 유지합니다.
- 공간/현금 부족은 제안 횟수를 쓰지 않습니다. 결렬 시 거절 통계·평판을 한 번 반영합니다.
- 재고는 손님 사이에 열 수 있습니다. 고물상은 실제 매입가50%를 반올림합니다.
  평판·일반 거래 횟수·판매 이익은 바꾸지 않습니다. 손님8명 후 영수증을 표시합니다.

## 데이터

WeaponTrueState, WeaponKnownState, PlayerJudgement는 별개입니다.
판단은 selected_value_tier(-1 미선택)와 included로 보관합니다.
강화/제련/안정도/기본/상위는4단계, 고유는 없음/있음/높음,
증폭은 미적용/0줄/1~3줄 낮음·높음, 시장은 부정/중립/긍정입니다.
제련 대표값1/4/7/10, 안정도20/60/80/100을 사용합니다.
제련은 체크된 능력치 판단 계수(미체크1.0), 안정도 미체크는 배율1.0입니다.
시장 체크는 선택한 -0.20/0/+0.20을 반영합니다. 틀린 판단도 그대로 적용합니다.

특수 속성은 양쪽 생성·설정·가격·감정에서 폐기했습니다. 시장은 안정도에 영향을 주지 않습니다.
buyer는 자신의 사용 가능 무기 pool의 item_type으로 호환을 판정합니다.
required_class는 시장·스탯 기준 직업이며 해당 직업만 구매한다는 뜻이 아닙니다.

## 실행·검증

```powershell
& './game/tools/godot/Godot_v4.6.1-stable_win64.exe' --path game
python -B -m unittest discover -s tests -q
python -B game/tests/build_reference_cases.py
& './game/tools/godot/Godot_v4.6.1-stable_win64_console.exe' --headless --path game --editor --quit
& './game/tools/godot/Godot_v4.6.1-stable_win64_console.exe' --headless --path game --script res://tests/run_tests.gd
& './game/tools/godot/Godot_v4.6.1-stable_win64_console.exe' --headless --path game --script res://tests/market_rules.gd
& './game/tools/godot/Godot_v4.6.1-stable_win64_console.exe' --headless --path game --script res://tests/negotiation_tests.gd
& './game/tools/godot/Godot_v4.6.1-stable_win64_console.exe' --headless --path game --script res://tests/ui_smoke.gd
```

기본 seed는12352이며 -- --seed=숫자로 바꿀 수 있습니다.
128개 기준 사례는 원본 Python 가격식을 보정 없이 Godot과 비교합니다.
[검증 기록](tests/VERIFICATION.md)을 참고하세요. 과거 output은 갱신하지 않았습니다.
아트·소리·연출·방송은 placeholder/TODO이고 저장·다일차 캠페인은 없습니다.
