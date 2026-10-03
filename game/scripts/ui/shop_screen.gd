extends Control

var day: DayController
var hud: Label
var customer: Label
var dialogue: Label
var portrait_label: Label
var portrait_image: TextureRect
var weapon_image: TextureRect
var weapon_caption: Label
var table_button: Button
var next_button: Button
var inventory_button: Button
var detail: ItemDetailPanel
var inventory_screen: InventoryScreen
var receipt: DailyReceipt
var sounded_trades = 0

func _ready() -> void:
	set_meta("painted_ui", true)
	UIFactory.setup_theme(self)
	UIFactory.backdrop(self)
	VisualAssets.image(self, VisualAssets.SHOP, Rect2(0, 0, 1920, 1080))
	var seed_input = DayController.DEFAULT_SEED
	for argument in OS.get_cmdline_user_args():
		if argument.begins_with("--seed="):
			seed_input = int(argument.trim_prefix("--seed="))
	day = DayController.new(seed_input)
	# Use the wooden board region; transparent hanging-rope padding is not stretched.
	VisualAssets.patch(self, VisualAssets.STATUS, Rect2(28, 26, 470, 150), Vector4(45, 36, 45, 36), 0.8, Rect2(174, 191, 446, 230))
	hud = UIFactory.label(self, "", 25)
	UIFactory.at(hud, Rect2(82, 51, 362, 100))
	hud.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	hud.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	UIFactory.at(UIFactory.label(self, "무기 전당포", 42), Rect2(770, 42, 480, 66))
	inventory_button = UIFactory.button(self, "보유 재고", func(): inventory_screen.open(day))
	UIFactory.at(inventory_button, Rect2(1658, 28, 230, 135))
	# Let the dialogue foreground hide the authored lower sprite edge.
	portrait_image = VisualAssets.image(self, null, Rect2(305, 245, 750, 700))
	portrait_label = UIFactory.label(self, "손님을 기다리는 중", 36)
	UIFactory.at(portrait_label, Rect2(435, 686, 420, 80))
	portrait_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	VisualAssets.patch(self, VisualAssets.DIALOGUE, Rect2(28, 800, 1314, 254), Vector4(120, 235, 120, 115), 0.4)
	customer = UIFactory.label(self, "", 30)
	UIFactory.at(customer, Rect2(70, 811, 1210, 43))
	dialogue = UIFactory.label(self, "", 28)
	UIFactory.at(dialogue, Rect2(70, 866, 1210, 102))
	next_button = UIFactory.button(self, "손님 맞이하기", continue_day)
	UIFactory.at(next_button, Rect2(980, 982, 334, 50))
	VisualAssets.image(self, VisualAssets.TABLE, Rect2(1335, 520, 580, 580))
	weapon_image = VisualAssets.image(self, null, Rect2(1435, 353, 390, 390))
	table_button = Button.new()
	table_button.pressed.connect(func(): Sfx.perform(open_detail))
	add_child(table_button)
	for style in ["normal", "hover", "pressed", "disabled"]:
		table_button.add_theme_stylebox_override(style, StyleBoxEmpty.new())
	table_button.alignment = HORIZONTAL_ALIGNMENT_CENTER
	table_button.add_theme_constant_override("outline_size", 6)
	table_button.add_theme_color_override("font_outline_color", Color("241e1c"))
	UIFactory.at(table_button, Rect2(1410, 340, 460, 468))
	table_button.add_theme_font_size_override("font_size", 28)
	weapon_caption = UIFactory.label(self, "", 27)
	weapon_caption.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	UIFactory.at(weapon_caption, Rect2(1410, 747, 460, 67))
	detail = ItemDetailPanel.new()
	add_child(detail)
	detail.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	detail.hide()
	detail.buy_requested.connect(day.buy)
	detail.refuse_requested.connect(day.refuse)
	inventory_screen = InventoryScreen.new()
	inventory_screen.set_meta("painted_ui", false)
	add_child(inventory_screen)
	inventory_screen.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	inventory_screen.hide()
	receipt = DailyReceipt.new()
	receipt.set_meta("painted_ui", false)
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
	var committed_trades = s.seller_trades + s.buyer_trades + s.scrapped_items
	if committed_trades > sounded_trades:
		Sfx.play("gold")
	sounded_trades = committed_trades
	hud.text = "%d일차 · 손님 %d / 8\n보유 자금  %s\n평판 %.2f" % [s.day, day.guest_number, UIFactory.money(s.cash), s.reputation]
	customer.text = "전당포 주인" if day.guest.is_empty() else "%s · %s · %d레벨" % [day.guest.name, TextCatalog.CLASSES[day.guest.adventurer_class], day.guest.adventurer_level]
	portrait_image.visible = day.phase in ["SELLER", "BUYER"]
	portrait_image.texture = VisualAssets.CHARACTERS.get(day.guest.get("adventurer_class", ""))
	portrait_label.text = "손님을 기다리는 중"
	portrait_label.visible = not portrait_image.visible
	dialogue.text = day.message
	table_button.disabled = day.phase != "SELLER"
	weapon_image.texture = null if day.item == null else VisualAssets.WEAPONS.get(day.item.known.item_type)
	weapon_caption.text = "빈 테이블" if day.item == null else "%s · %d등급\n눌러서 살펴보기" % [TextCatalog.weapon(day.item.known.item_type), day.item.known.tier]
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
