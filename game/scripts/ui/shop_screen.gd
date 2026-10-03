extends Control

var day: DayController
var hud: Label
var customer: Label
var dialogue: Label
var portrait_label: Label
var table_button: Button
var appraisal_button: Button
var next_button: Button
var inventory_button: Button
var detail: ItemDetailPanel
var inventory_screen: InventoryScreen
var receipt: DailyReceipt

func _ready() -> void:
	UIFactory.setup_theme(self)
	UIFactory.backdrop(self)
	var seed_input = DayController.DEFAULT_SEED
	for argument in OS.get_cmdline_user_args():
		if argument.begins_with("--seed="):
			seed_input = int(argument.trim_prefix("--seed="))
	day = DayController.new(seed_input)
	UIFactory.panel(self, Rect2(28, 26, 470, 140))
	hud = UIFactory.label(self, "", 25)
	UIFactory.at(hud, Rect2(48, 40, 435, 118))
	UIFactory.at(UIFactory.label(self, "무기 전당포", 42), Rect2(770, 42, 480, 66))
	inventory_button = UIFactory.button(self, "보유 재고", func(): inventory_screen.open(day))
	UIFactory.at(inventory_button, Rect2(1658, 28, 230, 135))
	UIFactory.panel(self, Rect2(405, 188, 480, 574))
	portrait_label = UIFactory.label(self, "손님을 기다리는 중", 36)
	UIFactory.at(portrait_label, Rect2(435, 368, 420, 240))
	portrait_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	UIFactory.at(UIFactory.label(self, "손님 영역 · 임시 초상", 22), Rect2(515, 708, 300, 40))
	customer = UIFactory.label(self, "", 30)
	UIFactory.at(customer, Rect2(40, 782, 800, 48))
	UIFactory.panel(self, Rect2(28, 838, 1314, 215))
	dialogue = UIFactory.label(self, "", 28)
	UIFactory.at(dialogue, Rect2(52, 861, 1266, 105))
	next_button = UIFactory.button(self, "손님 맞이하기", continue_day)
	UIFactory.at(next_button, Rect2(980, 982, 334, 50))
	appraisal_button = UIFactory.button(self, "감정하기", open_detail)
	UIFactory.at(appraisal_button, Rect2(1510, 245, 280, 65))
	UIFactory.panel(self, Rect2(1395, 791, 492, 258), Color("302b29"))
	UIFactory.at(UIFactory.label(self, "감정 테이블", 32), Rect2(1520, 892, 270, 60))
	table_button = UIFactory.button(self, "", open_detail)
	UIFactory.at(table_button, Rect2(1410, 340, 460, 468))
	table_button.add_theme_font_size_override("font_size", 34)
	detail = ItemDetailPanel.new()
	add_child(detail)
	detail.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	detail.hide()
	detail.buy_requested.connect(day.buy)
	detail.refuse_requested.connect(day.refuse)
	inventory_screen = InventoryScreen.new()
	add_child(inventory_screen)
	inventory_screen.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	inventory_screen.hide()
	receipt = DailyReceipt.new()
	add_child(receipt)
	receipt.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	receipt.hide()
	day.changed.connect(refresh)
	day.completed.connect(func(): receipt.display(day))
	refresh()

func open_detail() -> void:
	if day.phase == "SELLER":
		detail.show_item(day.item, day.config, day.market, true, day.message, day.negotiation)

func continue_day() -> void:
	if day.phase == "BUYER":
		day.resolve_buyer()
	else:
		day.next_guest()

func refresh() -> void:
	var s = day.state
	hud.text = "%d일차 · 손님 %d / 8\n보유 자금  %s\n평판 %.2f · 재고 %d / %d" % [s.day, day.guest_number, UIFactory.money(s.cash), s.reputation, s.inventory.size(), s.capacity]
	customer.text = "전당포 주인" if day.guest.is_empty() else "%s · %s · %d레벨" % [day.guest.name, TextCatalog.CLASSES[day.guest.guest_class], day.guest.level]
	portrait_label.text = "손님을 기다리는 중" if day.phase in ["BETWEEN", "COMPLETE"] else "%s\n\n%s 손님" % [TextCatalog.CLASSES[day.guest.guest_class], "무기를 파는" if day.phase == "SELLER" else "무기를 사는"]
	dialogue.text = day.message
	table_button.disabled = day.phase != "SELLER"
	appraisal_button.disabled = day.phase != "SELLER"
	table_button.text = "빈 테이블" if day.item == null else "%s\n\n%d등급 무기\n\n눌러서 살펴보기" % [TextCatalog.weapon(day.item.known.item_type), day.item.known.tier]
	inventory_button.disabled = day.phase != "BETWEEN"
	inventory_button.text = "보유 재고\n%d / %d\n%s" % [s.inventory.size(), s.capacity, "손님 응대 중" if inventory_button.disabled else "열기"]
	next_button.disabled = day.phase not in ["BETWEEN", "BUYER"]
	next_button.text = "재고를 보여주고 거래하기" if day.phase == "BUYER" else "손님 맞이하기  %d / 8" % (day.guest_number + 1)
	if day.phase == "COMPLETE":
		next_button.text = "첫날 영업 종료"
	if day.phase != "SELLER":
		detail.close_panel()
	elif detail.visible:
		detail.dialogue_label.text = day.message
		detail.refresh_controls()
