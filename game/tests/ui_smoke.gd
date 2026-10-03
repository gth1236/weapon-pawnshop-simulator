extends SceneTree

var checks = 0
var failures = 0
var screenshots = false

func check(condition: bool, message: String) -> void:
	checks += 1
	if not condition:
		failures += 1
		push_error(message)

func _initialize() -> void:
	screenshots = "--screenshots" in OS.get_cmdline_user_args()
	run.call_deferred()

func capture(caption: String) -> void:
	await process_frame
	await process_frame
	if screenshots:
		await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png("res://tests/" + caption + ".png")

func click_button(button: Button) -> void:
	var event = InputEventMouseButton.new()
	event.position = button.get_global_rect().get_center()
	event.button_index = MOUSE_BUTTON_LEFT
	event.pressed = true
	root.push_input(event, true)
	event = event.duplicate()
	event.pressed = false
	root.push_input(event, true)
	await process_frame

func audit_ui(node: Node) -> void:
	if node is Control and node.is_visible_in_tree():
		if node is Label or node is Button:
			var regex = RegEx.new()
			regex.compile("[A-Za-z]")
			check(regex.search(node.text) == null, "Player-facing English: " + node.text)
			var rect = node.get_global_rect()
			check(rect.position.x >= -1 and rect.position.y >= -1 and rect.end.x <= 1921 and rect.end.y <= 1081, "Control outside viewport: " + node.text)
		check(not node is ScrollContainer, "No scroll dependence")
	for child in node.get_children():
		audit_ui(child)

