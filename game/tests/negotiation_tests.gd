extends SceneTree

var failures = 0
var checks = 0

func check(ok: bool, description: String) -> void:
	checks += 1
	if not ok:
		failures += 1
		push_error(description)

func _initialize() -> void:
	run.call_deferred()

func run() -> void:
	var c = Balance.load_config()
	for purpose in c.seller_negotiation.attempts_by_selling_purpose:
		var guest = {"selling_purpose": purpose, "market_knowledge": "NONE", "trade_attitude": "NORMAL"}
		var n = SellerNegotiation.new(c, guest, 2000)
		var retry = SellerNegotiation.new(c, guest, 2000)
		check(n.remaining_offer_attempts == (1 if purpose == "EMERGENCY_CASH" else 2), "Purpose attempts from spec")
		check(n.evaluate(c, guest, 2000) == "ACCEPTED", "Exact asking accepted")
		check(n.evaluate(c, guest, 1) == "ACCEPTED" and n.last_offer == 2000, "Closed agreement cannot be reused")
		var result = retry.evaluate(c, guest, 1000)
		if purpose == "EMERGENCY_CASH":
			check(result == "FAILED" and retry.remaining_offer_attempts == 0, "One attempt expires")
		else:
			check(result == "OPEN" and retry.current_asking == 1900 and retry.last_offer == 1000 and retry.remaining_offer_attempts == 1, "Deterministic 5 percent counter")
			check(retry.evaluate(c, guest, 1900) == "ACCEPTED", "Counter accepted on final attempt")
	var high = {"selling_purpose": "UPGRADE_PURCHASE", "market_knowledge": "HIGH", "trade_attitude": "NORMAL"}
	var held = SellerNegotiation.new(c, high, 2000)
	held.evaluate(c, high, 1000)
	check(held.current_asking == 2000, "High knowledge holds asking")
	check(held.evaluate(c, high, 1999) == "FAILED", "Final low offer breaks negotiation")
	var guest = {"selling_purpose": "GREEDY_SELLING", "market_knowledge": "NONE", "trade_attitude": "SCAMMER"}
	var scam = SellerNegotiation.new(c, guest, 2000)
	scam.evaluate(c, guest, 1000)
	check(scam.current_asking == 2000, "Scammer holds asking")
	guest.trade_attitude = "NORMAL"
	var close_offer = SellerNegotiation.new(c, guest, 2000)
	close_offer.evaluate(c, guest, 1990)
	check(close_offer.current_asking == 1991, "Counter remains above rejected offer")
	var day = DayController.new()
	day.next_guest()
	var item = day.item
	var true_price = PriceCalculator.calculate(c, item, day.market).true_appraised_price
	var base = int(c.price.base_prices[str(item.known.tier)])
	for section in ["unique_property", "amplification"]:
		AppraisalService.reveal(c, item, section, c.appraisal.property_tools.values())
		var visible = item.known.player_view()
		var mapping = c.player_estimate[section]
		for i in range(PlayerJudgement.option_count(section)):
			check(item.judgement.choose(section, i, visible), "Every category option accepted")
			check(item.judgement.include(section, true, visible), "Category include accepted")
			var expected = PriceCalculator.finish(c.price, visible.tier, c.price[mapping.table][mapping.keys[i]])
			check(PriceCalculator.estimate(c, visible, item.judgement) == expected, "Category maps to exact reference contribution")
			item.judgement.include(section, false, visible)
			check(PriceCalculator.estimate(c, visible, item.judgement) == base, "Unchecked category omitted")
		check(not item.judgement.choose(section, PlayerJudgement.option_count(section), visible), "Invalid category option rejected")
	check(PriceCalculator.calculate(c, item, day.market).true_appraised_price == true_price, "Category selection cannot mutate true price")
	# Live controller + UI: known fixture asking sits just above the tier-only estimate.
	var scene = load("res://scenes/main.tscn").instantiate()
	root.add_child(scene)
	await process_frame
	scene.next_button.pressed.emit()
	var current = scene.day
	current.guest.selling_purpose = "UPGRADE_PURCHASE"
	current.guest.market_knowledge = "NONE"
	current.item.seller = current.guest.duplicate()
	base = int(current.config.price.base_prices[str(current.item.known.tier)])
	current.negotiation = SellerNegotiation.new(current.config, current.guest, base + 1)
	scene.table_button.pressed.emit()
	var panel = scene.detail
	var cash_before = current.state.cash
	panel.buy_button.pressed.emit()
	check(current.phase == "SELLER" and current.negotiation.remaining_offer_attempts == 1, "Rejected offer stays in seller UI")
	check(current.state.cash == cash_before and current.state.inventory.is_empty(), "Counter has no money/inventory effect")
	check(current.negotiation.last_offer == base and "너무 낮아" in panel.dialogue_label.text, "Actual estimate sent and counter dialogue shown")
	check("1회" in panel.negotiation_label.text and str(base + 1) in current.message, "Remaining attempts and current ask visible")
	if "--screenshots" in OS.get_cmdline_user_args():
		await process_frame
		await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png("res://tests/seller_counter_offer.png")
	panel.back_button.pressed.emit()
	scene.table_button.pressed.emit()
	check(current.negotiation.remaining_offer_attempts == 1, "Reopening does not reset negotiation")
	panel.row_buttons.normal_stat.pressed.emit()
	panel.grade_buttons[3].pressed.emit()
	panel.toggles.normal_stat.button_pressed = true
	var accepted_offer = PriceCalculator.estimate(current.config, current.item.known.player_view(), current.item.judgement)
	var owned = current.item
	var true_before = PriceCalculator.calculate(current.config, owned, current.market).true_appraised_price
	panel.buy_button.pressed.emit()
	check(current.phase == "BETWEEN" and current.state.inventory.size() == 1, "Adjusted estimate accepted")
	check(current.state.cash == cash_before - accepted_offer and owned.final_purchase_price == accepted_offer and current.state.purchase_spending == accepted_offer, "Offer used as actual purchase cost")
	check(current.state.reputation == ProgressionService.purchase_delta(current.config, owned.seller, float(accepted_offer) / true_before), "Reputation uses actual offer ratio")
	check(TransactionService.scrap_quote(current.config, owned).revenue == Balance.money(accepted_offer * 0.5), "Scrap uses negotiated purchase cost")
	# Next seller: two low offers, no accepted transaction, then a guarded repeat click.
	scene.next_button.pressed.emit()
	current.guest.selling_purpose = "UPGRADE_PURCHASE"
	current.negotiation = SellerNegotiation.new(current.config, current.guest, 90000)
	scene.table_button.pressed.emit()
	var trades = current.state.trade_count
	cash_before = current.state.cash
	panel.buy_button.pressed.emit()
	panel.buy_button.pressed.emit()
	check(current.phase == "BETWEEN" and current.negotiation.status == "FAILED", "Two low offers break deal")
	check(current.state.trade_count == trades and current.state.cash == cash_before and current.state.refused_purchases == 1, "Broken deal counted once, no transaction")
	current.buy()
	check(current.state.refused_purchases == 1, "Repeated click cannot count failure twice")
	# Cash validation leaves the offer budget untouched.
	scene.next_button.pressed.emit()
	current.state.cash = 0
	var attempts = current.negotiation.remaining_offer_attempts
	current.buy()
	check(current.negotiation.remaining_offer_attempts == attempts and current.negotiation.last_offer == -1, "Unaffordable proposal consumes no attempt")
	current.refuse()
	# Eighth seller failure must still finish the day automatically.
	current.guest_number = 7
	current.sequence[7] = "SELL_TO_SHOP"
	current.state.cash = 100000
	current.next_guest()
	current.guest.selling_purpose = "EMERGENCY_CASH"
	current.negotiation = SellerNegotiation.new(current.config, current.guest, 90000)
	current.buy()
	check(current.phase == "COMPLETE" and scene.receipt.visible, "Final failed negotiation triggers receipt")
	scene.queue_free()
	# Give the audio mixer time to release voices before terminating the test.
	root.get_node("Sfx").player.stop()
	await create_timer(0.2).timeout
	print("NEGOTIATION CHECKS: %d | FAILURES: %d" % [checks, failures])
	quit(0 if failures == 0 else 1)
