class_name DailyReceipt
extends Control

func display(day: DayController) -> void:
	UIFactory.clear(self)
	UIFactory.backdrop(self)
	UIFactory.panel(self, Rect2(366, 30, 1188, 1020))
	UIFactory.at(UIFactory.label(self, "첫날 영업 완료", 44), Rect2(420, 59, 1080, 70))
	UIFactory.at(UIFactory.label(self, "영업 정산서 · 손님 8명 응대 완료", 26), Rect2(420, 137, 1080, 50))
	var s = day.state
	var amounts = {"시작 자금": s.starting_cash, "매입 지출": s.purchase_spending, "판매 수익": s.sale_revenue, "고물상 수익": s.scrap_revenue, "실현 거래 이익": s.realized_trade_profit, "고물상 실현 손실": s.scrap_realized_loss, "재고 확장 지출": s.expansion_spending}
	var index = 0
	for key in amounts:
		UIFactory.at(UIFactory.label(self, key, 27), Rect2(424, 216 + index * 53, 630, 47))
		var value = UIFactory.label(self, UIFactory.money(amounts[key]), 27)
		value.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
		UIFactory.at(value, Rect2(1030, 216 + index * 53, 454, 47))
		index += 1
	UIFactory.at(UIFactory.label(self, "평판 변화: %+.2f\n매입 거래: %d회 · 판매 거래: %d회\n매입 거절: %d회 · 고물상 처분: %d개" % [s.reputation, s.seller_trades, s.buyer_trades, s.refused_purchases, s.scrapped_items], 27), Rect2(424, 616, 1060, 142))
	UIFactory.at(UIFactory.label(self, "종료 자금: %s\n보유 재고: %d / %d" % [UIFactory.money(s.cash), s.inventory.size(), s.capacity], 32), Rect2(424, 773, 1060, 105))
	UIFactory.at(UIFactory.label(self, "실현 거래 이익은 판매한 무기의 매입 원가를 뺀 금액입니다.\n고물상 손익과 확장 지출은 별도로 표시합니다.", 21), Rect2(424, 889, 1060, 64))
	UIFactory.at(UIFactory.button(self, "같은 하루 다시 시작", func(): get_tree().reload_current_scene()), Rect2(424, 971, 1060, 54))
	show()
	# TODO: receipt sound, pop-up and stamp animation.
