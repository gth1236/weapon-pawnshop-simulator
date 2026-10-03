class_name InventoryScreen
extends Control

signal closed
var controller: DayController
var body: Control
var selected: WeaponData
var confirmation: ConfirmationDialog
var detail: ItemDetailPanel
var slot_buttons: Array = []
var expand_button: Button
var inspect_button: Button
var scrap_button: Button
var back_button: Button

func _ready() -> void:
	body = Control.new()
	add_child(body)
	body.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	detail = ItemDetailPanel.new()
	add_child(detail)
	detail.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	detail.hide()
	confirmation = ConfirmationDialog.new()
	confirmation.title = "고물상에 처분할까요?"
	confirmation.get_ok_button().text = "처분하기"
	confirmation.get_cancel_button().text = "취소"
	confirmation.confirmed.connect(func(): Sfx.perform(confirm_scrap))
	confirmation.canceled.connect(func(): Sfx.play("click"))
	add_child(confirmation)

func open(day: DayController) -> void:
	if day.phase != "BETWEEN":
		return
	controller = day
	selected = null
	show()
	rebuild()

func rebuild() -> void:
	UIFactory.clear(body)
	slot_buttons.clear()
	UIFactory.backdrop(body)
	var state = controller.state
	back_button = UIFactory.button(body, "상점으로", func(): hide(); closed.emit())
	UIFactory.at(back_button, Rect2(30, 28, 230, 116))
	UIFactory.at(UIFactory.label(body, "보유 재고", 42), Rect2(800, 32, 460, 70))
	UIFactory.at(UIFactory.label(body, "재고 %d / %d  ·  최대 %d칸  ·  보유 자금 %s" % [state.inventory.size(), state.capacity, controller.config.economy.maximum_inventory_capacity, UIFactory.money(state.cash)], 26), Rect2(490, 116, 1000, 52))
	expand_button = UIFactory.button(body, "슬롯 1칸 확장\n%s" % UIFactory.money(int(controller.config.economy.inventory_expansion_cost)), func():
		controller.expand()
		rebuild())
	UIFactory.at(expand_button, Rect2(1550, 30, 336, 115))
	expand_button.disabled = state.capacity >= controller.config.economy.maximum_inventory_capacity or state.cash < controller.config.economy.inventory_expansion_cost
	if state.capacity >= controller.config.economy.maximum_inventory_capacity:
		expand_button.text = "최대 슬롯 도달\n20 / 20"
	for shelf in range(2):
		var table_y = 450 if shelf == 0 else 962
		UIFactory.panel(body, Rect2(45, table_y, 1830, 78), Color("302b29"))
		UIFactory.at(UIFactory.label(body, "첫 번째 보관 테이블" if shelf == 0 else "두 번째 보관 테이블", 24), Rect2(760, table_y + 19, 600, 50))
		for column in range(10):
			var index = shelf * 10 + column
			var owned = state.inventory[index] if index < state.inventory.size() else null
			var caption = "%02d\n\n잠긴 슬롯" % (index + 1) if index >= state.capacity else "%02d\n\n빈 슬롯" % (index + 1)
			if owned != null:
				caption = "%02d\n\n%s\n%d등급" % [index + 1, TextCatalog.weapon(owned.known.item_type), owned.known.tier]
			var slot = UIFactory.button(body, caption, func():
				selected = owned
				rebuild())
			slot.add_theme_font_size_override("font_size", 22)
			UIFactory.at(slot, Rect2(54 + column * 182, table_y - 215, 174, 205))
			slot.disabled = owned == null
			slot.toggle_mode = true
			slot.button_pressed = owned != null and owned == selected
			slot_buttons.append(slot)
	UIFactory.panel(body, Rect2(46, 555, 1828, 158))
	inspect_button = UIFactory.button(body, "상세 감정 보기", open_detail)
	UIFactory.at(inspect_button, Rect2(1370, 580, 225, 102))
	scrap_button = UIFactory.button(body, "고물상에 처분", request_scrap)
	UIFactory.at(scrap_button, Rect2(1613, 580, 236, 102))
	var valid = selected != null and selected in state.inventory
	inspect_button.disabled = not valid
	scrap_button.disabled = not valid
	if valid:
		UIFactory.at(UIFactory.label(body, "%s · %d등급\n요구 직업: %s" % [TextCatalog.weapon(selected.known.item_type), selected.known.tier, TextCatalog.CLASSES[selected.known.required_class]], 26), Rect2(70, 577, 320, 112))
		UIFactory.at(UIFactory.label(body, "매입 가격: %s\n현재 감정가: %s\n획득일: %d일차" % [UIFactory.money(selected.final_purchase_price), UIFactory.money(PriceCalculator.calculate(controller.config, selected, controller.market).true_appraised_price), selected.purchase_day], 23), Rect2(420, 571, 410, 130))
		var stats = []
		for line in selected.known.stat_lines + selected.known.amplification_lines:
			stats.append(TextCatalog.stat(line))
		UIFactory.at(UIFactory.label(body, " · ".join(stats) if not stats.is_empty() else "부여된 능력치 없음", 21), Rect2(870, 575, 465, 122))
	else:
		UIFactory.at(UIFactory.label(body, "테이블 위의 무기를 선택하면 상세 정보와 처분 가격을 확인할 수 있습니다.", 27), Rect2(70, 595, 1250, 82))

func open_detail() -> void:
	if selected != null:
		detail.show_item(selected, controller.config, controller.market, false)

func request_scrap() -> void:
	if selected == null:
		return
	var quote = TransactionService.scrap_quote(controller.config, selected)
	confirmation.dialog_text = "매입 가격: %s\n고물상 처분가: %s\n실현 손실: %s\n\n처분 수익은 일반 거래와 별도로 기록합니다.\n평판과 거래 횟수는 변하지 않습니다." % [UIFactory.money(quote.purchase), UIFactory.money(quote.revenue), UIFactory.money(quote.loss)]
	confirmation.popup_centered(Vector2i(760, 380))

func confirm_scrap() -> void:
	if selected != null:
		controller.scrap(selected)
		selected = null
		rebuild()
