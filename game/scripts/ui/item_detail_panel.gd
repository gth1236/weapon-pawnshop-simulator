class_name ItemDetailPanel
extends Control

signal buy_requested
signal refuse_requested
signal closed

var item: WeaponData
var config: Dictionary
var market: Dictionary
var is_seller = false
var busy = false
var generation = 0
var active_section = "normal_stat"
var row_buttons: Dictionary = {}
var toggles: Dictionary = {}
var grade_buttons: Array = []
var estimate_label: Label
var dialogue_label: Label
var judgement_title: Label
var judgement_result: Label
var judgement_status: Label
var public_stats_label: Label
var buy_button: Button
var refuse_button: Button
var back_button: Button
var customer_words = ""
var negotiation: SellerNegotiation
var asking_label: Label
var negotiation_label: Label
var grade_area: Control
var grade_section = ""
var weapon_image: TextureRect

func show_item(weapon: WeaponData, balance: Dictionary, current_market: Dictionary, seller = true, words = "보유한 무기를 자세히 살펴보세요.", negotiation_state: SellerNegotiation = null) -> void:
	generation += 1
	busy = false
	item = weapon
	config = balance
	market = current_market
	is_seller = seller
	customer_words = words
	negotiation = negotiation_state
	active_section = "normal_stat"
	rebuild()
	show()

func close_panel() -> void:
	generation += 1
	busy = false
	hide()
	closed.emit()

