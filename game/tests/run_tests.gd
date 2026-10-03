extends SceneTree

var checks = 0
var failures = 0

func check(condition: bool, message: String) -> void:
	checks += 1
	if not condition:
		failures += 1
		push_error(message)

func _initialize() -> void:
	run.call_deferred()

func run() -> void:
	var day = DayController.new(12345)
	var c = day.config
	check(day.state.cash == 100000 and day.state.debt_remaining == 0, "Starting cash/debt")
	check(day.state.capacity == 10 and c.economy.maximum_inventory_capacity == 20, "Capacity config")
	check(c.economy.inventory_expansion_cost == 10000, "Expansion cost")
	check(day.state.weekly_operating_cost(c, 7) == 14000, "Weekly cost")
	var seller_eights = 0
	for seed_index in range(1000):
		var replay = DayController.new(seed_index)
		check(replay.sequence == DayController.new(seed_index).sequence, "Seed repeatability")
		check(replay.sequence.slice(0, 4) == ["SELL_TO_SHOP", "SELL_TO_SHOP", "SELL_TO_SHOP", "SELL_TO_SHOP"], "First four sellers")
		check(replay.sequence.slice(4, 7) == ["BUY_FROM_SHOP", "BUY_FROM_SHOP", "BUY_FROM_SHOP"], "Next three buyers")
		seller_eights += int(replay.sequence[7] == "SELL_TO_SHOP")
	check(seller_eights > 430 and seller_eights < 570, "Guest 8 approximately 50/50 over seeds")
	check(day.expand() and day.state.capacity == 11 and day.state.cash == 90000, "Manual expansion")
	day.next_guest()
	check(not day.expand(), "No expansion during visit")
	var weapon = day.item
	var original = PriceCalculator.calculate(c, weapon, day.market).true_appraised_price
	var judgement = weapon.judgement
	check(not weapon.truth.values.has("special_stat_grade") and not weapon.known.properties.has("special_property"), "Special removed from runtime data")
	check(not judgement.choose("refining", 3, weapon.known.player_view()), "Cannot judge hidden result")
	check(not judgement.include("refining", true, weapon.known.player_view()), "Cannot include hidden result")
	for property in AppraisalService.FIELDS:
		check(weapon.known.properties[property].knowledge_state == "UNAPPRAISED_GUESS", "Stored unassisted guess")
		check(weapon.known.player_view().properties[property].displayed_value == null, "Guess masked in Day 1 UI")
		check(not AppraisalService.reveal(c, weapon, property, []), "Missing tool cannot reveal")
		check(AppraisalService.reveal(c, weapon, property, c.appraisal.property_tools.values()), "Reveal succeeds")
		check(weapon.known.properties[property].known_exact_value == weapon.truth.values[AppraisalService.FIELDS[property]], "Exact reveal")
		check(judgement.entries[property].grade == -1 and not judgement.entries[property].included, "Reveal never judges or includes")
	check(weapon.truth.values.is_read_only(), "True state is immutable")
	var visible = weapon.known.player_view()
	var base = int(c.price.base_prices[str(weapon.known.tier)])
	check(PriceCalculator.estimate(c, visible, judgement) == base, "Reveal alone keeps base estimate")
	for section in PlayerJudgement.SECTIONS:
		check(judgement.choose(section, PlayerJudgement.option_count(section) - 1, visible), "Player can choose grade")
	check(PriceCalculator.estimate(c, visible, judgement) == base, "Judgement alone excluded")
	for section in PlayerJudgement.SECTIONS:
		check(judgement.include(section, true, visible), "Explicit include succeeds")
	var estimated = PriceCalculator.estimate(c, visible, judgement)
	check(estimated != base, "Included judgements affect estimate")
	weapon.known.properties.stability = WeaponKnownState.field(0, "EXACT")
	check(PriceCalculator.calculate(c, weapon, day.market).true_appraised_price == original, "Known edits never change true price")
	check(PriceCalculator.estimate(c, weapon.known.player_view(), judgement) == estimated, "Actual reveal does not override player judgement")
	judgement.choose("stability", 0, visible)
	check(PriceCalculator.estimate(c, visible, judgement) != estimated, "Different player grade changes estimate")
	check(PriceCalculator.calculate(c, weapon, day.market).true_appraised_price == original, "Player judgement never changes true price")
	judgement.include("stability", false, visible)
	var without_stability = PriceCalculator.estimate(c, visible, judgement)
	judgement.choose("stability", 3, visible)
	check(PriceCalculator.estimate(c, visible, judgement) == without_stability, "Unchecked grade changes have no price effect")
	var asking = PriceCalculator.estimate(c, weapon.known.player_view(), weapon.judgement)
	day.buy()
	check(day.state.inventory.size() == 1 and day.state.cash == 90000 - asking, "Seller purchase accounting")
	check(day.state.trade_count == 1 and day.state.seller_trades == 1, "Seller trade counters")
	var reputation = day.state.reputation
	var cash = day.state.cash
	check(day.scrap(weapon), "Junk disposal")
	check(day.state.cash == cash + Balance.money(asking * 0.5) and day.state.inventory.is_empty(), "Junk returns half purchase")
	check(day.state.reputation == reputation and day.state.trade_count == 1 and day.state.buyer_trades == 0 and day.state.realized_trade_profit == 0 and day.state.sale_revenue == 0, "Junk excluded from normal trades")
	check(not day.scrap(weapon), "Cannot scrap twice")
	check(Balance.money(101 * 0.5) == 50 and Balance.money(103 * 0.5) == 52, "Python ties-to-even scrap")
	day.next_guest()
	var before = day.state.cash
	day.refuse()
	check(day.state.cash == before and day.state.inventory.is_empty() and day.state.refused_purchases == 1, "Refusal accounting")
	while day.phase != "COMPLETE":
		if day.phase == "BETWEEN":
			day.next_guest()
		elif day.phase == "SELLER":
			day.refuse()
		else:
			day.resolve_buyer()
	check(day.guest_number == 8 and day.phase == "COMPLETE", "Eight visits complete day")
	day.next_guest()
	check(day.guest_number == 8, "No ninth visit")
	var capacity_state = ShopState.new(c)
	for i in range(10):
		check(TransactionService.expand(c, capacity_state), "Expand each slot")
	check(capacity_state.capacity == 20 and capacity_state.cash == 0, "Maximum expansion accounting")
	capacity_state.cash = 100000
	check(not TransactionService.expand(c, capacity_state), "Maximum capacity enforced")
	capacity_state.capacity = 10
	capacity_state.cash = 9999
	check(not TransactionService.expand(c, capacity_state), "Insufficient expansion cash")
	capacity_state.cash = 0
	check(not TransactionService.buy(c, capacity_state, weapon, day.market, 1000).success, "Insufficient purchase cash")
	capacity_state.cash = 100000
	capacity_state.capacity = 0
	check(not TransactionService.buy(c, capacity_state, weapon, day.market, 1000).success, "Full inventory blocks purchase")
	verify_reference(c)
	# Stress the Godot generator across all progression ranges and foreign branches.
	var modes = {}
	for index in range(1000):
		var rng = RandomNumberGenerator.new()
		rng.seed = index
		var state = ShopState.new(c)
		state.reputation = index
		state.trade_count = index
		var guest = CustomerController.generate(c, rng, state, "SELL_TO_SHOP", index)
		var generated = WeaponGenerator.generate(c, rng, guest, day.market)
		modes[generated.truth.values.generation_mode] = true
		check(PriceCalculator.calculate(c, generated, day.market).true_appraised_price > 0, "Generated price positive")
		for property in AppraisalService.FIELDS:
			check(generated.truth.values[AppraisalService.FIELDS[property]] in AppraisalService.domain(c, property), "Generator property domain")
	check(modes.size() == 3, "All generation modes covered")
	for seed_index in range(12345, 12365):
		var played = DayController.new(seed_index)
		while played.phase != "COMPLETE":
			if played.phase == "BETWEEN":
				played.next_guest()
			elif played.phase == "SELLER":
				played.buy()
				if played.phase == "SELLER":
					played.refuse()
			else:
				played.resolve_buyer()
		check(played.guest_number == 8, "Complete buy-all playthrough")
		check(played.state.cash == played.state.starting_cash - played.state.purchase_spending + played.state.sale_revenue, "Day receipt cash reconciliation")
		if seed_index == DayController.DEFAULT_SEED:
			print("Default seed buy-all: %d seller trades, %d buyer trades" % [played.state.seller_trades, played.state.buyer_trades])
			check(played.state.trade_count == played.state.seller_trades + played.state.buyer_trades, "Normal trade counters reconcile")
	print("CHECKS: %d | FAILURES: %d | Guest 8 sellers: %d/1000" % [checks, failures, seller_eights])
	quit(0 if failures == 0 else 1)

