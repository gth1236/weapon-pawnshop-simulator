# 공통 규칙 정리 검증 — 2026-10-04

환경: Windows, Godot 4.6.1.stable.official.14d19694e.
실제 UI 렌더링: OpenGL Compatibility / NVIDIA RTX 4060 / 1920×1080.

| 검증 | 결과 |
|---|---|
| Python 전체 unittest | 95 tests, OK |
| Godot 규칙·Python 대조 run_tests.gd | 14,231 checks / 0 failures |
| Godot 시장·호환 market_rules.gd | 321 checks / 0 failures |
| Godot seller negotiation_tests.gd | 79 checks / 0 failures |
| Godot ui_smoke.gd | 768 checks / 0 failures, headless 및 실제 렌더링 |
| Editor import | parse/resource 오류 없음 |
| main scene 시작 | 오류 없이 종료 |
| git diff --check | 통과 |

128개 기준 사례는 현재 Python config/가격식을 임시 보정 없이 사용합니다.
실제 가격·요구가·buyer fit 성분·판매 결과·평판·progression을 Godot과 대조했습니다.
성공 buyer 판매56개와 실패 사례를 포함합니다.

추가 검증:
- 특수 속성 모델/config/감정/가격/생성 잔재 제거.
- 모든 직업과 무기 종류 조합을 usable pool 기준으로 확인.
- staff의 MAGE/CLERIC 호환, config에 새로 추가한 공유 bow 호환.
- 두 시장 축 NORMAL=0, 양수/음수=±0.20.
- 동일 seed에서 시장을 바꿔도 생성된 true state 전체가 동일.
- 시장 판단 선택/미체크/체크/변경이 예상가에만 반영.
- 플레이어 시장 관찰은 null로 시작하며 힌트 기록이 실제 시장을 바꾸지 않음.
- 1,000개 seed의 Day 1 순서·재현성; 8번 seller491/1000.
- 감정·판단·체크 분리, seller 제안/흥정/재제안/수락/결렬.
- 수동 재고 확장, 고물상, 8명 후 영수증, 현금·거래 통계 보존.
- 실제 포인터 입력으로 감정 진입; viewport 좌표로 push_input.
- 표시된 Label/Button의 한국어 및 viewport 경계, 스크롤 미사용.
- 9개 판단 행을 1920×1080에서 직접 캡처 확인.

초기 제한된 실행 환경에서 OS 인증서/사용자 로그 경로 오류가 발생하여,
최종 엔진 검증은 정상 OS 접근 환경에서 다시 실행했습니다. 최종 로그에는 해당 오류가 없습니다.
초기 UI 테스트에서 발견한 창 제목 속성의 잘못된 rename과 좌표 변환 문제는 수정 후 재검증했습니다.

과거 output/ 파일을 수정·재생성하지 않았습니다. commit/push하지 않았습니다.
규칙/이름 변경은 ../docs/RULE_CHANGES.md, 실행은 ../README.md를 참고하세요.