func rebuild() -> void:
	set_meta("painted_ui", is_seller)
	UIFactory.clear(self)
	row_buttons.clear()
	toggles.clear()
	grade_buttons.clear()
	grade_section = ""
	UIFactory.backdrop(self)
	if is_seller:
		VisualAssets.image(self, VisualAssets.APPRAISAL, Rect2(0, 0, 1920, 1080))
	UIFactory.at(UIFactory.label(self, "무기 감정", 42), Rect2(32, 26, 480, 70))
	back_button = UIFactory.button(self, "상점으로" if is_seller else "재고로 돌아가기", close_panel)
	UIFactory.at(back_button, Rect2(1628, 26, 260, 62))
	negotiation_label = UIFactory.label(self, "", 24)
	UIFactory.at(negotiation_label, Rect2(40, 111, 480, 85))
	weapon_image = null
	if is_seller:
		weapon_image = VisualAssets.image(self, VisualAssets.WEAPONS.get(item.known.item_type), Rect2(48, 216, 460, 460))
		VisualAssets.patch(self, VisualAssets.DIALOGUE, Rect2(32, 760, 492, 290), Vector4(120, 235, 120, 115), 0.28)
	else:
		UIFactory.panel(self, Rect2(32, 200, 492, 510))
		var image_label = UIFactory.label(self, "%s\n\n무기 이미지\n임시 표시" % TextCatalog.weapon(item.known.item_type), 38)
		UIFactory.at(image_label, Rect2(65, 330, 426, 290))
		image_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		UIFactory.panel(self, Rect2(32, 760, 492, 290))
	UIFactory.at(UIFactory.label(self, "손님의 말" if is_seller else "보유 무기", 26), Rect2(54, 765, 442, 44))
	dialogue_label = UIFactory.label(self, customer_words, 26)
	UIFactory.at(dialogue_label, Rect2(60, 825, 434, 201))
	if is_seller:
		# Reuse authored header/body regions independently to fit all nine rows.
		VisualAssets.patch(self, VisualAssets.ITEM_INTERFACE, Rect2(554, 26, 802, 185), Vector4(42, 30, 42, 30), 1.0, Rect2(28, 22, 780, 172))
		VisualAssets.patch(self, VisualAssets.ITEM_INTERFACE, Rect2(554, 213, 802, 837), Vector4(42, 30, 42, 30), 1.0, Rect2(28, 198, 780, 660))
	else:
		UIFactory.panel(self, Rect2(554, 26, 802, 1024))
	UIFactory.at(UIFactory.label(self, TextCatalog.weapon(item.known.item_type), 40), Rect2(600, 50, 712, 62))
	UIFactory.at(UIFactory.label(self, "무기 종류: %s  /  기준 직업: %s\n아이템 등급: %d" % [TextCatalog.weapon(item.known.item_type), TextCatalog.CLASSES[item.known.required_class], item.known.tier], 25), Rect2(600, 126, 712, 82))
	var public_stats = []
	for line in item.known.stat_lines + item.known.amplification_lines:
		public_stats.append(TextCatalog.stat(line))
	public_stats_label = UIFactory.label(self, "공개 능력치\n" + ("  ·  ".join(public_stats) if not public_stats.is_empty() else "부여된 능력치 없음"), 23)
	UIFactory.at(public_stats_label, Rect2(598, 246, 714, 89))
	for i in range(PlayerJudgement.SECTIONS.size()):
		var section = PlayerJudgement.SECTIONS[i]
		var y = 349 + i * 76
		var row = UIFactory.detail_row(self, func(): select_section(section))
		row.add_theme_font_size_override("font_size", 21)
		UIFactory.at(row, Rect2(578, y, 550, 70))
		row_buttons[section] = row
		var toggle = CheckBox.new()
		toggle.text = "가격 반영"
		toggle.add_theme_font_size_override("font_size", 23)
		toggle.toggled.connect(func(enabled):
			var was_included = item.judgement.entries[section].included
			item.judgement.include(section, enabled, item.known.player_view())
			if was_included != item.judgement.entries[section].included:
				Sfx.play("check")
			refresh_controls())
		add_child(toggle)
		UIFactory.at(toggle, Rect2(1143, y + 16, 190, 50))
		toggles[section] = toggle
	UIFactory.panel(self, Rect2(1386, 130, 502, 558))
	judgement_title = UIFactory.label(self, "", 32)
	UIFactory.at(judgement_title, Rect2(1410, 148, 455, 52))
	judgement_result = UIFactory.label(self, "", 26)
	UIFactory.at(judgement_result, Rect2(1410, 208, 455, 65))
	UIFactory.at(UIFactory.label(self, "결과를 보고 가치를 직접 판단하세요.", 22), Rect2(1410, 278, 455, 42))
	grade_area = Control.new()
	add_child(grade_area)
	UIFactory.at(grade_area, Rect2(1410, 326, 455, 244))
	judgement_status = UIFactory.label(self, "", 22)
	UIFactory.at(judgement_status, Rect2(1410, 590, 455, 76))
	UIFactory.panel(self, Rect2(1386, 718, 502, 91))
	asking_label = UIFactory.label(self, "", 24)
	UIFactory.at(asking_label, Rect2(1430, 734, 414, 59))
	asking_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	asking_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	UIFactory.panel(self, Rect2(1386, 832, 502, 91))
	estimate_label = UIFactory.label(self, "", 24)
	UIFactory.at(estimate_label, Rect2(1430, 848, 414, 59))
	estimate_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	estimate_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	buy_button = UIFactory.button(self, "이 가격으로 매입 제안", func(): buy_requested.emit())
	UIFactory.at(buy_button, Rect2(1386, 948, 320, 78))
	refuse_button = UIFactory.button(self, "매입 거절", func(): refuse_requested.emit())
	UIFactory.at(refuse_button, Rect2(1722, 948, 166, 78))
	buy_button.visible = is_seller
	refuse_button.visible = is_seller
	if not is_seller:
		UIFactory.at(UIFactory.label(self, "선택한 판단과 가격 반영 여부는\n이 무기에 계속 보관됩니다.", 23), Rect2(1396, 946, 482, 85))
	refresh_controls()

func result_text(section: String) -> String:
	if section in PlayerJudgement.MARKET_SECTIONS:
		return "기준 직업의 시장 상황을 추정하세요"
	if section in ["normal_stat", "high_stat"]:
		var values = []
		for line in item.known.stat_lines:
			var is_normal = line.stat_id in config.numeric_stats.normal_stat_ids
			if (section == "normal_stat" and is_normal) or (section == "high_stat" and line.stat_id in ["attack", "magic_power"]):
				values.append(TextCatalog.stat(line))
		return " · ".join(values) if not values.is_empty() else "해당 능력치 없음"
	return TextCatalog.property_result(section, item.known.player_view().properties[section].displayed_value)

func hint_color(section: String) -> Color:
	if section in PlayerJudgement.MARKET_SECTIONS:
		return UIFactory.MUTED
	if not PlayerJudgement.revealed(item.known.player_view(), section):
		return UIFactory.MUTED
	# A subtle visual observation, never a selected/recommended judgement.
	if section in ["normal_stat", "high_stat"]:
		return Color("aad3dc")
	var value = item.known.properties[section].displayed_value
	if section == "stability":
		return Color("b6d7be") if value >= 80 else Color("d7b477") if value >= 40 else Color("d7a3a0")
	if section == "refining":
		return Color("c7bce6") if value >= 7 else Color("aad3dc")
	return Color("c7bce6") if value in ["PERFECT", "HIGH", "THREE_LINE_HIGH"] else Color("d7a3a0") if value in ["BAD", "ZERO_LINE"] else Color("aad3dc")

