extends SceneTree

var checks = 0
var failures = 0

func check(ok: bool, description: String) -> void:
	checks += 1
	if not ok:
		failures += 1
		push_error(description)

func _initialize() -> void:
	run.call_deferred()

func run() -> void:
	var day = DayController.new(71)
	day.next_guest()
	var c = day.config
	var item = day.item
	var original = PriceCalculator.calculate(c, item, day.market).true_appraised_price
	var visible = item.known.player_view()
	var base = int(c.price.base_prices[str(visible.tier)])
	check(c.economy.visitor_roles == {"SELL_TO_SHOP": 0.55, "BUY_FROM_SHOP": 0.45}, "General role defaults")
	check(c.price.market_balance_values == {"STRONG": 0.2, "NORMAL": 0.0, "WEAK": -0.2}, "Balance contributions")
	check(c.price.market_popularity_values == {"POPULAR": 0.2, "NORMAL": 0.0, "UNPOPULAR": -0.2}, "Popularity contributions")
	for axis in PlayerJudgement.MARKET_SECTIONS:
		for choice in range(3):
			check(item.judgement.choose(axis, choice, visible), "Market choice requires no appraisal")
			check(PriceCalculator.estimate(c, visible, item.judgement) == base, "Unchecked market choice ignored")
			item.judgement.include(axis, true, visible)
			check(PriceCalculator.estimate(c, visible, item.judgement) == Balance.money(base * (1 + [-0.2, 0.0, 0.2][choice])), "Selected market contribution")
			check(PriceCalculator.calculate(c, item, day.market).true_appraised_price == original, "Market judgement never changes truth")
			item.judgement.include(axis, false, visible)
		check(day.market_knowledge.observations[item.truth.values.required_class][axis] == null, "No automatic market hint leak")
	day.market_knowledge.record_hint(item.truth.values.required_class, "class_balance", "WEAK", "radio")
	check(PriceCalculator.calculate(c, item, day.market).true_appraised_price == original, "Reported hint does not alter market truth")
	var types = []
	for pool in c.weapon.class_weapon_pools.values():
		for item_type in pool:
			if item_type not in types:
				types.append(item_type)
	for adventurer_class in c.guest.classes:
		var buyer = day.guest.duplicate(true)
		buyer.adventurer_class = adventurer_class
		for item_type in types:
			var w = item.truth.values.duplicate(true)
			w.item_type = item_type
			w.required_class = "WARRIOR"
			check(not BuyerFitService.calculate(c, buyer, w).is_empty() == (item_type in c.weapon.class_weapon_pools[adventurer_class]), "Usable pool compatibility for every class/type")
	var future = c.duplicate(true)
	future.weapon.class_weapon_pools.CLERIC.append("bow")
	var cleric = day.guest.duplicate(true)
	cleric.adventurer_class = "CLERIC"
	var shared = item.truth.values.duplicate(true)
	shared.item_type = "bow"
	check(not BuyerFitService.calculate(future, cleric, shared).is_empty(), "New shared weapon needs no code exception")
	var weak = {}
	var strong = {}
	for adventurer_class in c.guest.classes:
		weak[adventurer_class] = ["WEAK", "UNPOPULAR"]
		strong[adventurer_class] = ["STRONG", "POPULAR"]
	for seed_index in range(100):
		var a_rng = RandomNumberGenerator.new()
		var b_rng = RandomNumberGenerator.new()
		a_rng.seed = seed_index
		b_rng.seed = seed_index
		var a = WeaponGenerator.generate(c, a_rng, day.guest, weak)
		var b = WeaponGenerator.generate(c, b_rng, day.guest, strong)
		check(a.truth.values == b.truth.values, "Market-independent generation at same seed")
		check(a.truth.values.processing_load == a.truth.values.effective_processing_load, "Only equipment contributes load")
	print("MARKET CHECKS: %d | FAILURES: %d" % [checks, failures])
	quit(0 if failures == 0 else 1)