func verify_reference(c: Dictionary) -> void:
	var cases = JSON.parse_string(FileAccess.get_file_as_string("res://tests/reference_cases.json"))
	check(cases is Array and cases.size() == 128, "Python reference fixtures present")
	if not cases is Array:
		return
	var sales = 0
	for sample in cases:
		var rng = RandomNumberGenerator.new()
		rng.seed = 99
		var truth = WeaponTrueState.new(sample.weapon)
		var item = WeaponData.new(truth, AppraisalService.create_knowledge(c, truth, rng), sample.seller)
		var price = PriceCalculator.calculate(c, item, sample.market)
		check(price.true_appraised_price == int(sample.price.appraised_price), "Python true price parity expected=%s actual=%s modifier=%s/%s" % [sample.price.appraised_price, price.true_appraised_price, sample.price.item_value_modifier, price.modifier])
		check(price.asking_price == int(sample.price.asking_price), "Python asking parity")
		check(is_equal_approx(price.effective_refining, sample.price.effective_refining_value), "Python refining parity")
		var fit = BuyerFitService.calculate(c, sample.buyer, truth.values)
		check(fit.is_empty() == sample.fit.is_empty(), "Python compatibility parity")
		if not fit.is_empty():
			check(is_equal_approx(fit.score, sample.fit.score), "Python buyer fit score parity")
			for key in fit.components:
				check(is_equal_approx(fit.components[key], sample.fit.components[key]), "Python buyer component parity")
		check(ProgressionService.purchase_delta(c, sample.seller, float(price.asking_price) / price.true_appraised_price) == sample.purchase_delta, "Python seller reputation parity")
		for axis in ["reputation", "trade_count"]:
			for key in c.progression[axis]:
				var result = ProgressionService.interpolate(c.progression[axis][key], sample.reputation if axis == "reputation" else sample.trades)
				for weight in result:
					check(is_equal_approx(result[weight], sample.progression[key][weight]), "Python progression parity")
		var state = ShopState.new(c)
		state.reputation = sample.reputation
		item.final_purchase_price = price.asking_price
		state.inventory.append(item)
		var sale = TransactionService.buyer(c, rng, state, sample.buyer, sample.market)
		check(sale.success == sample.sale.success and state.cash == sample.sale.cash, "Python buyer sale parity")
		check(is_equal_approx(state.reputation, sample.sale.reputation) and state.realized_trade_profit == sample.sale.profit, "Python sale accounting parity")
		sales += int(sale.success)
	check(sales > 0 and sales < cases.size(), "Successful and failed buyer sales covered")
	print("Python parity: 128 cases, %d successful buyer sales" % sales)