func refresh_controls() -> void:
	if grade_section != active_section:
		rebuild_grade_choices()
	var view = item.known.player_view()
	for section in PlayerJudgement.SECTIONS:
		var revealed = PlayerJudgement.revealed(view, section)
		var entry = item.judgement.entries[section]
		var action_text = "감정하기" if not revealed else "판단 선택" if entry.selected_value_tier < 0 else "내 판단: " + TextCatalog.judgement_options(section)[entry.selected_value_tier]
		row_buttons[section].text = "%s  ·  %s\n%s" % [TextCatalog.SECTIONS[section], action_text, result_text(section)]
		row_buttons[section].add_theme_color_override("font_color", hint_color(section))
		toggles[section].disabled = not revealed or entry.selected_value_tier < 0
		toggles[section].set_pressed_no_signal(entry.included)
		var grade_name = TextCatalog.judgement_options(section)[entry.selected_value_tier] if entry.selected_value_tier >= 0 else "미선택"
		toggles[section].tooltip_text = "내 판단: %s\n가격 계산에 반영" % grade_name
	judgement_title.text = TextCatalog.SECTIONS[active_section] + " · 가치 판단"
	judgement_result.text = result_text(active_section)
	judgement_result.add_theme_color_override("font_color", hint_color(active_section))
	var active = item.judgement.entries[active_section]
	for i in range(grade_buttons.size()):
		grade_buttons[i].disabled = busy or not PlayerJudgement.revealed(view, active_section)
		grade_buttons[i].set_pressed_no_signal(active.selected_value_tier == i)
	judgement_status.text = "감정한 뒤 판단을 선택하세요." if not PlayerJudgement.revealed(view, active_section) else "판단을 선택한 뒤 해당 항목의\n가격 반영에 체크하세요." if active.selected_value_tier < 0 else "내 판단: %s · %s" % [TextCatalog.judgement_options(active_section)[active.selected_value_tier], "계산에 반영 중" if active.included else "아직 계산에 미반영"]
	if is_seller:
		var asking = negotiation.current_asking if negotiation != null else PriceCalculator.calculate(config, item, market).asking_price
		asking_label.text = "손님의 요구 가격\n" + UIFactory.money(asking)
		if negotiation != null:
			negotiation_label.text = "마지막 제안: %s\n남은 흥정 횟수: %d회" % ["없음" if negotiation.last_offer < 0 else UIFactory.money(negotiation.last_offer), negotiation.remaining_offer_attempts]
	else:
		asking_label.text = "현재 감정가\n" + UIFactory.money(PriceCalculator.calculate(config, item, market).true_appraised_price)
	estimate_label.text = "내가 계산한 예상 가격\n" + UIFactory.money(PriceCalculator.estimate(config, view, item.judgement))

func choose_grade(grade: int) -> void:
	if busy:
		return
	item.judgement.choose(active_section, grade, item.known.player_view())
	refresh_controls()

func select_section(section: String) -> void:
	if busy:
		return
	active_section = section
	refresh_controls()
	if not PlayerJudgement.revealed(item.known.player_view(), section):
		appraise(section)

func appraise(section: String) -> void:
	if busy or not AppraisalService.FIELDS.has(section):
		return
	busy = true
	Sfx.play("appraisal")
	var ticket = generation
	row_buttons[section].text = TextCatalog.SECTIONS[section] + "\n도구로 조사하는 중 · · ·"
	judgement_result.text = "감정 도구로 확인하고 있습니다…"
	await get_tree().create_timer(0.3).timeout
	if not is_inside_tree() or ticket != generation or not visible:
		return
	AppraisalService.reveal(config, item, section, config.appraisal.property_tools.values())
	busy = false
	refresh_controls()

func rebuild_grade_choices() -> void:
	UIFactory.clear(grade_area)
	grade_buttons.clear()
	grade_section = active_section
	var options = TextCatalog.judgement_options(active_section)
	var group = ButtonGroup.new()
	for i in range(options.size()):
		var choice = UIFactory.button(grade_area, options[i], func(): choose_grade(i))
		choice.toggle_mode = true
		choice.button_group = group
		UIFactory.at(choice, Rect2((i % 2) * 232, (i / 2) * 60, 220, 52))
		grade_buttons.append(choice)