func run() -> void:
	var scene = load("res://scenes/main.tscn").instantiate()
	root.add_child(scene)
	await process_frame
	check(scene.day.phase == "BETWEEN" and not scene.inventory_button.disabled, "Inventory before first visit")
	check(root.content_scale_size == Vector2i(1920, 1080), "1920x1080 baseline")
	scene.next_button.pressed.emit()
	check(scene.day.phase == "SELLER" and scene.inventory_button.disabled, "Seller enters")
	await capture("main_play")
	audit_ui(scene)
	await click_button(scene.table_button)
	var detail = scene.detail
	check(detail.visible and detail.item != null, "Dedicated appraisal view")
	if not detail.visible or detail.item == null:
		quit(1)
		return
	check(not detail.row_buttons.has("special_property") and detail.toggles.has("class_popularity") and detail.toggles.has("class_balance"), "Retired field absent and market judgements present")
	var before = detail.estimate_label.text
	for price_label in [detail.asking_label, detail.estimate_label]:
		var font = price_label.get_theme_font("font")
		var font_size = price_label.get_theme_font_size("font_size")
		check(font.get_string_size("999,999,999 골드", HORIZONTAL_ALIGNMENT_LEFT, -1, font_size).x < price_label.size.x, "Large price fits padded label")
	var actual = PriceCalculator.calculate(scene.day.config, detail.item, scene.day.market).true_appraised_price
	await capture("appraisal_before")
	for section in PlayerJudgement.SECTIONS:
		var row = detail.row_buttons[section]
		check(row.get_theme_stylebox("normal").bg_color.a == 0, "Detail row has no resting background")
		var motion = InputEventMouseMotion.new()
		motion.position = row.get_global_rect().get_center()
		root.push_input(motion, true)
		await process_frame
		check(row.is_hovered(), "Detail row receives hover")
		await click_button(row)
		if section in AppraisalService.FIELDS:
			check(detail.toggles[section].disabled, "Unrevealed include disabled")
			check(detail.grade_buttons[0].disabled, "Unrevealed judgement disabled")
			await create_timer(0.36).timeout
			check(detail.item.known.properties[section].knowledge_state == "EXACT", "Exact reveal")
		check(detail.item.judgement.entries[section].selected_value_tier == -1, "No auto judgement")
		check(not detail.toggles[section].button_pressed, "No auto include")
		var reveal_estimate = detail.estimate_label.text
		detail.grade_buttons.back().pressed.emit()
		check(detail.item.judgement.entries[section].selected_value_tier == PlayerJudgement.option_count(section) - 1, "Grade chosen")
		check(detail.estimate_label.text == reveal_estimate, "Grade alone does not include")
		detail.toggles[section].button_pressed = true
		check(detail.item.judgement.entries[section].included, "Include selected")
		if section == "amplification":
			await capture("amplification_choices")
			audit_ui(detail)
	check(before != detail.estimate_label.text, "Estimate updates")
	check(PriceCalculator.calculate(scene.day.config, detail.item, scene.day.market).true_appraised_price == actual, "True price unchanged by judgement")
	var kept = detail.estimate_label.text
	detail.back_button.pressed.emit()
	scene.table_button.pressed.emit()
	check(detail.estimate_label.text == kept, "Reopening preserves judgements")
	await capture("appraisal_judged")
	audit_ui(detail)
	detail.buy_button.pressed.emit()
	check(scene.day.phase == "BETWEEN" and scene.day.state.inventory.size() == 1, "Buy returns to shop")
	scene.inventory_button.pressed.emit()
	var inventory = scene.inventory_screen
	check(inventory.visible and inventory.slot_buttons.size() == 20, "Two rows of ten slots")
	check(inventory.slot_buttons[10].disabled, "Locked expansion slots")
	inventory.slot_buttons[0].pressed.emit()
	inventory.expand_button.pressed.emit()
	check(scene.day.state.capacity == 11, "Manual expansion")
	check("빈 슬롯" in inventory.slot_buttons[10].text, "Expanded slot opens")
	await capture("inventory_slots")
	audit_ui(inventory)
	inventory.inspect_button.pressed.emit()
	check(inventory.detail.visible and inventory.detail.estimate_label.text == kept, "Owned item keeps judgement")
	inventory.detail.back_button.pressed.emit()
	inventory.scrap_button.pressed.emit()
	check(inventory.confirmation.visible and "실현 손실" in inventory.confirmation.dialog_text, "Korean scrap confirmation")
	var rep = scene.day.state.reputation
	var trades = scene.day.state.trade_count
	inventory.confirmation.confirmed.emit()
	inventory.confirmation.hide()
	check(scene.day.state.scrapped_items == 1 and scene.day.state.reputation == rep and scene.day.state.trade_count == trades, "Scrap excludes reputation and trades")
	inventory.back_button.pressed.emit()
	# Exercise cancellation while the appraisal timer is running.
	scene.next_button.pressed.emit()
	scene.table_button.pressed.emit()
	detail.row_buttons.refining.pressed.emit()
	detail.back_button.pressed.emit()
	await create_timer(0.36).timeout
	scene.table_button.pressed.emit()
	check(detail.item.known.properties.refining.knowledge_state != "EXACT", "Cancelled tool does not reveal later")
	detail.refuse_button.pressed.emit()
	check(scene.day.state.refused_purchases == 1, "Refuse returns to shop")
	while scene.day.phase != "COMPLETE":
		if scene.day.phase == "BETWEEN":
			scene.next_button.pressed.emit()
		elif scene.day.phase == "SELLER":
			scene.table_button.pressed.emit()
			detail.buy_button.pressed.emit()
			if scene.day.phase == "SELLER":
				detail.refuse_button.pressed.emit()
		else:
			scene.next_button.pressed.emit()
		await process_frame
	check(scene.receipt.visible and scene.day.guest_number == 8, "Eighth visit shows receipt")
	await capture("daily_receipt")
	audit_ui(scene.receipt)
	# Worst-size public stat payload and fully occupied 20-slot layout.
	var fixtures = JSON.parse_string(FileAccess.get_file_as_string("res://tests/reference_cases.json"))
	var largest = fixtures[0]
	for sample in fixtures:
		if sample.weapon.stat_lines.size() + sample.weapon.amplification_lines.size() > largest.weapon.stat_lines.size() + largest.weapon.amplification_lines.size():
			largest = sample
	var test_day = DayController.new()
	test_day.state.capacity = 20
	for i in range(20):
		var truth = WeaponTrueState.new(largest.weapon)
		var known = AppraisalService.create_knowledge(test_day.config, truth, test_day.rng)
		var owned = WeaponData.new(truth, known, largest.seller)
		owned.final_purchase_price = 1000
		test_day.state.inventory.append(owned)
	scene.receipt.hide()
	inventory.open(test_day)
	inventory.slot_buttons[19].pressed.emit()
	await capture("inventory_full")
	check(inventory.expand_button.disabled, "Max capacity expansion button disabled")
	audit_ui(inventory)
	inventory.inspect_button.pressed.emit()
	await capture("appraisal_full_stats")
	audit_ui(inventory.detail)
	check(inventory.detail.public_stats_label.get_rect().end.y < inventory.detail.row_buttons.normal_stat.position.y, "Full public stats do not overlap appraisal rows")
	scene.queue_free()
	await process_frame
	print("UI CHECKS: %d | FAILURES: %d" % [checks, failures])
	quit(0 if failures == 0 else 1)
