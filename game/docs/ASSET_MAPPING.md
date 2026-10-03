# 비주얼 1차 적용 리소스 매핑

기존 파일명과 원본 이미지를 그대로 사용한다. 경로는 `res://assets/` 기준이다.
게임 데이터·생성·가격·거래 로직은 변경하지 않는다.

| 용도 | 리소스 |
|---|---|
| 메인 배경 | `backgrounds/shop_background.png` |
| 감정 배경 | `backgrounds/appraisal_background.png` |
| 공통 폰트 | `fonts/Hakgyoansim Nadeuri OTF L.otf` |
| 무기 테이블 | `props/item_table.png` |
| 일자·골드·상태 패널 | `ui/day_money_info.png` |
| 버튼 | `ui/button_panel_godot_pack/button_panel_9patch.png` |
| 대화창 | `ui/chat_panel_godot_pack/dialogue_panel_9patch.png` |
| 감정 정보 패널 | `ui/item_interface.png` |

## 손님

| adventurer_class | 리소스 |
|---|---|
| WARRIOR | `characters/warrior.png` |
| MAGE | `characters/mage.png` |
| ROGUE | `characters/rogue.png` |
| ARCHER | `characters/archer.png` |
| GUNNER | `characters/gunner.png` |
| CLERIC | `characters/cleric.png` |

## 무기

모든 `item_type`은 `weapons/{item_type}.png`에 연결한다.
파일명과 실제 이미지를 확인했으며 불명확한 매핑은 없다.

| item_type | 리소스 |
|---|---|
| one_handed_sword | `weapons/one_handed_sword.png` |
| greatsword | `weapons/greatsword.png` |
| spear | `weapons/spear.png` |
| axe | `weapons/axe.png` |
| staff | `weapons/staff.png` |
| wand | `weapons/wand.png` |
| grimoire | `weapons/grimoire.png` |
| dagger | `weapons/dagger.png` |
| throwing_weapon | `weapons/throwing_weapon.png` |
| bow | `weapons/bow.png` |
| crossbow | `weapons/crossbow.png` |
| gun | `weapons/gun.png` |
| heavy_weapon | `weapons/heavy_weapon.png` |
| gauntlet | `weapons/gauntlet.png` |
| mace | `weapons/mace.png` |

## 표시 방식

- `visual_assets.gd`에서 경로와 TextureRect/NinePatchRect 생성을 공유한다.
- 배경·손님·무기·테이블은 종횡비를 유지한다. 장식 노드는 마우스 입력을 가로채지 않는다.
- 버튼 패치는 원본 팩 권장 여백 90/70/90/70, 대화창은 120/235/120/115를 사용한다(좌/상/우/하).
- 상태 패널은 원본의 보드 영역 `(174, 191, 446, 230)`을 사용한다.
- 아이템 인터페이스는 제목 영역 `(28, 22, 780, 172)`과 본문 영역 `(28, 198, 780, 660)`을 나눠 사용하여 기존 감정 행과 조작부를 유지한다. 원본 이미지는 수정하지 않는다.
- 폰트는 공통 Theme에 적용한다. 재고·정산 화면에는 새 아트를 적용하지 않는다.

## 검증

Godot 4.6.1에서 리소스 임포트 및 파싱 오류 없이 실행했다.

| 검증 스크립트 | 결과 |
|---|---|
| `tests/visual_assets.gd` | 735개 검사, 실패 0: 직업 6종·무기 15종, 메인/감정 이미지, 클릭 방해 여부, 버튼 배경 크기 |
| `tests/ui_smoke.gd` | 807개 검사, 실패 0: 실제 렌더링 및 1920×1080 화면 확인 |
| `tests/negotiation_tests.gd` | 79개 검사, 실패 0: 제안·흥정·재제안·수락/결렬·다음 손님 |
| `tests/run_tests.gd` | 14,231개 검사, 실패 0: 기존 Day 1 및 거래 규칙 회귀 검증 |
